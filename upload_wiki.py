#!/usr/bin/env python3
"""
Ανέβασμα σελίδων Textile στο Wiki του Redmine μέσω REST API.

Χρήση:
  python3 upload_wiki.py --url https://redmine.dataverse.gr --project aade-support --dry-run
  python3 upload_wiki.py --url https://redmine.dataverse.gr --project aade-support
      → ζητά το API key χωρίς να εμφανίζεται στην οθόνη
  python3 upload_wiki.py --url https://redmine.dataverse.gr --api-key <KEY> --project aade-support
  python3 upload_wiki.py ... --force        # αντικατάσταση υπαρχουσών σελίδων

API key: Redmine → My account → API access key.
Σειρά αναζήτησης: --url / --api-key → μεταβλητές REDMINE_URL / REDMINE_API_KEY → ερώτηση στην κονσόλα.
Το --api-key μένει στο ιστορικό του shell· προτιμήστε την ερώτηση ή τη μεταβλητή περιβάλλοντος.

Χωρίς --force, σελίδες που υπάρχουν ήδη ΔΕΝ αλλάζουν (εμφανίζονται ως SKIP).
Ιδιαίτερη προσοχή στη σελίδα «Wiki»: αν το project έχει ήδη αρχική σελίδα, ελέγξτε την πριν το --force.
Απαιτεί μόνο Python 3 (χωρίς εξωτερικές βιβλιοθήκες).
"""
import argparse, getpass, json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

# (όνομα σελίδας, γονική σελίδα) — με σειρά δημιουργίας: πρώτα οι γονείς
PAGES = [
    ("Wiki", None),
    ("10-System-Overview", "Wiki"),
    ("20-Environments", "Wiki"),
    ("30-Subsystems", "Wiki"),
    ("40-Integrations", "Wiki"),
    ("50-Troubleshooting", "Wiki"),
    ("60-Support-Process", "Wiki"),
    ("70-Admin-How-To", "Wiki"),
    ("80-Known-Issues", "Wiki"),
    ("90-References", "Wiki"),
    ("11-Subsystem-Map", "10-System-Overview"),
    ("12-Request-Lifecycle", "10-System-Overview"),
    ("13-Integration-Map", "10-System-Overview"),
    ("19-Glossary", "10-System-Overview"),
    ("63-Escalation-Matrix", "60-Support-Process"),   # πριν τα runbooks λόγω {{include}}
    ("64-Communication-Templates", "60-Support-Process"),
    ("21-Inventory-PROD", "20-Environments"),
    ("24-Access-How-To", "20-Environments"),
    ("38-Reporting", "30-Subsystems"),
    ("43-RabbitMQ-Queues", "40-Integrations"),
    ("45-HRMS-User-Sync", "40-Integrations"),
    ("72-Org-Structure", "70-Admin-How-To"),
    ("73-Mass-Operations", "70-Admin-How-To"),
    ("74-Camunda-Operations", "70-Admin-How-To"),
    ("76-Data-Fixes", "70-Admin-How-To"),
    ("50-Triage-Decision-Tree", "50-Troubleshooting"),
    ("51-RB01-Status-Complete-Revoke", "50-Troubleshooting"),
    ("52-RB02-Cannot-Process", "50-Troubleshooting"),
    ("53-RB03-No-Case-Number", "50-Troubleshooting"),
    ("54-RB04-Employee-Onboarding", "50-Troubleshooting"),
    ("55-RB05-Login-Slowness-Outage", "50-Troubleshooting"),
    ("56-RB06-Appointment-Booking", "50-Troubleshooting"),
    ("57-RB07-Audit-Appointments", "50-Troubleshooting"),
    ("81-Known-Issues-Register", "80-Known-Issues"),
    ("99-Wiki-Conventions", "90-References"),
    ("99-Template-Subsystem", "99-Wiki-Conventions"),
    ("99-Template-Integration", "99-Wiki-Conventions"),
    ("99-Template-Runbook", "99-Wiki-Conventions"),
]

def call(method, url, key, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Redmine-API-Key", key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status

def exists(base, project, title, key):
    url = f"{base}/projects/{project}/wiki/{urllib.parse.quote(title)}.json"
    try:
        call("GET", url, key)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Βασικό URL του Redmine, π.χ. https://redmine.dataverse.gr (ή REDMINE_URL)")
    ap.add_argument("--api-key", help="API key χρήστη Redmine (ή REDMINE_API_KEY· αν λείπει, ζητείται)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--dir", default=str(Path(__file__).parent / "wiki"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--comment", default="KB υποστήριξης — αρχική δημιουργία")
    a = ap.parse_args()

    base = (a.url or os.environ.get("REDMINE_URL", "")).rstrip("/")
    key = a.api_key or os.environ.get("REDMINE_API_KEY", "")
    if not a.dry_run:
        if not base:
            sys.exit("Δώστε --url (π.χ. --url https://redmine.dataverse.gr) ή ορίστε REDMINE_URL.")
        if not base.startswith(("https://", "http://")):
            sys.exit(f"Μη έγκυρο URL: {base}")
        if not key:
            key = getpass.getpass("Redmine API key: ").strip()
        if not key:
            sys.exit("Δεν δόθηκε API key.")

    missing = [t for t, _ in PAGES if not (Path(a.dir) / f"{t}.textile").exists()]
    if missing:
        sys.exit(f"Λείπουν αρχεία: {missing}")

    errors = 0
    for title, parent in PAGES:
        text = (Path(a.dir) / f"{title}.textile").read_text(encoding="utf-8")
        if a.dry_run:
            print(f"DRY   {title:40} parent={parent}  ({len(text)} χαρ.)")
            continue
        try:
            if not a.force and exists(base, a.project, title, key):
                print(f"SKIP  {title} (υπάρχει ήδη)")
                continue
            page = {"text": text, "comments": a.comment}
            if parent:
                page["parent_title"] = parent
            url = f"{base}/projects/{a.project}/wiki/{urllib.parse.quote(title)}.json"
            st = call("PUT", url, key, {"wiki_page": page})
            print(f"OK    {title} (HTTP {st})")
        except urllib.error.HTTPError as e:
            errors += 1
            print(f"ERROR {title}: HTTP {e.code} {e.read()[:300]!r}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
