#!/usr/bin/env python3
import os
import json
import time
import getpass
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import requests
import pandas as pd

REDMINE_URL = os.getenv("REDMINE_URL", "https://redmine.dataverse.gr").rstrip("/")
DEFAULT_PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "aade")
PROJECT_ID = input(
    f"Redmine Project ID [default={DEFAULT_PROJECT_ID}]: "
).strip() or DEFAULT_PROJECT_ID
API_KEY = os.getenv("REDMINE_API_KEY") or getpass.getpass("Redmine API key: ").strip()

DOWNLOAD_ATTACHMENTS = True
EXCLUDE_SUBPROJECTS = True
TIMEOUT = 60
PAGE_SIZE = 100
SLEEP_BETWEEN_REQUESTS = 0.05

session = requests.Session()
session.headers.update({
    "X-Redmine-API-Key": API_KEY,
    "Accept": "application/json",
    "User-Agent": "RedmineFullExporter/2.0",
})


def read_yes_no(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"{prompt} {suffix}: ").strip().lower()
        if value == "":
            return default
        if value in ("y", "yes", "ν", "ναι"):
            return True
        if value in ("n", "no", "ο", "όχι"):
            return False
        print("Δώσε y ή n.")


def read_date(prompt):
    while True:
        value = input(prompt).strip()
        if value == "":
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            print("Λάθος μορφή. Χρησιμοποίησε YYYY-MM-DD.")


def read_filter_mode():
    print("\nΦίλτρο ημερομηνίας για τα issues:")
    print("  1 = created_on")
    print("  2 = updated_on")
    print("  3 = χωρίς φίλτρο")
    while True:
        value = input("Επιλογή [1/2/3, default=1]: ").strip() or "1"
        if value == "1":
            return "created_on"
        if value == "2":
            return "updated_on"
        if value == "3":
            return None
        print("Δώσε 1, 2 ή 3.")


DATE_FIELD = read_filter_mode()
if DATE_FIELD:
    DATE_FROM = read_date("Από ημερομηνία [YYYY-MM-DD, Enter=χωρίς όριο]: ")
    DATE_TO = read_date("Έως ημερομηνία [YYYY-MM-DD, Enter=χωρίς όριο]: ")
else:
    DATE_FROM = None
    DATE_TO = None

if DATE_FROM and DATE_TO:
    if datetime.strptime(DATE_FROM, "%Y-%m-%d") > datetime.strptime(DATE_TO, "%Y-%m-%d"):
        raise SystemExit("Η ημερομηνία Από δεν μπορεί να είναι μεταγενέστερη από την Έως.")

EXPORT_WIKI = read_yes_no("Export Wiki pages?", True)
DOWNLOAD_WIKI_ATTACHMENTS = read_yes_no("Export Wiki attachments?", True) if EXPORT_WIKI else False
EXPORT_WIKI_VERSION_HISTORY = read_yes_no("Export Wiki version history?", False) if EXPORT_WIKI else False


def build_date_filter():
    if not DATE_FIELD:
        return None
    if DATE_FROM and DATE_TO:
        return f"><{DATE_FROM}|{DATE_TO}"
    if DATE_FROM:
        return f">={DATE_FROM}"
    if DATE_TO:
        return f"<={DATE_TO}"
    return None


DATE_FILTER = build_date_filter()


def api_get(path, params=None, retries=4):
    url = f"{REDMINE_URL}{path}"
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", "5")))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == retries:
                raise
            time.sleep(attempt * 2)
    raise last_exc


def entity_name(obj):
    return obj.get("name", "") if isinstance(obj, dict) else ""


def entity_id(obj):
    return obj.get("id", "") if isinstance(obj, dict) else ""


def custom_fields_to_dict(custom_fields):
    out = {}
    for cf in custom_fields or []:
        name = cf.get("name") or f"custom_field_{cf.get('id')}"
        value = cf.get("value")
        if isinstance(value, list):
            value = " | ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        out[name] = value
    return out


def safe_filename(name):
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if c in invalid else c for c in str(name))
    cleaned = cleaned.strip().rstrip(".")
    return cleaned[:180] or "file"


def output_suffix():
    parts = []
    if DATE_FIELD:
        parts.append("created" if DATE_FIELD == "created_on" else "updated")
    if DATE_FROM:
        parts.append(f"from_{DATE_FROM}")
    if DATE_TO:
        parts.append(f"to_{DATE_TO}")
    return "_" + "_".join(parts) if parts else ""


