### Library of Congress Reconciliation Service for OpenRefine

The following is a web service that interacts with the [OpenRefine Reconciliation Service API](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API)
to [reconcile](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation) names from the Library of Congress Name Authority File ([LCNAF](http://id.loc.gov/authorities/names.html)) and
subjects from the Library of Congress Subject Headings ([LCSH](http://id.loc.gov/authorities/subjects.html)).

#### How does it work?

This service attempts to fetch names and subjects from the Library of Congress using the following methods sequentially:

* **suggest** - Query the Library of Congress using their suggest API, which returns a JSON list of the best suggestion(s). 
  * Example: [http://id.loc.gov/authorities/names/suggest/?q=Crane,%20Roy](http://id.loc.gov/authorities/names/suggest/?q=Crane,%20Roy)
* **didyoumean** - Query the Library of Congress using their didyoumean API, which returns an XML list of close matches to your query
  * Example: [http://id.loc.gov/authorities/names/didyoumean/?label=Crane%20Roy](http://id.loc.gov/authorities/names/didyoumean/?label=Crane%20Roy)
* **web scraping** - As a last resort, the service will perform web scraping on the first page of results for a search query of the 
name or subject. 
  * Example: [http://id.loc.gov/search/?q=Crane%2C+Roy....](http://id.loc.gov/search/?q=Crane%2C+Roy&q=cs%3Ahttp%3A%2F%2Fid.loc.gov%2Fauthorities%2Fnames)
    
The reconciliation score, which indicates how good the match is, is determined using the Python [difflib](https://docs.python.org/3/library/difflib.html) library.


#### Installation

* Ensure Python 3 is installed. This program was developed with Python 3.4.3.
* Download this repository locally (`git clone` or `.zip`)
* Navigate to your local copy of the program in the command line interface
* Install the program requirements by typing `python -m pip install -r requirements.txt`
* Start the program by typing `python LoCreconcile.py` (or run in IDLE or another IDE)

#### Usage in OpenRefine

* Click the arrow in the title column of the column of names and/or subjects you wish to reconcile.
* Click `Reconcile > Start reconciling...`
* Click the `Add Standard Service...` button in the bottom left of the reconciliation menu
* Under `Enter the service's URL`, enter the URL `http://127.0.0.1:5000/reconcile/LoC`
* Note that after the service is added once per the previous steps, you will simply be able to select "LC Reconciliation Service" from the reconciliation menu in the future.
* In the following menu, `Names` reconciles from LCNAF, `Subjects` reconciles from LCSH, and `LoC` reconciles from both.
* Having `Auto-match candidates with high confidence` selected will automatically reconcile perfect matches
* If you do not quantify `Maximum number of candidates to return`, the program will attempt to return up to 3 candidate matches
for each name/subject. 
* Click `Start Reconciling`

#### Interpreting the Results

The results of reconciliation will be links to URIs of the best matching names and subjects the service could find.

Example: [http://id.loc.gov/authorities/names/n85243950](http://id.loc.gov/authorities/names/n85243950.html)

One of the best ways to expedite the reconciliation process is to start by exploring names which were near-perfect matches, having 
reconciliation scores of .80+ first, using the `best candidate's score` facet, continuing to decrement the score range until the matches no longer seem 
correct. Consult the OpenRefine wiki pages on [reconciliation](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation)
 and the [Reconciliation Service API](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API) for more information. You can also search the web for guides, 
 such as [this one](http://freeyourmetadata.org/reconciliation/). 

Other reconciliation services:
  * Christina Harlow's [lc-reconcile](https://github.com/cmh2166/lc-reconcile)
  * codeforkjeff's [conciliator](https://github.com/codeforkjeff/conciliator) (for LC identifiers via VIAF, plus much more)
  * A list of services from the [OpenRefine Wiki](https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#examples).

 