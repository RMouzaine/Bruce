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

URL_ADE = "https://aderead.univ-orleans.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=0cb0acbfa10fd68c9769e63289f7d1483ed7389bc6dd2ee49782fad5fcaf7f5f4a2cea4e0ce85231d703b1edfe75344af6ed377fd569fdc9a44be0d5e17794f1b9d9678561997212cf33897c1d423e46577d226868daa6af56688876af752974,1"
# J'ai ajouté /export?format=csv à la fin de votre lien pour éviter l'erreur de Raccourcis
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1CY5wtikz1j1smztGkEAyuwej8F_cus80mmRiEaWmIdM/export?format=csv"

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

def obtenir_derniers_mails():
    utilisateur = os.environ.get("GMAIL_USER")
    mot_de_passe = os.environ.get("GMAIL_PASS")
    
    if not utilisateur or not mot_de_passe:
        return "Les identifiants de messagerie ne sont pas configurés sur les serveurs."
        
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(utilisateur, mot_de_passe)
        mail.select("inbox")
        
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            return "Impossible d'accéder à l'interface de votre boîte de réception."
            
        id_list = messages[0].split()
        if not id_list:
            return "Votre boîte de réception est à jour. Aucun message prioritaire ne requiert votre attention pour le moment."
            
        # On réduit l'analyse aux 10 derniers e-mails non lus pour éviter les longs discours
        derniers_ids = id_list[-10:]
        mails_pro = []
        mails_perso = []
        nb_ignores = 0
        
        # Liste noire enrichie
        mots_promo = ['apple', 'under armour', 'zalando', 'pub', 'newsletter', 'promo', 'promotion', 'solde', 'offre spéciale', 'réduction', 'no-reply', 'noreply', 'ne-pas-repondre', 'marketing', 'unsubscribe', 'désinscription', 'spam', 'notification']
        # Liste professionnelle
        mots_pro = ['linkedin', 'candidature', 'entretien', 'indeed', 'recrutement', 'offre', 'stage', 'alternance', 'sopra', 'steria', 'auchan', 'cyber', 'pilote', 'informatique']
        
        for i in derniers_ids:
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sujet_complet = msg["Subject"]
                    sujet = "Sans objet"
                    if sujet_complet:
                        sujet_decode, encoding = decode_header(sujet_complet)[0]
                        if isinstance(sujet_decode, bytes):
                            sujet = sujet_decode.decode(encoding if encoding else "utf-8", errors="ignore")
                        else:
                            sujet = str(sujet_decode)
                            
                    expediteur_complet = msg.get("From")
                    exp_nom = "Expéditeur inconnu"
                    if expediteur_complet:
                        exp_decode, enc_exp = decode_header(expediteur_complet)[0]
                        if isinstance(exp_decode, bytes):
                            expediteur = exp_decode.decode(enc_exp if enc_exp else "utf-8", errors="ignore")
                        else:
                            expediteur = str(exp_decode)
                        exp_nom = expediteur.split('<')[0].strip()
                        
                    sujet_lower = sujet.lower()
                    exp_lower = expediteur.lower()
                    
                    est_promo = any(mot in sujet_lower or mot in exp_lower for mot in mots_promo)
                    est_pro = any(mot in sujet_lower or mot in exp_lower for mot in mots_pro)
                    
                    if est_promo:
                        nb_ignores += 1
                    elif est_pro:
                        mails_pro.append(f"De {exp_nom} concernant : {sujet}. ")
                    else:
                        mails_perso.append(f"De {exp_nom} concernant : {sujet}. ")
        
        mail.logout()
        
        discours = ""
        if nb_ignores > 0:
            discours += f"J'ai pris la liberté de filtrer {nb_ignores} courriels de type publicitaire ou automatisé. "
            
        if mails_pro:
            discours += "Concernant votre réseau professionnel et vos opportunités, vous avez reçu : "
            discours += " ".join(mails_pro) + " "
            
        if mails_perso:
            discours += "Pour vos autres correspondances importantes : "
            discours += " ".join(mails_perso) + " "
            
        if not mails_pro and not mails_perso and nb_ignores > 0:
            discours += "Aucun message important ne requiert votre attention immédiate."
            
        return discours
        
    except Exception as e:
        return "Une erreur de connexion aux serveurs Google est survenue lors de l'analyse."

