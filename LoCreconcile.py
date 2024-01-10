#!/usr/bin/env python3
#
# A simple Flask app for Reconciling names and subject headings from the Library of Congress (LoC) using OpenRefine
# 
# Rewritten by:
#   Digitization Program Office
#   Office of the Chief Information Officer
#   Smithsonian Institution
# 

from flask import Flask
from flask import request
from flask import jsonify
from flask import json
from flask import url_for

# caching
from flask_caching import Cache

import sys
import os
import requests
import difflib
from urllib.parse import quote
from lxml import etree
from bs4 import BeautifulSoup
import logging
# from reconciliation import SearchLoC, Recon


sys.setrecursionlimit(10000)
ver = "2023-12-12"


# Cache config
config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 900
}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


class Recon:

    def __init__(self, score):
        """Turns the raw lists of scores and term-id pairs into objects"""
        self.score = score[0]
        self.header = score[1][0]
        self.uri = score[1][1]
        self.id = self.uri.split("/")[-1]

    def __str__(self):
        return str(self.header) + " (" + str(self.score) + ")"

    @staticmethod
    def reconcile(original, term_pairs, sort=False, limit=20):
        """appends a reconciliation score to each term-identifier pair"""
        recon_scores = []
        for tp in term_pairs:
            # NOTE: assumes 0th element of tuple == term
            term = tp[0].lower().replace("&amp;", "&")
            if term.endswith("."):
                term = term[:-1]
            sim_ratio = str(round(float(difflib.SequenceMatcher(
                None, original.lower(), term).ratio()), 3))
            recon_scores.append([sim_ratio, tp])
        if sort:
            return sorted(recon_scores,
                          key=lambda x: x[0],
                          reverse=True)[:limit]
        return recon_scores[:limit]


class SearchLoC:

    logging.basicConfig(level=logging.INFO)
    LOGGER = logging.getLogger(__name__)

    def __init__(self, term, term_type=''):
        self._term_type = term_type
        self.term = term
        self.suggest_uri = "https://id.loc.gov/authorities" + self.term_type + "/suggest/?q="
        self.__raw_uri_start = "https://id.loc.gov/search/?q="
        self.__raw_uri_end = "&q=cs%3Ahttp%3A%2F%2Fid.loc.gov%2Fauthorities%2F" + self.term_type[1:]

    def __str__(self):
        return str(self.search_terms())

    @property
    def _term_type(self):
        return self.term_type

    @_term_type.setter
    def _term_type(self, val):
        valid = ['', 'all', 'names', '/names', 'subjects', '/subjects']
        if val in valid:
            if val == 'all' or val == '':
                self.term_type = ''
            else:
                if not val.startswith('/'):
                    self.term_type = '/' + val
                else:
                    self.term_type = val
        else:
            self.term_type = ''

    def search_terms(self):
        """Looks for a term using the suggest API"""
        self.LOGGER.debug("HTTP request on Suggest API for {}".format(self.term))
        response = requests.get(self.suggest_uri + quote(self.term))
        result = response.json()
        return self.__process_results(result)

    @staticmethod
    def __process_results(results):
        """parse web results into term-id pairs"""
        id_pairs = []
        for i, _ in enumerate(results[1]):
            term_name = results[1][i]
            term_id = results[3][i]
            if term_id and term_name:
                id_pairs.append((term_name, term_id))
        return id_pairs

    def did_you_mean(self):
        dym_base = "https://id.loc.gov/authorities" + self.term_type + "/didyoumean/?label="
        dym_url = dym_base + quote(self.term)
        self.LOGGER.debug("querying didyoumean with URL {}".format(str(dym_url)))
        response = requests.get(dym_url)
        tree = etree.fromstring(response.content)
        return [(child.text, child.attrib['uri']) for child in iter(tree)]

    def search_terms_raw(self):
        """Switches to looking for a term by scraping the first web page of search results"""
        self.LOGGER.debug("Web scraping page 1 of web results...".format(self.term))
        search_uri = self.__raw_uri_start + quote(self.term) + self.__raw_uri_end
        response = requests.get(search_uri)
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('a', title="Click to view record")
        return self.__process_results_raw(search_results)

    def __process_results_raw(self, results):
        id_pairs = []
        for r in results:
            term_id_link = r.get('href').split('/')
            term_id = term_id_link[len(term_id_link)-1]
            heading = r.get_text()
            term_id = self.get_term_uri(term_id)
            if term_id and heading:
                id_pairs.append((heading, term_id))
        return id_pairs

    def full_search(self, suggest=True, didyoumean=True, scrape=True):
        """implement all 3 search methods (suggest, did you mean, and web sraping"""
        results = None
        if not suggest and not didyoumean and not scrape:
            return results
        if suggest:
            results = self.search_terms()  # start with suggest
        if not results and didyoumean:
            results = self.did_you_mean()
        if not results and scrape:
            results = self.search_terms_raw()  # wasn't found with "suggest", try scraping first page instead
        return results

    def get_term_uri(self, term_id, extension="html", include_ext=False):
        """return the URI of a term term, given the ID of the term"""
        term_uri = "https://id.loc.gov/authorities" + self.term_type + "/" + term_id
        if include_ext:
            return term_uri + "." + extension
        return term_uri



