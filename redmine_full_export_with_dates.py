#!/usr/bin/env python3
import os
import json
import time
import getpass
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import requests
import pandas as pd

# =========================
# CONFIGURATION
# =========================
REDMINE_URL = os.getenv("REDMINE_URL", "https://redmine.dataverse.gr").rstrip("/")
PROJECT_ID = os.getenv("REDMINE_PROJECT_ID", "et-support")

# Safer than hard-coding: set REDMINE_API_KEY or enter it when prompted.
API_KEY = os.getenv("REDMINE_API_KEY") or getpass.getpass("Redmine API key: ").strip()

# Download the actual attachment files as well as their metadata.
DOWNLOAD_ATTACHMENTS = True

# Keep issues strictly in this project, excluding subprojects.
EXCLUDE_SUBPROJECTS = True

OUTPUT_DIR = Path(f"redmine_export_{PROJECT_ID}{output_suffix()}")
ATTACHMENTS_DIR = OUTPUT_DIR / "attachments"
RAW_ISSUES_DIR = OUTPUT_DIR / "raw_issues"

TIMEOUT = 60
PAGE_SIZE = 100
SLEEP_BETWEEN_REQUESTS = 0.05


# =========================
# DATE FILTERS
# =========================
def read_date(prompt):
    while True:
        value = input(prompt).strip()
        if value == "":
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD, e.g. 2026-01-01.")


def read_filter_mode():
    print("\nIssue date filter:")
    print("  1 = created_on  (issues created in the period)")
    print("  2 = updated_on  (issues updated in the period)")
    print("  3 = no issue date filter")
    while True:
        value = input("Choice [1/2/3, default=1]: ").strip() or "1"
        if value == "1":
            return "created_on"
        if value == "2":
            return "updated_on"
        if value == "3":
            return None
        print("Enter 1, 2 or 3.")


DATE_FIELD = read_filter_mode()
if DATE_FIELD:
    DATE_FROM = read_date("From date [YYYY-MM-DD, Enter=no lower limit]: ")
    DATE_TO = read_date("To date   [YYYY-MM-DD, Enter=no upper limit]: ")
else:
    DATE_FROM = None
    DATE_TO = None

if DATE_FROM and DATE_TO:
    if datetime.strptime(DATE_FROM, "%Y-%m-%d") > datetime.strptime(DATE_TO, "%Y-%m-%d"):
        raise SystemExit("From date cannot be later than To date.")


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


def output_suffix():
    parts = []
    if DATE_FIELD:
        parts.append("created" if DATE_FIELD == "created_on" else "updated")
    if DATE_FROM:
        parts.append(f"from_{DATE_FROM}")
    if DATE_TO:
        parts.append(f"to_{DATE_TO}")
    return "_" + "_".join(parts) if parts else ""

session = requests.Session()
session.headers.update({
    "X-Redmine-API-Key": API_KEY,
    "Accept": "application/json",
    "User-Agent": "RedmineFullExporter/1.0",
})


def api_get(path, params=None, stream=False, retries=4):
    url = f"{REDMINE_URL}{path}"
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, params=params, timeout=TIMEOUT, stream=stream)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "5"))
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == retries:
                raise
            wait = attempt * 2
            print(f"Request failed ({exc}). Retry {attempt}/{retries} in {wait}s...")
            time.sleep(wait)

    raise last_exc


def entity_name(obj):
    if isinstance(obj, dict):
        return obj.get("name", "")
    return ""


def entity_id(obj):
    if isinstance(obj, dict):
        return obj.get("id", "")
    return ""


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
    return cleaned[:180] or "attachment"


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
    params = {"include": "journals,attachments,relations,children"}
    return api_get(f"/issues/{issue_id}.json", params=params).json()["issue"]


def list_time_entries():
    entries = []
    offset = 0

    while True:
        params = {
            "project_id": PROJECT_ID,
            "limit": PAGE_SIZE,
            "offset": offset,
        }
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


