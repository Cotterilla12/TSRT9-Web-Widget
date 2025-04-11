from flask import Flask, render_template, redirect, url_for, jsonify
import pandas as pd
import numpy as np
import os

def LoadData(filename):
    # Load raw values in
    rawData = pd.read_csv(os.path.join("data", filename)).values
    
    # Find the unique entries in the first col
    categories = np.unique(rawData[:, 0])
    
    # Data is of different sizes
    elementsToInclude = rawData.shape[1] - 2
    
    # Create dictionary to hold the full data
    data = dict()
    
    # For each category, find all related subcodes
    for category in categories:
        catDict = dict()
        locs = np.where(rawData == category)[0]
        
        for loc in locs:
            # Set list and grab all values needed
            entry = []

            if elementsToInclude == 1:
                catDict[rawData[loc, 1]] = rawData[loc,  2]
                continue
            for x in range(elementsToInclude):
                if isinstance(rawData[loc,  x + 2], float) and np.isnan(rawData[loc,  x + 2]):
                    continue
                entry.append(rawData[loc,  x + 2])
            
            catDict[rawData[loc, 1]] = entry
        
        data[category] = catDict
    
    # Return the dict
    return data

pathwayCodes = LoadData("Pathway Codes.csv")
causativeFactors = LoadData("Causative Factors.csv")
severityLevels = LoadData("Severity Levels.csv")

app = Flask(__name__)

@app.route("/api/severity")
def api_severity():
    return jsonify(severityLevels)

@app.route("/api/pathwaycodes", defaults={"category": None})
@app.route("/api/pathwaycodes/<path:category>")
def api_pathway(category=""):
    if category is None:
        return jsonify(sorted(list(pathwayCodes.keys()), key = lambda x: int(x.split(":")[0])))
    if category in pathwayCodes:
        return jsonify(pathwayCodes[category])
    else:
        return jsonify({"error": f"Category '{category}' not found"}), 404

@app.route("/api/causativefactors", defaults={"category": None})
@app.route("/api/causativefactors/<path:category>")
def api_causative(category):
    if category is None:
        return jsonify(sorted(list(causativeFactors.keys()), key = lambda x: int(x.split(":")[0])))
    return jsonify(causativeFactors[category])

@app.route("/TSRT9/<path:code>")
@app.route("/TSRT9")
@app.route("/")
def home(code = ""):
    code = code.replace(" ", "")
    return render_template("home.html", initialCode = code)

@app.route("/widget/TSRT9/<path:code>")
@app.route("/widget/TSRT9")
@app.route("/widget")
def widget(code = ""):
    code = code.replace(" ", "")
    return render_template("widget.html", initialCode = code)

@app.route("/widget/<taxonomy>/TSRT9/<path:code>")
@app.route("/widget/<taxonomy>")
def widgetSingle(taxonomy, code = ""):
    code = code.replace(" ", "")
    return render_template("widget.html", singleTaxonomy=taxonomy, initialCode=code)

if __name__ == "__main__":
    app.run(debug=True)