OUTPUT_DIR = Path(f"redmine_export_{PROJECT_ID}{output_suffix()}")
RAW_ISSUES_DIR = OUTPUT_DIR / "raw_issues"
ATTACHMENTS_DIR = OUTPUT_DIR / "attachments"
WIKI_DIR = OUTPUT_DIR / "wiki"
WIKI_RAW_DIR = OUTPUT_DIR / "wiki_raw"
WIKI_ATTACHMENTS_DIR = OUTPUT_DIR / "wiki_attachments"
WIKI_HISTORY_DIR = OUTPUT_DIR / "wiki_history"


def list_all_issues():
    issues = []
    offset = 0
    while True:
        params = {
            "project_id": PROJECT_ID,
            "status_id": "*",
            "limit": PAGE_SIZE,
            "offset": offset,
            "sort": "id:asc",
        }
        if EXCLUDE_SUBPROJECTS:
            params["subproject_id"] = "!*"
        if DATE_FIELD and DATE_FILTER:
            params[DATE_FIELD] = DATE_FILTER

        data = api_get("/issues.json", params=params).json()
        batch = data.get("issues", [])
        total = data.get("total_count", len(batch))
        issues.extend(batch)
        print(f"Issues list: {len(issues)}/{total}")

        if not batch or len(issues) >= total:
            break

        offset += len(batch)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return issues


def get_issue_full(issue_id):
    return api_get(
        f"/issues/{issue_id}.json",
        params={"include": "journals,attachments,relations,children"},
    ).json()["issue"]


def list_time_entries():
    entries = []
    offset = 0
    while True:
        params = {"project_id": PROJECT_ID, "limit": PAGE_SIZE, "offset": offset}
        if DATE_FROM:
            params["from"] = DATE_FROM
        if DATE_TO:
            params["to"] = DATE_TO

        data = api_get("/time_entries.json", params=params).json()
        batch = data.get("time_entries", [])
        total = data.get("total_count", len(batch))
        entries.extend(batch)
        print(f"Time entries: {len(entries)}/{total}")

        if not batch or len(entries) >= total:
            break

        offset += len(batch)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return entries