def download_attachment(attachment, issue_id):
    content_url = attachment.get("content_url")
    if not content_url:
        return ""

    filename = safe_filename(attachment.get("filename", f"attachment_{attachment.get('id', '')}"))
    issue_dir = ATTACHMENTS_DIR / str(issue_id)
    issue_dir.mkdir(parents=True, exist_ok=True)

    # Prefix with attachment id to avoid collisions.
    local_path = issue_dir / f"{attachment.get('id', 'x')}_{filename}"

    if local_path.exists() and local_path.stat().st_size > 0:
        return str(local_path)

    try:
        # Usually content_url is on the same Redmine instance.
        r = session.get(content_url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return str(local_path)
    except requests.RequestException as exc:
        print(f"  WARNING attachment {attachment.get('id')} failed: {exc}")
        return ""


def build_exports(full_issues, time_entries):
    issue_rows = []
    journal_rows = []
    detail_rows = []
    attachment_rows = []
    relation_rows = []
    child_rows = []

    for issue in full_issues:
        issue_id = issue.get("id")

        row = {
            "id": issue_id,
            "project_id": entity_id(issue.get("project")),
            "project": entity_name(issue.get("project")),
            "tracker_id": entity_id(issue.get("tracker")),
            "tracker": entity_name(issue.get("tracker")),
            "status_id": entity_id(issue.get("status")),
            "status": entity_name(issue.get("status")),
            "priority_id": entity_id(issue.get("priority")),
            "priority": entity_name(issue.get("priority")),
            "author_id": entity_id(issue.get("author")),
            "author": entity_name(issue.get("author")),
            "assigned_to_id": entity_id(issue.get("assigned_to")),
            "assigned_to": entity_name(issue.get("assigned_to")),
            "category_id": entity_id(issue.get("category")),
            "category": entity_name(issue.get("category")),
            "fixed_version_id": entity_id(issue.get("fixed_version")),
            "fixed_version": entity_name(issue.get("fixed_version")),
            "parent_id": entity_id(issue.get("parent")),
            "subject": issue.get("subject"),
            "description": issue.get("description"),
            "start_date": issue.get("start_date"),
            "due_date": issue.get("due_date"),
            "done_ratio": issue.get("done_ratio"),
            "estimated_hours": issue.get("estimated_hours"),
            "total_estimated_hours": issue.get("total_estimated_hours"),
            "spent_hours": issue.get("spent_hours"),
            "total_spent_hours": issue.get("total_spent_hours"),
            "is_private": issue.get("is_private"),
            "created_on": issue.get("created_on"),
            "updated_on": issue.get("updated_on"),
            "closed_on": issue.get("closed_on"),
        }
        row.update(custom_fields_to_dict(issue.get("custom_fields")))
        issue_rows.append(row)

        for journal in issue.get("journals", []) or []:
            journal_rows.append({
                "issue_id": issue_id,
                "journal_id": journal.get("id"),
                "user_id": entity_id(journal.get("user")),
                "user": entity_name(journal.get("user")),
                "notes": journal.get("notes"),
                "private_notes": journal.get("private_notes"),
                "created_on": journal.get("created_on"),
            })

            for d in journal.get("details", []) or []:
                detail_rows.append({
                    "issue_id": issue_id,
                    "journal_id": journal.get("id"),
                    "user": entity_name(journal.get("user")),
                    "created_on": journal.get("created_on"),
                    "property": d.get("property"),
                    "name": d.get("name"),
                    "old_value": d.get("old_value"),
                    "new_value": d.get("new_value"),
                })

        for att in issue.get("attachments", []) or []:
            local_path = ""
            if DOWNLOAD_ATTACHMENTS:
                local_path = download_attachment(att, issue_id)

            attachment_rows.append({
                "issue_id": issue_id,
                "attachment_id": att.get("id"),
                "filename": att.get("filename"),
                "filesize": att.get("filesize"),
                "content_type": att.get("content_type"),
                "description": att.get("description"),
                "author_id": entity_id(att.get("author")),
                "author": entity_name(att.get("author")),
                "created_on": att.get("created_on"),
                "content_url": att.get("content_url"),
                "local_path": local_path,
            })

        for rel in issue.get("relations", []) or []:
            relation_rows.append({
                "issue_id_exported": issue_id,
                "relation_id": rel.get("id"),
                "issue_id": rel.get("issue_id"),
                "issue_to_id": rel.get("issue_to_id"),
                "relation_type": rel.get("relation_type"),
                "delay": rel.get("delay"),
            })

        for child in issue.get("children", []) or []:
            child_rows.append({
                "parent_issue_id": issue_id,
                "child_issue_id": child.get("id"),
                "child_subject": child.get("subject"),
            })

    time_rows = []
    for te in time_entries:
        row = {
            "id": te.get("id"),
            "project_id": entity_id(te.get("project")),
            "project": entity_name(te.get("project")),
            "issue_id": entity_id(te.get("issue")),
            "user_id": entity_id(te.get("user")),
            "user": entity_name(te.get("user")),
            "activity_id": entity_id(te.get("activity")),
            "activity": entity_name(te.get("activity")),
            "hours": te.get("hours"),
            "comments": te.get("comments"),
            "spent_on": te.get("spent_on"),
            "created_on": te.get("created_on"),
            "updated_on": te.get("updated_on"),
        }
        row.update(custom_fields_to_dict(te.get("custom_fields")))
        time_rows.append(row)

    return {
        "Issues": issue_rows,
        "Journals": journal_rows,
        "Journal_Details": detail_rows,
        "Attachments": attachment_rows,
        "Relations": relation_rows,
        "Children": child_rows,
        "Time_Entries": time_rows,
    }


def autosize_worksheet(ws, df, max_width=60):
    for idx, col in enumerate(df.columns, start=1):
        samples = [str(col)]
        if not df.empty:
            samples += [str(v) for v in df[col].head(500).fillna("")]
        width = min(max(len(s) for s in samples) + 2, max_width)
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_excel(tables):
    xlsx_path = OUTPUT_DIR / f"{PROJECT_ID}_full_export{output_suffix()}.xlsx"

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for sheet_name, rows in tables.items():
            df = pd.DataFrame(rows)

            # Excel cells have a max length of 32,767 characters.
            # Keep the complete untruncated data in JSON; truncate only Excel display.
            if not df.empty:
                for col in df.columns:
                    df[col] = df[col].map(
                        lambda v: (v[:32760] + "…") if isinstance(v, str) and len(v) > 32760 else v
                    )

            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            ws = writer.book[sheet_name[:31]]
            autosize_worksheet(ws, df)

    return xlsx_path


def main():
    if not API_KEY:
        raise SystemExit("No API key supplied.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    if DOWNLOAD_ATTACHMENTS:
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Redmine: {REDMINE_URL}")
    print(f"Project: {PROJECT_ID}")
    if DATE_FIELD:
        print(f"Issue filter: {DATE_FIELD}")
        print(f"From: {DATE_FROM or 'no limit'}")
        print(f"To:   {DATE_TO or 'no limit'}")
    else:
        print("Issue filter: none")
    print("Testing API access...")

    # Verify project and credentials.
    project_resp = api_get(f"/projects/{PROJECT_ID}.json").json()
    project = project_resp.get("project", {})
    print(f"Connected. Project: {project.get('name')} (id={project.get('id')})")

    issue_list = list_all_issues()
    issue_ids = [i["id"] for i in issue_list]
    print(f"\nFetching full details for {len(issue_ids)} issues...")

    full_issues = []
    for pos, issue_id in enumerate(issue_ids, start=1):
        issue = get_issue_full(issue_id)
        full_issues.append(issue)

        with open(RAW_ISSUES_DIR / f"{issue_id}.json", "w", encoding="utf-8") as f:
            json.dump(issue, f, ensure_ascii=False, indent=2)

        print(f"Full issue: {pos}/{len(issue_ids)}  #{issue_id}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print("\nFetching time entries...")
    time_entries = list_time_entries()

    export = {
        "export_info": {
            "redmine_url": REDMINE_URL,
            "project_identifier": PROJECT_ID,
            "project_numeric_id": project.get("id"),
            "project_name": project.get("name"),
            "date_field": DATE_FIELD,
            "date_from": DATE_FROM,
            "date_to": DATE_TO,
            "issues_count": len(full_issues),
            "time_entries_count": len(time_entries),
            "attachments_downloaded": DOWNLOAD_ATTACHMENTS,
        },
        "issues": full_issues,
        "time_entries": time_entries,
    }

    json_path = OUTPUT_DIR / f"{PROJECT_ID}_full_export{output_suffix()}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    tables = build_exports(full_issues, time_entries)
    xlsx_path = write_excel(tables)

    print("\nDONE")
    print(f"JSON:       {json_path.resolve()}")
    print(f"Excel:      {xlsx_path.resolve()}")
    if DOWNLOAD_ATTACHMENTS:
        print(f"Attachments:{ATTACHMENTS_DIR.resolve()}")
    print(f"Raw issues: {RAW_ISSUES_DIR.resolve()}")


if __name__ == "__main__":
    main()
