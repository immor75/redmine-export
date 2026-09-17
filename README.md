# Redmine Full Exporter

Python script για πλήρες export tickets από συγκεκριμένο Redmine project, με δυνατότητα χρονικού φιλτραρίσματος.

Το script δημιουργεί:

- Excel αρχείο με ξεχωριστά worksheets
- πλήρες JSON export
- ξεχωριστό JSON ανά issue
- πραγματικά attachment files
- time entries
- journals / comments
- αλλαγές πεδίων
- relations
- subtasks / children

Υποστηρίζει επίσης φίλτρο:

- `created_on`
- `updated_on`
- full export χωρίς ημερομηνιακό περιορισμό

---

## Περιεχόμενα

- [Αρχεία του project](#αρχεία-του-project)
- [Προαπαιτούμενα](#προαπαιτούμενα)
- [Εγκατάσταση](#εγκατάσταση)
- [Ρυθμίσεις](#ρυθμίσεις)
- [Redmine API Key](#redmine-api-key)
- [Εκτέλεση](#εκτέλεση)
- [Χρονικό φίλτρο](#χρονικό-φίλτρο)
- [Time Entries](#time-entries)
- [Output](#output)
- [Excel worksheets](#excel-worksheets)
- [JSON export](#json-export)
- [Attachments](#attachments)
- [Troubleshooting](#troubleshooting)
- [Ασφάλεια](#ασφάλεια)
- [.gitignore](#gitignore)

---

## Αρχεία του project

Η προτεινόμενη δομή του repository είναι:

```text
RedmineExporter/
├── redmine_full_export_with_dates.py
├── requirements.txt
├── README.md
└── .gitignore
```

Για να εκτελέσει κάποιος το exporter, αρκούν:

```text
redmine_full_export_with_dates.py
requirements.txt
README.md
```

Δεν πρέπει να διανέμεται κανένα API key μαζί με τα παραπάνω αρχεία.

---

## Προαπαιτούμενα

Απαιτείται Python 3.

Προτείνεται:

```text
Python 3.10+
```

Έλεγχος εγκατάστασης:

```powershell
python --version
```

ή:

```powershell
py --version
```

Παράδειγμα:

```text
Python 3.12.4
```

Αν η Python δεν είναι εγκατεστημένη:

https://www.python.org/downloads/

Στα Windows είναι χρήσιμο κατά την εγκατάσταση να επιλεγεί:

```text
Add Python to PATH
```

---

## Εγκατάσταση

Άνοιξε Command Prompt ή PowerShell και πήγαινε στον φάκελο του project.

Παράδειγμα:

```powershell
cd C:\RedmineExporter
```

ή:

```powershell
cd C:\Users\<username>\Downloads
```

Εγκατάσταση dependencies:

```powershell
py -m pip install -r requirements.txt
```

ή:

```powershell
python -m pip install -r requirements.txt
```

Οι βασικές βιβλιοθήκες είναι:

```text
requests
pandas
openpyxl
```

---

## Ρυθμίσεις

Το script είναι ήδη ρυθμισμένο για:

```python
REDMINE_URL = "https://redmine.dataverse.gr"
PROJECT_ID = "et-support"
```

### Subprojects

Η ρύθμιση:

```python
EXCLUDE_SUBPROJECTS = True
```

σημαίνει ότι εξάγονται μόνο issues που ανήκουν απευθείας στο project:

```text
et-support
```

και όχι issues από subprojects.

### Attachments

Η ρύθμιση:

```python
DOWNLOAD_ATTACHMENTS = True
```

σημαίνει ότι το script θα κατεβάσει και τα πραγματικά attachment files.

Αν θέλεις μόνο metadata:

```python
DOWNLOAD_ATTACHMENTS = False
```

---

## Redmine API Key

Το API key **δεν αποθηκεύεται μέσα στο script**.

Κατά την εκτέλεση εμφανίζεται:

```text
Redmine API key:
```

Κάνε paste το API key και πάτησε Enter.

Για λόγους ασφαλείας δεν εμφανίζεται στην οθόνη καθώς πληκτρολογείται.

Το API key βρίσκεται συνήθως στο Redmine:

```text
My account
→ API access key
```

---

## Εκτέλεση

Τρέξε:

```powershell
py redmine_full_export_with_dates.py
```

ή:

```powershell
python redmine_full_export_with_dates.py
```

---

## Χρονικό φίλτρο

Κατά την εκτέλεση εμφανίζεται:

```text
Φίλτρο ημερομηνίας για τα issues:

1 = created_on
2 = updated_on
3 = χωρίς φίλτρο ημερομηνίας

Επιλογή [1/2/3, default=1]:
```

### 1. `created_on`

Εξάγονται tickets που δημιουργήθηκαν μέσα στο συγκεκριμένο χρονικό διάστημα.

Παράδειγμα:

```text
Επιλογή: 1
Από: 2026-01-01
Έως: 2026-06-30
```

Αυτό σημαίνει:

> Εξαγωγή tickets που δημιουργήθηκαν από 01/01/2026 έως 30/06/2026.

### 2. `updated_on`

Εξάγονται tickets που ενημερώθηκαν μέσα στο συγκεκριμένο χρονικό διάστημα.

Παράδειγμα:

```text
Επιλογή: 2
Από: 2026-01-01
Έως: 2026-06-30
```

Αυτό είναι χρήσιμο όταν θέλουμε να βρούμε tickets στα οποία υπήρξε activity, ακόμα κι αν είχαν δημιουργηθεί παλαιότερα.

> Σημαντικό: αν ένα ticket επιλεγεί λόγω `updated_on`, το export περιλαμβάνει όλο το history του ticket και όχι μόνο τα journals που δημιουργήθηκαν μέσα στο διάστημα.

### 3. Χωρίς φίλτρο

```text
Επιλογή: 3
```

Γίνεται πλήρες export του project.

---

## Ημερομηνίες Από / Έως

Η μορφή ημερομηνίας είναι:

```text
YYYY-MM-DD
```

Παράδειγμα:

```text
2026-01-01
```

### Από συγκεκριμένη ημερομηνία και μετά

```text
Από: 2026-01-01
Έως: [Enter]
```

### Μέχρι συγκεκριμένη ημερομηνία

```text
Από: [Enter]
Έως: 2025-12-31
```

### Συγκεκριμένο διάστημα

```text
Από: 2026-01-01
Έως: 2026-06-30
```

---

## Time Entries

Τα Time Entries φιλτράρονται με τις ίδιες ημερομηνίες Από / Έως.

Το φίλτρο βασίζεται στο:

```text
spent_on
```

και είναι ανεξάρτητο από το `created_on` / `updated_on` των issues.

---

## Τι εμφανίζεται κατά την εκτέλεση

Παράδειγμα:

```text
REDMINE FULL EXPORT

Redmine : https://redmine.dataverse.gr
Project : et-support
Filter  : created_on
From    : 2026-01-01
To      : 2026-06-30

Testing API access...
```

Αν η σύνδεση είναι επιτυχής:

```text
Connected. Project: ET Support (id=...)
```

Στη συνέχεια:

```text
Issues list: 100/1243
Issues list: 200/1243
...
```

και μετά:

```text
Fetching full details for 1243 issues...

Full issue: 1/1243 #12345
Full issue: 2/1243 #12346
...
```

Τέλος:

```text
Fetching time entries...
```

---

## Output

Το script δημιουργεί αυτόματα output directory.

Παράδειγμα:

```text
redmine_export_et-support_created_from_2026-01-01_to_2026-06-30/
```

Χωρίς ημερομηνιακό φίλτρο:

```text
redmine_export_et-support/
```

### Παράδειγμα δομής

```text
redmine_export_et-support_created_from_2026-01-01_to_2026-06-30/
│
├── et-support_full_export_created_from_2026-01-01_to_2026-06-30.xlsx
├── et-support_full_export_created_from_2026-01-01_to_2026-06-30.json
│
├── raw_issues/
│   ├── 12345.json
│   ├── 12346.json
│   └── ...
│
└── attachments/
    ├── 12345/
    │   ├── 1001_document.pdf
    │   └── 1002_image.png
    └── ...
```

---

## Excel worksheets

Το Excel περιλαμβάνει τα παρακάτω φύλλα.

### `Issues`

Περιλαμβάνει μεταξύ άλλων:

- ID
- Project
- Tracker
- Status
- Priority
- Author
- Assignee
- Category
- Version
- Parent issue
- Subject
- Description
- Created date
- Updated date
- Closed date
- Estimated hours
- Spent hours
- Custom Fields

### `Journals`

Περιλαμβάνει comments / notes:

- Issue ID
- Journal ID
- User
- Notes
- Private notes
- Created date

### `Journal_Details`

Περιλαμβάνει αλλαγές στα issues:

- status
- assignee
- priority
- custom fields
- άλλα changed fields

### `Attachments`

Περιλαμβάνει:

- Issue ID
- Attachment ID
- Filename
- File size
- Content type
- Author
- Created date
- Content URL
- Local path

### `Relations`

Περιλαμβάνει συσχετίσεις μεταξύ issues.

### `Children`

Περιλαμβάνει parent / child relationships και subtasks.

### `Time_Entries`

Περιλαμβάνει:

- User
- Issue
- Activity
- Hours
- Comments
- `spent_on`
- `created_on`
- `updated_on`

---

## JSON export

Το JSON είναι το πλήρες master export.

Διατηρεί την hierarchical δομή:

```text
Issue
├── custom fields
├── journals
│   └── details
├── attachments
├── relations
└── children
```

Για AI / data analysis συνιστάται το JSON να θεωρείται το βασικό dataset, επειδή διατηρεί την πλήρη αρχική δομή.

---

## Raw Issues

Στον φάκελο:

```text
raw_issues/
```

δημιουργείται ξεχωριστό JSON για κάθε issue.

Παράδειγμα:

```text
raw_issues/12345.json
```

Χρήσιμο για:

- debugging
- AI ingestion
- incremental processing
- έλεγχο συγκεκριμένου ticket

---

## Attachments

Αν:

```python
DOWNLOAD_ATTACHMENTS = True
```

δημιουργείται ξεχωριστός φάκελος ανά issue:

```text
attachments/<issue_id>/
```

Παράδειγμα:

```text
attachments/12345/
├── 1001_document.pdf
└── 1002_image.png
```

Το attachment ID χρησιμοποιείται ως prefix ώστε να αποφεύγονται filename collisions.

---

## Troubleshooting

### `python is not recognized`

Δοκίμασε:

```powershell
py --version
```

Αν δεν λειτουργεί, εγκατέστησε Python και βεβαιώσου ότι βρίσκεται στο PATH.

### `No module named requests`

Εκτέλεσε:

```powershell
py -m pip install -r requirements.txt
```

### `401 Unauthorized`

Έλεγξε:

- ότι το API key είναι σωστό
- ότι δεν έχει γίνει reset
- ότι ο χρήστης έχει πρόσβαση στο project

### `403 Forbidden`

Ο χρήστης/API key δεν έχει τα απαιτούμενα permissions.

### `404 Not Found`

Έλεγξε:

```python
REDMINE_URL = "https://redmine.dataverse.gr"
PROJECT_ID = "et-support"
```

### SSL / Certificate error

Μην απενεργοποιείς αυθαίρετα το SSL verification.

Έλεγξε πρώτα:

- certificate του Redmine
- certificate chain
- corporate proxy
- local trusted certificates

### Attachment download error

Το script συνεχίζει την εκτέλεση ακόμα και αν αποτύχει η λήψη κάποιου attachment.

Παράδειγμα:

```text
WARNING attachment ... failed
```

---

## Ασφάλεια

Μην αποθηκεύεις API keys μέσα στον Python source code.

Μην ανεβάζεις API keys σε:

- GitHub
- GitLab
- tickets
- documentation
- README files
- shared folders

Το script ζητά το API key κατά την εκτέλεση ώστε να μη βρίσκεται αποθηκευμένο στον κώδικα.

Αν κάποιο API key έχει ήδη εμφανιστεί σε public repository, πρέπει να γίνει reset / regeneration.

---

## `.gitignore`

Προτείνεται το repository να περιέχει:

```gitignore
__pycache__/
*.pyc

.env
.venv/
venv/

redmine_export_*/
*.xlsx
*.json

attachments/
raw_issues/
```

Με αυτόν τον τρόπο αποφεύγεται η κατά λάθος μεταφόρτωση:

- exports
- attachments
- local virtual environments
- `.env`
- generated JSON / Excel files

---

## Γρήγορη εκτέλεση

Σε νέο υπολογιστή:

```powershell
cd C:\RedmineExporter

py --version

py -m pip install -r requirements.txt

py redmine_full_export_with_dates.py
```

Στη συνέχεια:

```text
Redmine API key: <paste>

Επιλογή φίλτρου: 1 / 2 / 3

Από: YYYY-MM-DD

Έως: YYYY-MM-DD
```

---

## Προτεινόμενη χρήση repository

```text
RedmineExporter/
├── redmine_full_export_with_dates.py
├── requirements.txt
├── README.md
└── .gitignore
```

Δεν απαιτείται ούτε συνιστάται η αποθήκευση credentials μέσα στο repository.
