# Wiki Uploader  — «Τα Αιτήματά μου» & «Τα Ραντεβού μου» (ΑΑΔΕ)

## Περιεχόμενα

| Αρχείο | Τι είναι |
|---|---|
| `KB-Design-ΑΑΔΕ.md` | Έγγραφο σχεδιασμού (πρότυπο ΕΤ προσαρμοσμένο): ανάλυση tickets, δέντρο σελίδων, ρυθμίσεις Redmine, roadmap, σημεία επαλήθευσης, ευρήματα ασφαλείας |
| `wiki/*.textile` | 37 σελίδες Wiki: Φάση Α, runbooks Φάσης Β και διαχειριστικές/υποδομής σελίδες από το wiki `aade` |
| `tickets-classification.csv` | 1.415 tickets με κατηγορία R01–R99 και προτεινόμενο runbook (UTF-8 BOM, διαχωριστικό `;`, ανοίγει σε Excel) |
| `upload_wiki.py` | Ανέβασμα σελίδων στο Redmine μέσω REST API |

## Πριν το ανέβασμα

1. **Δικαιώματα:** αποφασίστε αν οι χρήστες της ΑΑΔΕ θα βλέπουν το Wiki του `aade-support` (βλ. KB-Design §5). Τα runbooks περιέχουν SQL και εσωτερικά του συστήματος.
2. **REST API:** Administration → Settings → API → «Enable REST web service».
3. **Αρχική σελίδα:** το script γράφει στη σελίδα `Wiki`. Αν υπάρχει ήδη περιεχόμενο, κρατήστε αντίγραφο.
4. **Ασφάλεια:** αλλαγή των κωδικών που εμφανίζονται στο #77427 και στις σελίδες `RabbitMQ`, `MongoDB`, `Wiki` και `Σύνδεση σε PC ΑΑΔΕ` του project `aade`, και καθαρισμός τους μαζί με το ιστορικό εκδόσεων (KB-Design §9).

## Ανέβασμα

```bash
export REDMINE_URL=https://redmine.dataverse.gr
export REDMINE_API_KEY=xxxxxxxx
python3 upload_wiki.py --project aade-support --dry-run   # έλεγχος
python3 upload_wiki.py --project aade-support             # δημιουργεί μόνο όσες δεν υπάρχουν
```

Για αντικατάσταση υπαρχουσών σελίδων: `--force`. Χειροκίνητα: δημιουργία με τη σειρά της λίστας `PAGES` στο script (πρώτα οι γονικές).

## Δέντρο που δημιουργείται

```
Wiki
├── 10-System-Overview ── 11-Subsystem-Map · 12-Request-Lifecycle · 13-Integration-Map · 19-Glossary
├── 20-Environments ──── 21-Inventory-PROD · 24-Access-How-To          (περιορισμένη πρόσβαση)
├── 30-Subsystems ────── 38-Reporting
├── 40-Integrations ──── 43-RabbitMQ-Queues · 45-HRMS-User-Sync
├── 50-Troubleshooting ─ 50-Triage-Decision-Tree · 51-RB01 · 52-RB02 · 53-RB03 · 54-RB04 · 55-RB05 · 56-RB06 · 57-RB07
├── 60-Support-Process ─ 63-Escalation-Matrix (σκελετός) · 64-Communication-Templates
├── 70-Admin-How-To ──── 72-Org-Structure · 73-Mass-Operations · 74-Camunda-Operations · 76-Data-Fixes
├── 80-Known-Issues ──── 81-Known-Issues-Register
└── 90-References ────── 99-Wiki-Conventions ── 99-Template-Subsystem · 99-Template-Integration · 99-Template-Runbook
```

**Προσοχή για τις σελίδες 21 και 24:** περιέχουν IPs και hostnames (όχι credentials). Αν τα δικαιώματα του `aade-support` δεν περιοριστούν, μην τις ανεβάσετε εκεί — αφαιρέστε τις από τη λίστα `PAGES` του script και ανεβάστε τις σε restricted project.

Οι σύνδεσμοι προς σελίδες του roadmap που δεν έχουν γραφτεί ακόμα (π.χ. `21-Inventory-PROD`, `45-HRMS-User-Sync`, `72-Org-Structure`) εμφανίζονται κόκκινοι στο Redmine. Αυτό είναι σκόπιμο: δείχνει τι απομένει.

Οι παραπομπές `[[aade:…]]` δείχνουν στις υπάρχουσες σελίδες του project `aade`, μέχρι να μεταφερθούν.

## Μετά το ανέβασμα — συμπληρώνονται από την ομάδα

- `Owner` και `Τελευταίος έλεγχος` σε κάθε σελίδα
- `63-Escalation-Matrix`: ρόλοι και κανάλια
- Επίλυση των σημείων ⚠ (θέση services, APP3/APP4, παλαιές βάσεις) — KB-Design §8
- Διόρθωση της σελίδας πηγής `aade:Αδυναμία_αλλαγής_κατάστασης_αιτημάτων_&_ραντεβού` (KI-24) ή σήμανσή της ως αντικατεστημένης
- Μαζική ενημέρωση Category στα tickets από το CSV (αφού δημιουργηθούν οι Categories R01–R99)
