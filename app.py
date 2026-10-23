import os
import random
import requests
import csv
from io import StringIO
from datetime import datetime
import pytz
from icalendar import Calendar
from flask import Flask, jsonify

app = Flask(__name__)

TITRES = ["Monsieur", "Sir", "Excellence", "Boss", "Patron", "Mentor"]
ACCROCHES = ["Salutations distinguées,", "Les systèmes sont opérationnels,", "Rapport de situation prêt,", "À vos ordres,"]

URL_ADE = "https://aderead.univ-orleans.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=0cb0acbfa10fd68c9769e63289f7d1483ed7389bc6dd2ee49782fad5fcaf7f5f4a2cea4e0ce85231d703b1edfe75344af6ed377fd569fdc9a44be0d5e17794f1b9d9678561997212cf33897c1d423e46577d226868daa6af56688876af752974,1"
URL_DRIVE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHx5JoIBSJXZuYY22hS9ToHWcgy2Vyuw1cPtm_gIfw-I73RZOQ47HHh56ut9SOHInnWPZoUp90asvp/pub?gid=961193327&single=true&output=csv"

def obtenir_meteo_et_conseil():
    try:
        # Coordonnées d'Orléans
        url_meteo = "https://api.open-meteo.com/v1/forecast?latitude=47.90&longitude=1.90&current_weather=true"
        reponse = requests.get(url_meteo).json()
        meteo = reponse.get("current_weather", {})
        
        temp = meteo.get("temperature", 0)
        code = meteo.get("weathercode", 0)
        
        if code in [0, 1]: condition = "Le ciel est dégagé"
        elif code in [2, 3]: condition = "Le ciel est nuageux"
        elif code in [45, 48]: condition = "Il y a du brouillard"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: condition = "Il pleut"
        elif code in [71, 73, 75, 85, 86]: condition = "Il neige"
        elif code in [95, 96, 99]: condition = "Il y a de l'orage"
        else: condition = "Le temps est mitigé"

        conseil = f"{condition} sur Orléans avec {temp} degrés. "
        
        if "pleut" in condition or "orage" in condition:
            conseil += "Je vous recommande de prendre une veste imperméable. Si vous avez entraînement ce soir, n'oubliez pas les coupe-vents pour les petits."
        elif temp < 10:
            conseil += "Les températures sont assez basses. Couvrez-vous bien, surtout si vous enchaînez les pistes au Drive."
        elif temp > 22:
            conseil += "Il fait particulièrement chaud. N'oubliez pas votre bouteille d'eau."
        else:
            conseil += "Les conditions météorologiques sont optimales pour votre journée."
            
        return conseil
    except Exception:
        return "Météo indisponible pour le moment."

def obtenir_cours_du_jour():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        reponse = requests.get(URL_ADE, headers=headers)
        cal = Calendar.from_ical(reponse.content)
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau).date()
        cours_liste = []
        for composant in cal.walk():
            if composant.name == "VEVENT":
                debut = composant.get('dtstart').dt
                date_evenement = debut.astimezone(fuseau).date() if hasattr(debut, 'astimezone') else (debut.date() if hasattr(debut, 'date') else debut)
                if date_evenement == aujourd_hui:
                    titre = str(composant.get('summary')).split('\n')[0].strip()
                    heure_debut = debut.astimezone(fuseau).strftime("%Hh%M")
                    fin = composant.get('dtend').dt.astimezone(fuseau).strftime("%Hh%M")
                    cours_liste.append(f"{titre} ({heure_debut}-{fin})")
        return " / ".join(cours_liste) if cours_liste else "Aucun cours aujourd'hui."
    except Exception as e:
        return f"Erreur ADE: {str(e)}"

def obtenir_horaires_drive():
    try:
        reponse = requests.get(URL_DRIVE)
        reponse.encoding = 'utf-8'
        lecteur = list(csv.reader(StringIO(reponse.text)))
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau)
        jour_py = aujourd_hui.weekday()
        offset_jour = 0 if jour_py == 6 else jour_py + 1
        semaine_actuelle = aujourd_hui.isocalendar()[1]
        if jour_py == 6: semaine_actuelle += 1
            
        recherche_sem = f"sem {semaine_actuelle}"
        dans_bonne_semaine = False
        
        for ligne in lecteur:
            if not ligne: continue
            texte_ligne0 = ligne[0].lower()
            if "date:" in texte_ligne0 and recherche_sem in texte_ligne0:
                dans_bonne_semaine = True
                continue
            if dans_bonne_semaine and "rayan" in texte_ligne0:
                valeurs_jours = ligne[2:]
                jours_extraits = []
                i = 0
                while len(jours_extraits) < 7 and i < len(valeurs_jours):
                    val = valeurs_jours[i].strip()
                    if val == "00:00" or val == "" or val.lower() == "repos":
                        jours_extraits.append("Repos")
                        if i + 2 < len(valeurs_jours):
                            v2, v3 = valeurs_jours[i+1].strip(), valeurs_jours[i+2].strip()
                            if (v2 == "00:00" or v2 == "") and (v3 == "00:00" or v3 == ""): i += 3
                            else: i += 1
                        else: i += 1
                    else:
                        if i + 1 < len(valeurs_jours):
                            jours_extraits.append(f"{val} à {valeurs_jours[i+1].strip()}")
                            i += 3
                        else: break
                return jours_extraits[offset_jour] if offset_jour < len(jours_extraits) else "Erreur colonnes"
            if dans_bonne_semaine and "date:" in texte_ligne0 and recherche_sem not in texte_ligne0: break
        return f"Erreur : Semaine {semaine_actuelle} introuvable."
    except Exception as e:
        return f"Erreur Drive: {str(e)}"

@app.route('/rapport/matin', methods=['GET'])
def route_matin():
    titre = f"{random.choice(ACCROCHES)} {random.choice(TITRES)}."
    
    cours_str = obtenir_cours_du_jour()
    drive_str = obtenir_horaires_drive()
    meteo_conseil = obtenir_meteo_et_conseil()
    
    fuseau = pytz.timezone('Europe/Paris')
    jour_py = datetime.now(fuseau).weekday()
    
    if jour_py == 0: coaching = "18h30 à 19h45 (Séance physique)"
    elif jour_py == 2: coaching = "18h30 à 19h45 (Séance tactique ludique)"
    else: coaching = "Aucun"
        
    if jour_py == 5: match = "Match aujourd'hui"
    else: match = "Aucun"
    
    corps = (
        f"Cours : {cours_str}\n"
        f"Drive : {drive_str}\n"
        f"Coaching : {coaching}\n"
        f"Match : {match}"
    )
    
    # La phrase générée spécifiquement pour être lue à haute voix par l'iPhone
    phrase_vocale = f"{titre} {meteo_conseil}"
    
    return jsonify({
        "sous_titre": titre,
        "corps": corps,
        "phrase_vocale": phrase_vocale
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