default_query = {
    "id": "LoC",
    "name": "LCNAF & LCSH",
    "index": "/authorities"
}

refine_to_lc = list([
    {
        "id": "Names",
        "name": "Library of Congress Name Authority File",
        "index": "/authorities/names"
    },
    {
        "id": "Subjects",
        "name": "Library of Congress Subject Headings",
        "index": "authorities/subjects"

    }
])
refine_to_lc.append(default_query)

query_types = [{'id': item['id'], 'name': item['name']} for item in refine_to_lc]

metadata = {
    "name": "LC Reconciliation Service",
    "identifierSpace" : "http://localhost/identifier",
    "schemaSpace" : "http://localhost/schema",
    "defaultTypes": query_types,
    "view": {
        "url": "{{id}}"
    },
    "preview": {
        "height": 440,
        "width": 600,
        "url":  "http://127.0.0.1:5000/reconcile/preview/?url={{id}}"
    }
}


def preprocess(token):
    if token.endswith("."):
        token = token[:-1]
    return token.lower().lstrip().rstrip().replace("--", " ").replace(", ", " ")\
        .replace("\t", "").replace("\n", "")
    # may add other preprocessing steps later


@cache.cached()
def search(search_in, query_type='', limit=3):
    scores = []
    term = preprocess(search_in)
    query_result = SearchLoC(term=term, term_type=query_type.lower()).full_search(suggest=True,
                                                                                  didyoumean=True,
                                                                                  scrape=True)
    recon_ = Recon.reconcile(search_in, query_result, sort=True, limit=limit)
    for r in recon_:
        match = False
        recon_result = Recon(r)
        # logging.info("Recon object: " + str(recon_result))
        if recon_result.score == "1.0":
            match = True  # auto-match for perfect results

        scores.append({
            "id": str(recon_result.uri),
            "name": recon_result.header,
            "score": recon_result.score,
            "match": match,
            "type": metadata['defaultTypes'],
        })
    return scores


def jsonpify(obj):
    try:
        callback = request.args['callback']
        response = app.make_response("%s(%s)" % (callback, json.dumps(obj)))
        response.mimetype = "text/javascript"
        return response
    except KeyError:
        return jsonify(obj)


@app.route("/reconcile/LoC", methods=['POST', 'GET'])
def reconcile():
    queries = request.form.get('queries')
    if queries:
        # logging.info("queries: " + str(queries))
        queries = json.loads(queries)
        results = {}
        for (key, query) in queries.items():
            qtype = query.get('type')
            if qtype is None:
                return jsonpify(metadata)
            limit = 3
            if 'limit' in query:
                limit = int(query['limit'])
            data = search(query['query'], query_type=qtype, limit=limit)
            results[key] = {"result": data}
        return jsonpify(results)
    return jsonpify(metadata)


@cache.memoize()
def url_prev(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    text_body = soup.find(id="tab1")
    text_body.find("div", class_="bf-render-right").decompose()
    new_link = soup.new_tag("style")
    # Relevant css from loc_standard_v2_w.css
    new_link.string = """a#skip {
                position: absolute;
                top:-100px;
                }
                a:link {
                color: #036;
                text-decoration: underline;
                }
                a:visited {
                color: #609;
                }
                a:focus,
                a:hover,
                a:active {
                color: #36c;
                text-decoration: underline;
                }
                body {
                font-size: 75%; /* 12px */
                line-height: 1.4;
                font-family:Arial, Helvetica, sans-serif;
                color: #333;
                background-color: #fff;
                }
                h1, h2, h3 {font-family:Arial, Helvetica, sans-serif;}
                h1 {font-size: 1.6em;color:#343268;}
                h2, h3 {font-size: 1.2em;margin: 0 0 0.4em 0;color:#36C;}
                h3, h4, h5, h6 {color:#666;}
                h4 {font-size: 1em;margin: 0 0 0.2em 0;color:#333;}
                h5 {font-size: 1em;}
                h6 {font-size: 1em;}
                p, dl {margin: 0 0 1.25em 0;}
                ul, ol {margin: 0 0 1.25em 0; padding-left: 2.5em;}
                dt {margin: 0 0 0.5em 0;font-weight:bold;}
                dd {margin: 0 0 0.5em 2.5em;}
                pre, code, tt {margin: 0 0 1em 0; font-family:"Courier New", Courier, monospace;}"""
    text_body.insert(0, new_link)
    for a_tag in text_body.find_all('a'):
        a_string = a_tag.string
        new_div = soup.new_tag("div")
        new_div.string = a_string
        a_tag.replace_with(new_div)
    for img in text_body.find_all('img'):
        img.decompose()
    return text_body


@app.route("/reconcile/preview/", methods=['GET'])
def recon_preview():
    name_url = request.args.get('url')
    page_preview = url_prev(name_url)
    return str(page_preview)


@app.route("/")
def render_index():
    return "LoC Reconciliation Service is running at this port!"


if __name__ == "__main__":
    print("\n LoC Reconciliation Service\n https://github.com/Smithsonian/LoC-reconcile/\n   ver: {}\n\n Use the address: http://127.0.0.1:5000/reconcile/LoC\n".format(ver))
    app.run(debug=False)
    # default service URL: http://127.0.0.1:5000/reconcile/LoC
