import os
import random
import requests
import csv
from io import StringIO
from datetime import datetime
import pytz
from icalendar import Calendar
from flask import Flask, jsonify
import imaplib
import email
from email.header import decode_header

app = Flask(__name__)

TITRES = ["Monsieur", "Sir", "Excellence", "Boss", "Patron", "Mentor"]
ACCROCHES = ["Salutations distinguées,", "Les systèmes sont opérationnels,", "Rapport de situation prêt,", "À vos ordres,"]

CITATIONS_MOTIVANTES = [
    "N'oubliez pas : le succès, c'est de tomber sept fois et de se relever huit.",
    "La discipline est le pont entre les objectifs et les accomplissements.",
    "Chaque jour est une nouvelle opportunité de devenir la meilleure version de vous-même.",
    "Si tu pries pour qu'il y ait des fleurs, t'étonnes pas qu'il commence à pleuvoir.",
    "Allah n'impose à aucune âme une charge supérieur à sa capacité.",
    "Les diamants sont conçues sous la pression.",
    "la haine se transforme en dalle, la dalle se transforme en réussite.",
    "Rien ne te sera donné, va tout chercher.",
    "tu n'as aucun compte à rendre à personne, aucun.",
    "Certes avec la difficulté viens la facilité.",
    "Place ta confiance en Allah, Allah suffit comme garant.",
    "Le prophète a dit: rien ne sera plus lourd sur la balance du croyant que le bon caractère.",
    "Tu n'existe peut-être pas dans le futur dont t'es stressé.",
    "Demain tout ira mieux inshAllah.",
    "La seule limite à notre épanouissement de demain sera nos doutes d'aujourd'hui.",
    "Ce n'est pas l'aptitude, mais l'attitude, qui détermine votre altitude.",
    "Un voyage de mille lieues commence toujours par un premier pas.",
    "Faites de votre vie un rêve, et d'un rêve, une réalité.",
    "La motivation vous fait débuter, mais c'est l'habitude qui vous fait continuer.",
    "Le succès n'est pas final, l'échec n'est pas fatal : c'est le courage de continuer qui compte.",
    "Il n'y a pas d'ascenseur pour la réussite, il faut prendre l'escalier.",
    "La folie, c'est de faire toujours la même chose et de s'attendre à un résultat différent.",
    "Croyez en vous. Sachez qu'il y a quelque chose à l'intérieur de vous qui est plus grand que n'importe quel obstacle.",
    "Le meilleur moment pour planter un arbre était il y a 20 ans. Le deuxième meilleur moment est maintenant.",
    "Votre temps est limité, ne le gâchez pas en menant une existence qui n'est pas la vôtre.",
    "L'avenir appartient à ceux qui croient à la beauté de leurs rêves.",
    "Pour pouvoir accomplir de grandes choses, il faut d'abord y rêver.",
    "Le seul moyen de faire du bon travail, c'est d'aimer ce que vous faites.",
    "Ne regardez pas la montre ; faites comme elle. Avancez.",
    "Les gagnants trouvent des moyens, les perdants des excuses.",
    "Le succès est la somme de petits efforts, répétés jour après jour.",
    "L'action est la clé fondamentale de tout succès.",
    "Si vous traversez l'enfer, continuez d'avancer.",
    "La grandeur ne consiste pas à ne jamais tomber, mais à se relever après chaque chute.",
    "Tout ce que vous avez toujours voulu se trouve de l'autre côté de la peur.",
    "Le travail acharné bat le talent quand le talent ne travaille pas dur.",
    "Il est difficile de battre une personne qui n'abandonne jamais.",
    "Ne vous arrêtez pas quand vous êtes fatigué, arrêtez-vous quand vous avez terminé.",
    "La meilleure façon de prédire l'avenir est de le créer.",
    "Vous ne trouverez jamais ce que vous ne cherchez pas.",
    "Le succès, c'est d'aller d'échec en échec sans perdre son enthousiasme.",
    "Osez rêver. Osez essayer. Osez échouer. Osez réussir.",
    "Si l'opportunité ne frappe pas, construisez une porte."
]

TRANSITIONS_PROGRAMME = [
    "Voici le programme de votre journée :",
    "Passons maintenant en revue votre emploi du temps :",
    "Voici ce qui vous attend pour les prochaines heures :",
    "Consultons votre agenda du jour :",
    "Affichage de vos directives pour la journée :",
    "Je vous présente votre feuille de route :",
    "Initialisation du planning de la journée :",
    "Voici le détail de vos engagements d'aujourd'hui :",
    "Je charge votre emploi du temps. Le voici :",
    "Préparation de votre emploi du temps terminée. Voici les détails :"
]

ANNONCES_MAILS = [
    "Pour information, le compte-rendu de vos e-mails vous sera communiqué à 10 heures, {titre}.",
    "Je vous rappelle que votre briefing e-mails arrivera à 10 heures, {titre}.",
    "Le résumé complet de votre boîte de réception sera prêt pour 10 heures, {titre}."
]

CONCLUSIONS = [
    "Passez une excellente journée.",
    "Que votre journée soit des plus productives.",
    "Bon courage pour vos objectifs du jour.",
    "Force et honneur pour aujourd'hui.",
    "Je reste en veille. Excellente journée à vous."
]

URL_ADE = "https://aderead.univ-orleans.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=0cb0acbfa10fd68c9769e63289f7d1483ed7389bc6dd2ee49782fad5fcaf7f5f4a2cea4e0ce85231d703b1edfe75344af6ed377fd569fdc9a44be0d5e17794f1b9d9678561997212cf33897c1d423e46577d226868daa6af56688876af752974,1"
URL_DRIVE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHx5JoIBSJXZuYY22hS9ToHWcgy2Vyuw1cPtm_gIfw-I73RZOQ47HHh56ut9SOHInnWPZoUp90asvp/pub?gid=961193327&single=true&output=csv"

def obtenir_meteo_et_conseil():
    try:
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
            conseil += "Je vous recommande de prendre une veste imperméable. Si vous avez entraînement ce soir, n'oubliez pas les coupe-vents pour les petits. "
        elif temp < 10:
            conseil += "Les températures sont assez basses. Couvrez-vous bien. "
        elif temp > 22:
            conseil += "Il fait particulièrement chaud. N'oubliez pas votre bouteille d'eau. "
        else:
            conseil += "Les conditions météorologiques sont optimales pour votre journée. "
            
        return conseil
    except Exception:
        return "Météo indisponible pour le moment. "

def obtenir_cours_du_jour():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        reponse = requests.get(URL_ADE, headers=headers)
        cal = Calendar.from_ical(reponse.content)
