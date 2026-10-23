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
                
                if hasattr(debut, 'date'):
                    date_evenement = debut.astimezone(fuseau).date() if hasattr(debut, 'astimezone') else debut.date()
                else:
                    date_evenement = debut
                    
                if date_evenement == aujourd_hui:
                    titre = str(composant.get('summary'))
                    titre = titre.split('\n')[0].strip()
                    heure_debut = debut.astimezone(fuseau).strftime("%Hh%M")
                    fin = composant.get('dtend').dt.astimezone(fuseau).strftime("%Hh%M")
                    cours_liste.append(f"{titre} ({heure_debut}-{fin})")
        
        if not cours_liste:
            return "Aucun cours aujourd'hui."
        return " / ".join(cours_liste)
        
    except Exception as e:
        return f"Erreur de lecture ADE: {str(e)}"

def obtenir_horaires_drive():
    try:
        reponse = requests.get(URL_DRIVE)
        reponse.encoding = 'utf-8'
        lecteur = csv.reader(StringIO(reponse.text))
        
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau)
        date_str = aujourd_hui.strftime("%d/%m") # Cherche "23/10"
        
        dates_trouvees = []
        index_col_date = -1
        
        for ligne in lecteur:
            if not ligne:
                continue
                
            # Si on lit une ligne de dates
            if "DATE" in ligne[0].upper():
                index_col_date = -1
                # On mémorise les dates trouvées pour le débogage
                dates_trouvees.extend([val.strip() for val in ligne[1:8] if val.strip()])
                
                for i, val in enumerate(ligne):
                    # Recherche plus souple (tolère les espaces ou années)
                    if date_str in val:
                        index_col_date = i
                        break
                        
            # Si la date a été trouvée, on cherche votre prénom (insensible aux majuscules)
            elif index_col_date != -1 and "RAYAN" in ligne[0].upper():
                col_debut = index_col_date * 3 - 1
                col_fin = index_col_date * 3
                
                if len(ligne) > col_fin:
                    debut = ligne[col_debut].strip()
                    fin = ligne[col_fin].strip()
                    
                    if (debut == "00:00" and fin == "00:00") or debut == "" or debut.lower() == "repos":
                        return "Repos"
                    else:
                        return f"{debut} à {fin}"
                else:
                    return "Repos"
                    
        # Si on arrive ici, il n'a pas trouvé aujourd'hui
        if not dates_trouvees:
            return "Erreur : Ligne 'DATE' introuvable dans le tableau."
            
        # Il va nous afficher les premières dates qu'il a réellement lues pour qu'on comprenne
        dates_vues = ", ".join(dates_trouvees[:4])
        return f"Date {date_str} introuvable (Dates vues: {dates_vues}...)"
        
    except Exception as e:
        return f"Erreur Drive: {str(e)}"

@app.route('/rapport/matin', methods=['GET'])
def route_matin():
    titre = f"{random.choice(ACCROCHES)} {random.choice(TITRES)}."
    
    cours_str = obtenir_cours_du_jour()
    drive_str = obtenir_horaires_drive()
    
    coaching = "Aucun (test)"
    match = "Aucun (test)"
    
    corps = (
        f"Cours : {cours_str}\n"
        f"Drive : {drive_str}\n"
        f"Coaching : {coaching}\n"
        f"Match : {match}"
    )
    
    return jsonify({
        "sous_titre": titre,
        "corps": corps
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
