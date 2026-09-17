# Redmine Full Exporter

Python exporter για πλήρες export από Redmine project.

Υποστηρίζει:

- Issues
- Journals / Comments
- Journal field changes
- Issue attachments
- Relations
- Subtasks / Children
- Time Entries
- Wiki Pages σε αυθεντικό Textile
- Wiki attachments
- Προαιρετικό πλήρες Wiki version history
- JSON και Excel output
- Χρονικό φίλτρο για issues

## Δομή repository

```text
RedmineExporter/
├── redmine_full_export_with_wiki.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Προαπαιτούμενα

Python 3.10+.

```powershell
py --version
```

## Εγκατάσταση

```powershell
cd C:\RedmineExporter
py -m pip install -r requirements.txt
```

## Εκτέλεση

```powershell
py redmine_full_export_with_wiki.py
```

Το script ζητά το Redmine API key κατά την εκτέλεση.

## Issue date filters

```text
1 = created_on
2 = updated_on
3 = χωρίς φίλτρο
```

Οι ημερομηνίες δίνονται σε μορφή:

```text
YYYY-MM-DD
```

## Wiki Export

Κατά την εκτέλεση:

```text
Export Wiki pages? [Y/n]:
Export Wiki attachments? [Y/n]:
Export Wiki version history? [y/N]:
```

Κάθε wiki page αποθηκεύεται σε Textile:

```text
wiki/<PageTitle>.textile
```

και σε raw JSON:

```text
wiki_raw/<PageTitle>.json
```

Δημιουργείται επίσης:

```text
wiki/index.json
```

Τα attachments αποθηκεύονται σε:

```text
wiki_attachments/<PageTitle>/
```

Αν ενεργοποιηθεί το version history:

```text
wiki_history/<PageTitle>/
├── v0001.textile
├── v0001.json
├── v0002.textile
├── v0002.json
└── ...
```

## Output

```text
redmine_export_et-support_.../
├── ...full_export.xlsx
├── ...full_export.json
├── raw_issues/
├── attachments/
├── wiki/
├── wiki_raw/
├── wiki_attachments/
└── wiki_history/
```

## Excel worksheets

```text
Issues
Journals
Journal_Details
Attachments
Relations
Children
Time_Entries
Wiki_Pages
```

Αν ενεργοποιηθεί Wiki version history:

```text
Wiki_History
```

## Ασφάλεια

Μην ανεβάζεις στο GitHub:

- API keys
- exports
- attachments
- customer data
- generated JSON / Excel files

## Προτεινόμενο .gitignore

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
wiki/
wiki_raw/
wiki_attachments/
wiki_history/
```
