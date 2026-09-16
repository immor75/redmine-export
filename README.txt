Πώς θα το τρέξεις στα Windows

Άνοιξε ένα Command Prompt ή PowerShell σε έναν φάκελο όπου έχεις κατεβάσει τα δύο αρχεία. Π.χ.:

cd C:\Users\Andreas\Downloads

Έλεγξε πρώτα ότι έχεις Python:

python --version

ή:

py --version

Αν σου εμφανίσει π.χ.:

Python 3.12.4

είσαι ΟΚ.

Μετά εγκατέστησε τις dependencies:

py -m pip install -r requirements.txt

ή, αν χρησιμοποιείς python:

python -m pip install -r requirements.txt

Και τρέξε:

py redmine_full_export.py

Θα σου ζητήσει:

Redmine API key:

Κάνε paste το νέο API key και Enter. Δεν θα εμφανίζεται στην οθόνη καθώς το γράφεις — αυτό είναι σκόπιμο για λόγους ασφαλείας.

Το script είναι ήδη ρυθμισμένο με:

REDMINE_URL = "https://redmine.dataverse.gr"
PROJECT_ID = "et-support"

οπότε αυτά δεν χρειάζεται να τα αλλάξεις.

Αρχικά θα δεις κάτι σαν:

Redmine: https://redmine.dataverse.gr
Project: et-support
Testing API access...

Connected. Project: ET Support (id=...)
Issues list: 100/2847
Issues list: 200/2847
...

και μετά:

Fetching full details for 2847 issues...

Full issue: 1/2847  #123
Full issue: 2/2847  #124
...

Αυτό το δεύτερο στάδιο είναι απαραίτητο επειδή τα πλήρη journals/comments δεν επιστρέφονται από το απλό /issues.json; πρέπει να ζητηθούν ανά issue μέσω /issues/{id}.json?include=journals....

Στο τέλος:

DONE
JSON:       ...\redmine_export_et-support\et-support_full_export.json
Excel:      ...\redmine_export_et-support\et-support_full_export.xlsx
Attachments:...\redmine_export_et-support\attachments
Raw issues: ...\redmine_export_et-support\raw_issues

Το script κατεβάζει και τα πραγματικά attachment files, όχι μόνο τα metadata. Το API του Redmine επιστρέφει content_url για κάθε attachment, μέσω του οποίου μπορεί να ληφθεί το αρχείο.

Μια σημαντική λεπτομέρεια: έχω βάλει

EXCLUDE_SUBPROJECTS = True

οπότε εξάγει μόνο tickets που ανήκουν στο et-support και όχι tickets από subprojects. Αυτό γίνεται με subproject_id=!*, που υποστηρίζεται από το Redmine API.

Επίσης κρατάω το JSON ως master export χωρίς flattening. Αυτό είναι σημαντικό για τη μετέπειτα AI ανάλυση που θέλουμε να κάνουμε στα support tickets, γιατί εκεί διατηρείται ολόκληρη η δομή issue → journals → details → attachments → relations. Το Excel είναι κυρίως για εύκολη ανθρώπινη ανάλυση.