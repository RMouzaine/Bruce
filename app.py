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

# L'URL de votre emploi du temps universitaire
URL_ADE = "https://aderead.univ-orleans.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=0cb0acbfa10fd68c9769e63289f7d1483ed7389bc6dd2ee49782fad5fcaf7f5f4a2cea4e0ce85231d703b1edfe75344af6ed377fd569fdc9a44be0d5e17794f1b9d9678561997212cf33897c1d423e46577d226868daa6af56688876af752974,1"

# IMPORTANT : Assurez-vous que cette URL est bien celle du NOUVEL onglet "RMHoraires" 
# (le numéro après 'gid=' doit correspondre au bon onglet de votre fichier Google Sheets)
URL_DRIVE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHx5JoIBSJXZuYY22hS9ToHWcgy2Vyuw1cPtm_gIfw-I73RZOQ47HHh56ut9SOHInnWPZoUp90asvp/pub?gid=REMPLACEZ_CECI_PAR_LE_BON_GID&single=true&output=csv"


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
        lecteur = list(csv.reader(StringIO(reponse.text)))
        
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau)
        
        # Calcul du jour (Lundi = 0, Mardi = 1... Dimanche = 6)
        jour_py = aujourd_hui.weekday()
        offset_jour = 0 if jour_py == 6 else jour_py + 1
        
        # Détermination automatique du numéro de la semaine
        semaine_actuelle = aujourd_hui.isocalendar()[1]
        if jour_py == 6: 
            semaine_actuelle += 1
            
        recherche_sem = f"sem {semaine_actuelle}"
        dans_bonne_semaine = False
        
        for ligne in lecteur:
            if not ligne:
                continue
                
            texte_ligne0 = ligne[0].lower()
            
            if "date:" in texte_ligne