@app.route('/rapport/matin', methods=['GET'])
def route_matin():
    titre_choisi = random.choice(TITRES)
    accroche = random.choice(ACCROCHES)
    titre_complet = f"{accroche} {titre_choisi}."
    
    intro_vocale = f"{titre_complet} Je suis Brousse, votre assistant personnel."
    
    cours_str = obtenir_cours_du_jour()
    drive_str = obtenir_horaires_drive()
    meteo_conseil = obtenir_meteo_et_conseil()
    
    fuseau = pytz.timezone('Europe/Paris')
    jour_py = datetime.now(fuseau).weekday()
    
    if jour_py == 0: coaching = "18h30 à 19h45 (Séance physique)"
    elif jour_py == 2: coaching = "18h30 à 19h45 (Séance tactique/ludique)"
    else: coaching = "Pas de coaching"
        
    if jour_py == 5: match = "Jour de match"
    else: match = "Pas de match prévu"
    
    corps = (
        f"Cours : {cours_str}\n"
        f"Drive : {drive_str}\n"
        f"Coaching : {coaching}\n"
        f"Match : {match}"
    )
    
    citation = random.choice(CITATIONS_MOTIVANTES)
    transition = random.choice(TRANSITIONS_PROGRAMME)
    
    cours_vocal = "Aucun cours à l'université aujourd'hui." if "Aucun" in cours_str else f"Côté université, vous avez : {cours_str}."
    drive_vocal = "Vous êtes en repos au Drive." if "Repos" in drive_str else f"Pour Auchan Drive, vous travaillez de {drive_str}."
    
    phrase_programme = f"{cours_vocal} {drive_vocal}"
    if coaching != "Pas de coaching":
        phrase_programme += f" Vous donnez entraînement de {coaching}."
    if match != "Pas de match prévu":
        phrase_programme += " Et vous avez un match aujourd'hui."
        
    annonce_mails = random.choice(ANNONCES_MAILS).format(titre=titre_choisi)
    
    conclusions_matin = [
        "Passez une excellente journée.",
        "Que votre journée soit des plus productives.",
        "Bon courage pour vos objectifs du jour.",
        "Force et honneur pour aujourd'hui.",
        "Je reste en veille. Excellente journée à vous."
    ]
    conclusion = random.choice(conclusions_matin)
    
    phrase_vocale = f"{intro_vocale} {meteo_conseil} {transition} {phrase_programme} {annonce_mails} {citation} {conclusion}"
    
    return jsonify({
        "sous_titre": titre_complet,
        "corps": corps,
        "phrase_vocale": phrase_vocale
    })

@app.route('/rapport/emails', methods=['GET'])
def route_emails():
    titres_jarvis = ["Monsieur", "Sir", "Boss"]
    titre_choisi = random.choice(titres_jarvis)
    
    intros_mails = [
        f"Salutations, {titre_choisi}. J'ai procédé à l'analyse de votre boîte de réception pour ces dernières heures. ",
        f"Bonjour, {titre_choisi}. Voici la synthèse de vos correspondances récentes. ",
        f"À vos ordres, {titre_choisi}. Je viens de terminer l'évaluation et le tri de vos messages entrants. "
    ]
    
    conclusions_mails = [
        f" C'est tout pour le moment. Je reste à votre entière disposition, {titre_choisi}.",
        f" Fin du rapport de communication. Je poursuis ma veille en arrière-plan, {titre_choisi}.",
        f" Vos systèmes de communication sont à jour. Excellente continuation, {titre_choisi}."
    ]
    
    intro = random.choice(intros_mails)
    conclusion = random.choice(conclusions_mails)
    contenu_mails = obtenir_derniers_mails()
    
    phrase_vocale = f"{intro} {contenu_mails} {conclusion}"
    
    return jsonify({
        "phrase_vocale": phrase_vocale
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
