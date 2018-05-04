# A simple Flask app for Reconciling names and subject headings from the Library of Congress (LoC) using OpenRefine

from flask import Flask, request, jsonify, json
from reconciliation import SearchLoC, Recon


app = Flask(__name__)

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
    "defaultTypes": query_types,
    "view": {
        "url": "{{id}}"
    },
}


def preprocess(token):
    if token.endswith("."):
        token = token[:-1]
    return token.lower().lstrip().rstrip().replace("--", " ").replace(", ", " ")\
        .replace("\t", "").replace("\n", "")
    # may add other preprocessing steps later


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


@app.route("/")
def render_index():
    return "LoC Reconciliation Service is running at this port!"


if __name__ == "__main__":
    app.run(debug=True)
    # default service URL: http://127.0.0.1:5000/reconcile/LoC