def download_attachment(att, base_dir):
    url = att.get("content_url")
    if not url:
        return ""

    base_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(att.get("filename", f"attachment_{att.get('id', '')}"))
    local_path = base_dir / f"{att.get('id', 'x')}_{filename}"

    if local_path.exists() and local_path.stat().st_size > 0:
        return str(local_path)

    try:
        r = session.get(url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return str(local_path)
    except requests.RequestException as exc:
        print(f"WARNING attachment {att.get('id')} failed: {exc}")
        return ""


def wiki_index():
    project = quote(PROJECT_ID, safe="")
    return api_get(f"/projects/{project}/wiki/index.json").json().get("wiki_pages", [])


def get_wiki_page(title, version=None):
    project = quote(PROJECT_ID, safe="")
    title_q = quote(title, safe="")
    if version is None:
        path = f"/projects/{project}/wiki/{title_q}.json"
    else:
        path = f"/projects/{project}/wiki/{title_q}/{version}.json"
    return api_get(path, params={"include": "attachments"}).json()["wiki_page"]


def export_wiki():
    if not EXPORT_WIKI:
        return [], []

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_RAW_DIR.mkdir(parents=True, exist_ok=True)
    if DOWNLOAD_WIKI_ATTACHMENTS:
        WIKI_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    if EXPORT_WIKI_VERSION_HISTORY:
        WIKI_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    pages = wiki_index()
    print(f"Wiki pages found: {len(pages)}")

    rows = []
    history_rows = []
    index_rows = []

    for pos, summary in enumerate(pages, start=1):
        title = summary.get("title", "")
        page = get_wiki_page(title)
        slug = safe_filename(title)

        textile_file = WIKI_DIR / f"{slug}.textile"
        textile_file.write_text(page.get("text", "") or "", encoding="utf-8")

        raw_file = WIKI_RAW_DIR / f"{slug}.json"
        raw_file.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")

        att_meta = []
        for att in page.get("attachments", []) or []:
            local_path = ""
            if DOWNLOAD_WIKI_ATTACHMENTS:
                local_path = download_attachment(att, WIKI_ATTACHMENTS_DIR / slug)
            att_meta.append({
                "id": att.get("id"),
                "filename": att.get("filename"),
                "local_path": local_path,
            })

        row = {
            "title": page.get("title"),
            "parent_title": (page.get("parent") or {}).get("title", ""),
            "version": page.get("version"),
            "author": entity_name(page.get("author")),
            "comments": page.get("comments"),
            "created_on": page.get("created_on"),
            "updated_on": page.get("updated_on"),
            "textile": page.get("text"),
            "local_textile_file": str(textile_file),
            "local_raw_json": str(raw_file),
            "attachments_count": len(att_meta),
        }
        rows.append(row)

        index_rows.append({
            "title": row["title"],
            "parent_title": row["parent_title"],
            "version": row["version"],
            "author": row["author"],
            "created_on": row["created_on"],
            "updated_on": row["updated_on"],
            "local_textile_file": row["local_textile_file"],
            "local_raw_json": row["local_raw_json"],
            "attachments": att_meta,
        })

        if EXPORT_WIKI_VERSION_HISTORY:
            current_version = int(page.get("version") or 0)
            hist_dir = WIKI_HISTORY_DIR / slug
            hist_dir.mkdir(parents=True, exist_ok=True)

            for version in range(1, current_version + 1):
                try:
                    vp = get_wiki_page(title, version)
                    tf = hist_dir / f"v{version:04d}.textile"
                    jf = hist_dir / f"v{version:04d}.json"
                    tf.write_text(vp.get("text", "") or "", encoding="utf-8")
                    jf.write_text(json.dumps(vp, ensure_ascii=False, indent=2), encoding="utf-8")
                    history_rows.append({
                        "title": title,
                        "version": vp.get("version"),
                        "author": entity_name(vp.get("author")),
                        "comments": vp.get("comments"),
                        "created_on": vp.get("created_on"),
                        "updated_on": vp.get("updated_on"),
                        "textile": vp.get("text"),
                        "local_textile_file": str(tf),
                        "local_raw_json": str(jf),
                    })
                except requests.HTTPError as exc:
                    print(f"WARNING wiki version failed: {title} v{version}: {exc}")
                time.sleep(SLEEP_BETWEEN_REQUESTS)

        print(f"Wiki page: {pos}/{len(pages)} {title}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    (WIKI_DIR / "index.json").write_text(
        json.dumps(index_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return rows, history_rows


def build_tables(full_issues, time_entries, wiki_pages, wiki_history):
    issues, journals, details, attachments, relations, children = [], [], [], [], [], []

    for issue in full_issues:
        iid = issue.get("id")
        row = {
            "id": iid,
            "project": entity_name(issue.get("project")),
            "tracker": entity_name(issue.get("tracker")),
            "status": entity_name(issue.get("status")),
            "priority": entity_name(issue.get("priority")),
            "author": entity_name(issue.get("author")),
            "assigned_to": entity_name(issue.get("assigned_to")),
            "category": entity_name(issue.get("category")),
            "fixed_version": entity_name(issue.get("fixed_version")),
            "parent_id": entity_id(issue.get("parent")),
            "subject": issue.get("subject"),
            "description": issue.get("description"),
            "start_date": issue.get("start_date"),
            "due_date": issue.get("due_date"),
            "done_ratio": issue.get("done_ratio"),
            "estimated_hours": issue.get("estimated_hours"),
            "spent_hours": issue.get("spent_hours"),
            "created_on": issue.get("created_on"),
            "updated_on": issue.get("updated_on"),
            "closed_on": issue.get("closed_on"),
        }
        row.update(custom_fields_to_dict(issue.get("custom_fields")))
        issues.append(row)

        for j in issue.get("journals", []) or []:
            journals.append({
                "issue_id": iid,
                "journal_id": j.get("id"),
                "user": entity_name(j.get("user")),
                "notes": j.get("notes"),
                "private_notes": j.get("private_notes"),
                "created_on": j.get("created_on"),
            })
            for d in j.get("details", []) or []:
                details.append({
                    "issue_id": iid,
                    "journal_id": j.get("id"),
                    "user": entity_name(j.get("user")),
                    "created_on": j.get("created_on"),
                    "property": d.get("property"),
                    "name": d.get("name"),
                    "old_value": d.get("old_value"),
                    "new_value": d.get("new_value"),
                })

        for att in issue.get("attachments", []) or []:
            local_path = ""
            if DOWNLOAD_ATTACHMENTS:
                local_path = download_attachment(att, ATTACHMENTS_DIR / str(iid))
            attachments.append({
                "issue_id": iid,
                "attachment_id": att.get("id"),
                "filename": att.get("filename"),
                "filesize": att.get("filesize"),
                "content_type": att.get("content_type"),
                "author": entity_name(att.get("author")),
                "created_on": att.get("created_on"),
                "content_url": att.get("content_url"),
                "local_path": local_path,
            })

        for rel in issue.get("relations", []) or []:
            relations.append({
                "issue_id_exported": iid,
                "relation_id": rel.get("id"),
                "issue_id": rel.get("issue_id"),
                "issue_to_id": rel.get("issue_to_id"),
                "relation_type": rel.get("relation_type"),
                "delay": rel.get("delay"),
            })

        for child in issue.get("children", []) or []:
            children.append({
                "parent_issue_id": iid,
                "child_issue_id": child.get("id"),
                "child_subject": child.get("subject"),
            })

    time_rows = []
    for te in time_entries:
        row = {
            "id": te.get("id"),
            "project": entity_name(te.get("project")),
            "issue_id": entity_id(te.get("issue")),
            "user": entity_name(te.get("user")),
            "activity": entity_name(te.get("activity")),
            "hours": te.get("hours"),
            "comments": te.get("comments"),
            "spent_on": te.get("spent_on"),
            "created_on": te.get("created_on"),
            "updated_on": te.get("updated_on"),
        }
        row.update(custom_fields_to_dict(te.get("custom_fields")))
        time_rows.append(row)

    tables = {
        "Issues": issues,
        "Journals": journals,
        "Journal_Details": details,
        "Attachments": attachments,
        "Relations": relations,
        "Children": children,
        "Time_Entries": time_rows,
    }
    if EXPORT_WIKI:
        tables["Wiki_Pages"] = wiki_pages
        if EXPORT_WIKI_VERSION_HISTORY:
            tables["Wiki_History"] = wiki_history
    return tables


# Characters forbidden by Excel/OpenXML worksheets.
# Tabs (\x09), line feeds (\x0A) and carriage returns (\x0D) are intentionally preserved.
EXCEL_ILLEGAL_CHARACTERS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def clean_excel_value(value):
    """
    Sanitize values only for the Excel representation.

    - Removes control characters that openpyxl/Excel cannot store.
    - Preserves normal tabs/newlines/carriage returns.
    - Truncates strings to Excel's 32,767-character cell limit.
    - Does NOT modify the master JSON/raw issue/Textile exports.
    """
    if not isinstance(value, str):
        return value

    value = EXCEL_ILLEGAL_CHARACTERS_RE.sub("", value)

    # Excel cell text limit is 32,767 characters.
    if len(value) > 32767:
        value = value[:32760] + "…"

    return value


def write_excel(tables):
    xlsx_path = OUTPUT_DIR / f"{PROJECT_ID}_full_export{output_suffix()}.xlsx"

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for sheet, rows in tables.items():
            df = pd.DataFrame(rows)

            # Apply sanitization to ALL cells of ALL worksheets.
            # This covers comments, descriptions, Textile, custom fields,
            # time-entry comments, journal details, etc.
            if not df.empty:
                df = df.map(clean_excel_value)

            df.to_excel(writer, sheet_name=sheet[:31], index=False)

            ws = writer.book[sheet[:31]]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

    return xlsx_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    if DOWNLOAD_ATTACHMENTS:
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    project = api_get(f"/projects/{PROJECT_ID}.json").json().get("project", {})
    print(f"Connected. Project: {project.get('name')} (id={project.get('id')})")

    issue_ids = [i["id"] for i in list_all_issues()]
    full_issues = []

    print(f"\nFetching full details for {len(issue_ids)} issues...")
    for pos, iid in enumerate(issue_ids, start=1):
        issue = get_issue_full(iid)
        full_issues.append(issue)
        (RAW_ISSUES_DIR / f"{iid}.json").write_text(
            json.dumps(issue, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Full issue: {pos}/{len(issue_ids)} #{iid}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print("\nFetching time entries...")
    time_entries = list_time_entries()

    wiki_pages, wiki_history = [], []
    if EXPORT_WIKI:
        print("\nFetching wiki pages...")
        wiki_pages, wiki_history = export_wiki()

    master = {
        "export_info": {
            "project_identifier": PROJECT_ID,
            "project_name": project.get("name"),
            "date_field": DATE_FIELD,
            "date_from": DATE_FROM,
            "date_to": DATE_TO,
            "issues_count": len(full_issues),
            "time_entries_count": len(time_entries),
            "wiki_pages_count": len(wiki_pages),
            "wiki_history_count": len(wiki_history),
        },
        "issues": full_issues,
        "time_entries": time_entries,
        "wiki_pages": wiki_pages,
        "wiki_history": wiki_history,
    }

    json_path = OUTPUT_DIR / f"{PROJECT_ID}_full_export{output_suffix()}.json"
    json_path.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")

    xlsx_path = write_excel(build_tables(full_issues, time_entries, wiki_pages, wiki_history))

    print("\nDONE")
    print(f"JSON  : {json_path.resolve()}")
    print(f"Excel : {xlsx_path.resolve()}")
    if EXPORT_WIKI:
        print(f"Wiki  : {WIKI_DIR.resolve()}")


if __name__ == "__main__":
    main()
