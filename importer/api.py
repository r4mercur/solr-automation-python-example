from flask import Flask, request, jsonify

from solr.util import get_solr_client

app = Flask(__name__)
solr = get_solr_client()


@app.route("/import", methods=["POST"])
def import_user():
    try:
        data = request.data
        if not data:
            return jsonify({"error": "No data provided"}), 400

        solr.add(data)
        solr.commit()
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
