from flask import Flask, render_template, redirect, url_for, jsonify
import pandas as pd
import numpy as np
import os

def LoadData(filename, elementsToInclude = 3):
    # Load raw values in
    rawData = pd.read_csv(os.path.join("data", filename)).values
    
    # Find the unique entries in the first col
    categories = np.unique(rawData[:, 0].astype(str))
    
    # Create dictionary to hold the full data
    data = dict()
    
    # For each category, find all related subcodes
    for category in categories:
        catDict = dict()
        locs = np.where(rawData == category)[0]
        
        for loc in locs:
            if elementsToInclude == 2:
                data[rawData[loc, 0]] = rawData[loc,  1]
                continue
            for x in range(elementsToInclude):
                catDict[rawData[loc, 1]] = rawData[loc, 2]
        
        if not elementsToInclude == 2:
            data[category] = catDict
    
    # Return the dict
    return data

def ReturnAllCodes(taxonomy):
    if (taxonomy == "Cl"):
        return list(classifications.keys())
    elif (taxonomy == "Modality"):
        return list(modalities.keys())
    elif (taxonomy == "PS"):
        codes = []
        for category in pathwaySubcodes.keys():
            codes += list(pathwaySubcodes[category].keys())
        return codes
    elif (taxonomy == "MD"):
        codes = []
        for category in pathwaySubcodes.keys():
            codes += list(pathwaySubcodes[category].keys())
        for index in range(len(codes)):
            codes[index] = "MD" + codes[index]
        return codes
    elif (taxonomy == "CF"):
        codes = []
        for category in contributoryFactors.keys():
            codes += list(contributoryFactors[category].keys())
        return codes

def SanatiseCodes(codes):
    allClassifications = ReturnAllCodes("Cl")
    allPathwayCodes = ReturnAllCodes("PS")
    allMethodsOfDetection = ReturnAllCodes("MD")
    allCausitiveFactors = ReturnAllCodes("CF")
    allModalities = ReturnAllCodes("Modality")

    CL = []
    PPS = []
    APS = []
    MD = []
    CFs = []
    Modality = []

    for code in codes.replace(" ", "").split("/"):
        lower_code = code.lower()  # Convert the user input code to lower case
        matchingCL = next((original for original in allClassifications
                           if original.replace(" ", "").lower() == lower_code.replace(" ", "")), None)
        matchingPPS = []
        matchingAPS = next((original for original in allPathwayCodes
                           if original.replace(" ", "").lower() == lower_code), None)
        matchingMD = next((original for original in allMethodsOfDetection
                           if original.replace(" ", "").lower() == lower_code), None)
        matchingCF = next((original for original in allCausitiveFactors
                           if original.replace(" ", "").lower() == lower_code.replace(" ", "")), None)
        matchingModality = next((original for original in allModalities
                           if original.replace(" ", "").lower() == lower_code.replace(" ", "")), None)
        
        if matchingCL is not None:
            CL.append(matchingCL)
        # Sort out matchingPPS later
        elif matchingAPS is not None:
            APS.append(matchingAPS)
        elif matchingMD is not None:
            MD.append(matchingMD)
        elif matchingCF is not None:
            CFs.append(matchingCF)
        elif matchingModality is not None:
            Modality.append(matchingModality)
    
     # Remove duplicates
    CL = list(set(CL))
    PPS = PPS
    APS = list(set(APS))
    MD = list(set(MD))
    CFs = list(set(CFs))
    Modality = list(set(Modality))

    if len(CL) > 1:
        CL = []
    if len(MD) > 1:
        MD = []
    if len(Modality) > 1:
        Modality = []
    
    return CL, PPS, APS, MD, CFs, Modality


pathwaySubcodes = LoadData("Pathway Subcodes.csv")
contributoryFactors = LoadData("Contributory Factors.csv")
classifications = LoadData("Classification.csv", 2)
modalities = LoadData("Modality.csv", 2)

app = Flask(__name__)

@app.after_request
def allow_iframe(response):
    # Remove any restrictive headers
    response.headers.pop('X-Frame-Options', None)
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

@app.route("/api/classification")
def api_classification():
    return jsonify(classifications)

@app.route("/api/pathwaysubcodes", defaults={"category": None})
@app.route("/api/pathwaysubcodes/<path:category>")
def api_pathway(category=""):
    if category is None:
        return jsonify(sorted(list(pathwaySubcodes.keys()), key = lambda x: int(x.split(" ")[0])))
    if category in pathwaySubcodes:
        return jsonify(pathwaySubcodes[category])
    else:
        return jsonify({"error": f"Category '{category}' not found"}), 404

@app.route("/api/contributoryfactors", defaults={"category": None})
@app.route("/api/contributoryfactors/<path:category>")
def api_causative(category):
    if category is None:
        return jsonify(sorted(list(contributoryFactors.keys()), key = lambda x: int(x[2])))
    return jsonify(contributoryFactors[category])

@app.route("/api/modality")
def api_modality():
    return jsonify(modalities)

@app.route("/TSRT9/<path:code>")
@app.route("/TSRT9 /<path:code>")
@app.route("/")
def home(code = ""):
    code = code.replace(" ", "")
    return render_template("home.html", initialCode = code)

@app.route("/widget/TSRT9/<path:code>")
@app.route("/widget/TSRT9 /<path:code>")
@app.route("/widget")
def widget(code = ""):
    code = code.replace(" ", "")
    CL, PPS, APS, MD, CFs, Modality = SanatiseCodes(code)
    return render_template("widget.html",
                       ClTaxonomy=CL, PPSTaxonomy=PPS, APSTaxonomy=APS, MDTaxonomy=MD, CFTaxonomy=CFs, modalityTaxonomy = Modality)

@app.route("/widget/<taxonomy>/TSRT9/<path:code>")
@app.route("/widget/<taxonomy>/TSRT9 /<path:code>")
@app.route("/widget/<taxonomy>")
def widgetSingle(taxonomy, code=""):
    code = code.replace(" ", "")
    CL, PPS, APS, MD, CFs, Modality = SanatiseCodes(code)
    return render_template("widget.html", singleTaxonomy=taxonomy,
                           ClTaxonomy=CL, PPSTaxonomy=PPS, APSTaxonomy=APS, MDTaxonomy=MD, CFTaxonomy=CFs, modalityTaxonomy = Modality)

@app.route("/webdeveloperinformation")
def web_developer_information():
    return render_template("webdeveloperinformation.html")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)