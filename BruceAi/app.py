"""
Bruce AI / Orayzis - Enterprise Secured Assistant API
Fully hardened production backend with rate limiting, bearer authentication,
security headers, CORS validation, XSS protection, zero exposed secrets,
and secure SQLite database audit logging.
"""

import os
import sys
import csv
import re
import random
import socket
import logging
from io import StringIO
from datetime import datetime
import pytz
import requests
from icalendar import Calendar
from flask import Flask, jsonify, request, make_response
import imaplib
import email
from email.header import decode_header

# Optional dotenv loading for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from security import (
    require_api_key,
    require_admin,
    rate_limit,
    apply_security_headers,
    handle_cors,
    sanitize_text,
    sanitize_payload,
    safe_compare
)
from database import (
    init_db,
    verify_user_credentials,
    get_recent_audit_logs,
    create_user
)

# ------------------------------------------------------------------------------
# Logging & Flask Configuration
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bruce.app")

app = Flask(__name__)

# Security configuration
app.config["DEBUG"] = False
app.config["TESTING"] = False
app.config["PROPAGATE_EXCEPTIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024  # 32 KB maximum request payload to prevent memory exhaustion DoS
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())

# Initialize database schema safely
try:
    init_db(admin_initial_password=os.environ.get("ADMIN_INITIAL_PASSWORD"))
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

# ------------------------------------------------------------------------------
# Constant Pools & Configurable Environment Variables
# ------------------------------------------------------------------------------
TITRES = ["Monsieur", "Sir", "Excellence", "Boss", "Patron", "Mentor"]
ACCROCHES = [
    "Salutations distinguées,",
    "Les systèmes sont opérationnels,",
    "Rapport de situation prêt,",
    "À vos ordres,"
]

CITATIONS_MOTIVANTES = [
    "N'oubliez pas : le succès, c'est de tomber sept fois et de se relever huit.",
    "La discipline est le pont entre les objectifs et les accomplissements.",
    "Chaque jour est une nouvelle opportunité de devenir la meilleure version de vous-même.",
    "Les diamants sont conçus sous la pression.",
    "Rien ne te sera donné, va tout chercher.",
    "La seule limite à notre épanouissement de demain sera nos doutes d'aujourd'hui.",
    "Ce n'est pas l'aptitude, mais l'attitude, qui détermine votre altitude.",
    "Un voyage de mille lieues commence toujours par un premier pas.",
    "Faites de votre vie un rêve, et d'un rêve, une réalité.",
    "La motivation vous fait débuter, mais c'est l'habitude qui vous fait continuer.",
    "Le succès n'est pas final, l'échec n'est pas fatal : c'est le courage de continuer qui compte.",
    "Il n'y a pas d'ascenseur pour la réussite, il faut prendre l'escalier.",
    "Le meilleur moment pour planter un arbre était il y a 20 ans. Le deuxième meilleur moment est maintenant.",
    "L'action est la clé fondamentale de tout succès.",
    "La meilleure façon de prédire l'avenir est de le créer."
]

TRANSITIONS_PROGRAMME = [
    "Voici le programme de votre journée :",
    "Passons maintenant en revue votre emploi du temps :",
    "Voici ce qui vous attend pour les prochaines heures :",
    "Consultons votre agenda du jour :",
    "Je vous présente votre feuille de route :",
    "Voici le détail de vos engagements d'aujourd'hui :"
]

ANNONCES_MAILS = [
    "Pour information, le compte-rendu de vos e-mails vous sera communiqué à 10 heures, {titre}.",
    "Je vous rappelle que votre briefing e-mails arrivera à 10 heures, {titre}.",
    "Le résumé complet de votre boîte de réception sera prêt pour 10 heures, {titre}."
]

# Sensitive external feed URLs loaded strictly from environment variables
URL_ADE = os.environ.get("ADE_ICAL_URL", "")
URL_DRIVE = os.environ.get("DRIVE_CSV_URL", "")
SCHEDULE_USER = os.environ.get("SCHEDULE_USER_NAME", "orayzis").lower()

# ------------------------------------------------------------------------------
# Core Helper Functions with Hardening
# ------------------------------------------------------------------------------
def extraire_temps(horaire_str: str):
    """
    Extracts start and end times in minutes from an hour string with strict ReDoS boundaries.
    """
    if not horaire_str or not isinstance(horaire_str, str) or len(horaire_str) > 100:
        return None, None
    matches = re.findall(r'(\d{1,2})[h:](\d{2})', horaire_str)
    if len(matches) >= 2:
        try:
            start = int(matches[0][0]) * 60 + int(matches[0][1])
            end = int(matches[-1][0]) * 60 + int(matches[-1][1])
            return start, end
        except ValueError:
            return None, None
    return None, None


def obtenir_meteo_et_conseil() -> str:
    """
    Retrieves weather forecast from Open-Meteo with network timeout bounds.
    """
    try:
        url_meteo = "https://api.open-meteo.com/v1/forecast?latitude=47.90&longitude=1.90&current_weather=true"
        # Network timeout of 4 seconds to prevent thread stalling
        reponse = requests.get(url_meteo, timeout=4.0)
        reponse.raise_for_status()
        data = reponse.json()
        meteo = data.get("current_weather", {})
        
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
            conseil += "Je vous recommande de prendre une veste imperméable. "
        elif temp < 10:
            conseil += "Les températures sont fraîches. Couvrez-vous bien. "
        elif temp > 22:
            conseil += "Les températures sont chaudes. Pensez à vous hydrater. "
        else:
            conseil += "Les conditions météorologiques sont optimales. "
            
        return conseil
    except Exception as e:
        logger.warning(f"Erreur service météo: {e}")
        return "Météo locale actuellement indisponible. "


def obtenir_cours_du_jour() -> str:
    """
    Retrieves calendar events from private iCal with timeout and parsing safeguards.
    """
    if not URL_ADE:
        return "Flux d'agenda non configuré (ADE_ICAL_URL requis)."
        
    try:
        headers = {'User-Agent': 'Orayzis-Bruce/1.2 (Security Hardened)'}
        reponse = requests.get(URL_ADE, headers=headers, timeout=5.0)
        reponse.raise_for_status()
        cal = Calendar.from_ical(reponse.content)
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau).date()
        cours_liste = []
        for composant in cal.walk():
            if composant.name == "VEVENT":
                dtstart = composant.get('dtstart')
                if not dtstart:
                    continue
                debut = dtstart.dt
                date_evenement = debut.astimezone(fuseau).date() if hasattr(debut, 'astimezone') else (debut.date() if hasattr(debut, 'date') else debut)
                if date_evenement == aujourd_hui:
                    titre = sanitize_text(str(composant.get('summary', 'Événement')).split('\n')[0].strip(), max_length=60)
                    heure_debut = debut.astimezone(fuseau).strftime("%Hh%M")
                    dtend = composant.get('dtend')
                    fin = dtend.dt.astimezone(fuseau).strftime("%Hh%M") if dtend else "inconnue"
                    cours_liste.append(f"{titre} ({heure_debut}-{fin})")
        return " / ".join(cours_liste) if cours_liste else "Aucune obligation académique aujourd'hui."
    except Exception as e:
        logger.warning(f"Erreur parsing iCal: {e}")
        return "Données d'agenda indisponibles pour le moment."


def obtenir_horaires_drive() -> str:
    """
    Fetches schedules from private CSV feed with bounded timeout and safe string matching.
    """
    if not URL_DRIVE:
        return "Flux de planning non configuré (DRIVE_CSV_URL requis)."
        
    try:
        reponse = requests.get(URL_DRIVE, timeout=5.0)
        reponse.raise_for_status()
        reponse.encoding = 'utf-8'
        lecteur = list(csv.reader(StringIO(reponse.text)))
        fuseau = pytz.timezone('Europe/Paris')
        aujourd_hui = datetime.now(fuseau)
        jour_py = aujourd_hui.weekday()
        offset_jour = 0 if jour_py == 6 else jour_py + 1
        semaine_actuelle = aujourd_hui.isocalendar()[1]
        if jour_py == 6: 
            semaine_actuelle += 1
            
        recherche_sem = f"sem {semaine_actuelle}"
        dans_bonne_semaine = False
        
        for ligne in lecteur:
            if not ligne: 
                continue
            texte_ligne0 = ligne[0].lower()
            if "date:" in texte_ligne0 and recherche_sem in texte_ligne0:
                dans_bonne_semaine = True
                continue
            if dans_bonne_semaine and SCHEDULE_USER in texte_ligne0:
                valeurs_jours = ligne[2:]
                jours_extraits = []
                i = 0
                while len(jours_extraits) < 7 and i < len(valeurs_jours):
                    val = valeurs_jours[i].strip()
                    if val in ("00:00", "", "repos", "Repos"):
                        jours_extraits.append("Repos")
                        if i + 2 < len(valeurs_jours):
                            v2, v3 = valeurs_jours[i+1].strip(), valeurs_jours[i+2].strip()
                            if v2 in ("00:00", "") and v3 in ("00:00", ""): 
                                i += 3
                            else: 
                                i += 1
                        else: 
                            i += 1
                    else:
                        if i + 1 < len(valeurs_jours):
                            val_clean = sanitize_text(val, 15)
                            val_fin = sanitize_text(valeurs_jours[i+1].strip(), 15)
                            jours_extraits.append(f"{val_clean} à {val_fin}")
                            i += 3
                        else: 
                            break
                return jours_extraits[offset_jour] if offset_jour < len(jours_extraits) else "Créneau non répertorié"
            if dans_bonne_semaine and "date:" in texte_ligne0 and recherche_sem not in texte_ligne0: 
                break
        return "Repos"
    except Exception as e:
        logger.warning(f"Erreur parsing Drive CSV: {e}")
        return "Données de planning non synchronisées."


def obtenir_derniers_mails() -> str:
    """
    Connects to Gmail via IMAP over TLS with socket timeouts, strict subject sanitization,
    and protected credential handling.
    """
    utilisateur = os.environ.get("GMAIL_USER")
    mot_de_passe = os.environ.get("GMAIL_PASS")
    
    if not utilisateur or not mot_de_passe or mot_de_passe.startswith("your_"):
        return "Les identifiants sécurisés de messagerie ne sont pas configurés sur le serveur."
        
    # Enforce socket timeout to avoid hanging IMAP sessions
    socket.setdefaulttimeout(8.0)
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", port=993)
        mail.login(utilisateur, mot_de_passe)
        mail.select("inbox", readonly=True)  # Read-only flag protects against accidental state modification
        
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            return "Impossible d'accéder à la boîte de réception."
            
        id_list = messages[0].split()
        if not id_list:
            return "Votre boîte de réception est à jour. Aucun message prioritaire en attente."
            
        derniers_ids = id_list[-10:]
        mails_pro = []
        mails_perso = []
        nb_ignores = 0
        
        mots_promo = [
            'apple', 'under armour', 'zalando', 'pub', 'newsletter', 'promo', 'promotion',
            'solde', 'offre spéciale', 'réduction', 'no-reply', 'noreply', 'ne-pas-repondre',
            'marketing', 'unsubscribe', 'désinscription', 'spam', 'notification'
        ]
        mots_pro = [
            'linkedin', 'candidature', 'entretien', 'indeed', 'recrutement', 'offre',
            'stage', 'alternance', 'sopra', 'steria', 'orayzis', 'cyber', 'informatique'
        ]
        
        for i in derniers_ids:
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sujet_complet = msg.get("Subject", "")
                    sujet = "Sans objet"
                    if sujet_complet:
                        try:
                            sujet_decode, encoding = decode_header(sujet_complet)[0]
                            if isinstance(sujet_decode, bytes):
                                sujet = sujet_decode.decode(encoding if encoding else "utf-8", errors="ignore")
                            else:
                                sujet = str(sujet_decode)
                        except Exception:
                            sujet = "Objet non décodable"
                            
                    expediteur_complet = msg.get("From", "")
                    exp_nom = "Expéditeur inconnu"
                    if expediteur_complet:
                        try:
                            exp_decode, enc_exp = decode_header(expediteur_complet)[0]
                            if isinstance(exp_decode, bytes):
                                expediteur = exp_decode.decode(enc_exp if enc_exp else "utf-8", errors="ignore")
                            else:
                                expediteur = str(exp_decode)
                            exp_nom = expediteur.split('<')[0].strip()
                        except Exception:
                            exp_nom = "Expéditeur non décodable"
                        
                    # Strict sanitization against injection
                    sujet_clean = sanitize_text(sujet, 80)
                    exp_clean = sanitize_text(exp_nom, 50)
                    
                    sujet_lower = sujet_clean.lower()
                    exp_lower = exp_clean.lower()
                    
                    est_promo = any(mot in sujet_lower or mot in exp_lower for mot in mots_promo)
                    est_pro = any(mot in sujet_lower or mot in exp_lower for mot in mots_pro)
                    
                    if est_promo:
                        nb_ignores += 1
                    elif est_pro:
                        mails_pro.append(f"De {exp_clean} concernant : {sujet_clean}. ")
                    else:
                        mails_perso.append(f"De {exp_clean} concernant : {sujet_clean}. ")
        
        mail.logout()
        
        discours = ""
        if nb_ignores > 0:
            discours += f"J'ai pris la liberté de filtrer {nb_ignores} courriels automatisés. "
            
        if mails_pro:
            discours += "Sur le plan professionnel, vous avez reçu : "
            discours += " ".join(mails_pro) + " "
            
        if mails_perso:
            discours += "Pour vos autres correspondances : "
            discours += " ".join(mails_perso) + " "
            
        if not mails_pro and not mails_perso and nb_ignores > 0:
            discours += "Aucun message prioritaire ne requiert votre attention immédiate."
            
        return discours
        
    except Exception as e:
        logger.error(f"Erreur d'accès IMAP: {e}")
        return "Une anomalie de connexion au serveur de messagerie est survenue."

# ------------------------------------------------------------------------------
# Security Middleware (Headers & CORS)
# ------------------------------------------------------------------------------
@app.after_request
def after_request_security(response):
    response = apply_security_headers(response)
    response = handle_cors(response)
    return response


@app.route('/<path:path>', methods=['OPTIONS'])
def options_preflight(path):
    """
    Handles CORS preflight checks safely.
    """
    res = make_response('', 204)
    res = handle_cors(res)
    res = apply_security_headers(res)
    return res

# ------------------------------------------------------------------------------
# Standard Error Handlers (Zero Information Disclosure)
# ------------------------------------------------------------------------------
@app.errorhandler(400)
def handle_400(e):
    return jsonify({"status": "error", "error": "Bad Request", "message": "The request format is invalid."}), 400


@app.errorhandler(401)
def handle_401(e):
    return jsonify({"status": "error", "error": "Unauthorized", "message": "Authentication token missing or invalid."}), 401


@app.errorhandler(403)
def handle_403(e):
    return jsonify({"status": "error", "error": "Forbidden", "message": "Insufficient permissions to access this resource."}), 403


@app.errorhandler(404)
def handle_404(e):
    return jsonify({"status": "error", "error": "Not Found", "message": "The requested endpoint does not exist."}), 404


@app.errorhandler(405)
def handle_405(e):
    return jsonify({"status": "error", "error": "Method Not Allowed", "message": "HTTP method not supported."}), 405


@app.errorhandler(429)
def handle_429(e):
    return jsonify({"status": "error", "error": "Too Many Requests", "message": "Rate limit exceeded. Please back off."}), 429


@app.errorhandler(500)
def handle_500(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"status": "error", "error": "Internal Server Error", "message": "An unexpected error occurred. Administrators have been notified."}), 500

# ------------------------------------------------------------------------------
# Public & Demonstration Endpoints
# ------------------------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def health_check():
    """
    Public health check endpoint for monitoring (UptimeRobot, render keep-alive).
    Returns server status without exposing environment internals.
    """
    return jsonify({
        "status": "healthy",
        "service": "Bruce AI / Orayzis",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200


@app.route('/api/public-preview', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def public_preview():
    """
    Sanitized simulation endpoint providing safe mock briefings for web visitors.
    Does not require private API keys or expose personal data.
    """
    fuseau = pytz.timezone('Europe/Paris')
    jour_nom = datetime.now(fuseau).strftime("%A")
    return jsonify({
        "status": "preview",
        "assistant": "Bruce AI",
        "firm": "Orayzis",
        "phrase_vocale": f"Salutations. Je suis Bruce, votre assistant personnel développé par Orayzis. Tous les systèmes sont opérationnels pour ce {jour_nom}. Aucun conflit logistique détecté.",
        "meteo": "Ciel dégagé, 18°C. Conditions optimales.",
        "agenda": "Déploiement API & Supervision des flux sécurisés."
    }), 200


@app.route('/api/contact', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def contact_form():
    """
    Secure contact endpoint with strict payload sanitization and length limits.
    """
    if not request.is_json:
        return jsonify({"status": "error", "error": "Content-Type must be application/json"}), 400

    raw_data = request.get_json(silent=True) or {}
    data = sanitize_payload(raw_data)

    email_input = data.get("email", "")
    message_input = data.get("message", "")

    if not email_input or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_input):
        return jsonify({"status": "error", "error": "Adresse e-mail invalide"}), 400

    if not message_input or len(message_input) < 10:
        return jsonify({"status": "error", "error": "Le message doit contenir au moins 10 caractères"}), 400

    logger.info(f"Formulaire de contact reçu de: {email_input}")
    return jsonify({
        "status": "success",
        "message": "Votre message a été transmis en toute sécurité à l'équipe Orayzis."
    }), 200

# ------------------------------------------------------------------------------
# Protected Core Routes (Requiring Authentication & Rate Limiting)
# ------------------------------------------------------------------------------
@app.route('/rapport/matin', methods=['GET'])
@require_api_key
@rate_limit(max_requests=15, window_seconds=60)
def route_matin():
    """
    Morning briefing route protected by API Key authentication and rate limiting.
    """
    titre_choisi = random.choice(TITRES)
    accroche = random.choice(ACCROCHES)
    titre_complet = f"{accroche} {titre_choisi}."
    
    intro_vocale = f"{titre_complet} Je suis Bruce, votre assistant personnel développé par Orayzis."
    
    cours_str = obtenir_cours_du_jour()
    drive_str = obtenir_horaires_drive()
    meteo_conseil = obtenir_meteo_et_conseil()
    
    fuseau = pytz.timezone('Europe/Paris')
    jour_py = datetime.now(fuseau).weekday()
    
    coaching = "18h30 à 19h45 (Séance tactique)" if jour_py in (0, 2) else "Pas d'activité prévue"
    match = "Journée de compétition" if jour_py == 5 else "Pas de compétition"
    
    corps = (
        f"Agenda : {cours_str}\n"
        f"Planning : {drive_str}\n"
        f"Activités : {coaching}\n"
        f"Statut : {match}"
    )
    
    citation = random.choice(CITATIONS_MOTIVANTES)
    transition = random.choice(TRANSITIONS_PROGRAMME)
    
    cours_vocal = "Aucune obligation académique aujourd'hui." if "Aucun" in cours_str else f"Côté obligations, vous avez : {cours_str}."
    drive_vocal = "Vous êtes en repos professionnel." if "Repos" in drive_str else f"Pour vos engagements, vous êtes prévu de {drive_str}."
    
    phrase_programme = f"{cours_vocal} {drive_vocal}"
    if coaching != "Pas d'activité prévue":
        phrase_programme += f" Activité programmée de {coaching}."

    # Conflict detection algorithm
    blocks = []
    if "Aucun" not in cours_str and "indisponible" not in cours_str:
        cours_liste = cours_str.split(" / ")
        for c in cours_liste:
            s, e = extraire_temps(c)
            if s and e:
                blocks.append((s, e, "vos obligations principales"))
                
    if "Repos" not in drive_str and "non synchronisées" not in drive_str:
        s, e = extraire_temps(drive_str)
        if s and e:
            blocks.append((s, e, "vos engagements professionnels"))
            
    if coaching != "Pas d'activité prévue":
        s, e = extraire_temps(coaching)
        if s and e:
            blocks.append((s, e, "votre activité annexe"))
            
    blocks.sort(key=lambda x: x[0])
    
    avertissements = []
    for i in range(len(blocks) - 1):
        fin_actuel = blocks[i][1]
        debut_suivant = blocks[i+1][0]
        nom_actuel = blocks[i][2]
        nom_suivant = blocks[i+1][2]
        
        if nom_actuel != nom_suivant:
            diff = debut_suivant - fin_actuel
            if diff < 0:
                avertissements.append(f"Anomalie logistique détectée : {nom_actuel} chevauche directement {nom_suivant}.")
            elif diff <= 25:
                avertissements.append(f"Vigilance de transit requise : vous n'aurez que {diff} minutes de battement entre {nom_actuel} et {nom_suivant}.")
                
    phrase_conflits = " ".join(avertissements)
    if phrase_conflits:
        phrase_programme += f" {phrase_conflits}"
        
    annonce_mails = random.choice(ANNONCES_MAILS).format(titre=titre_choisi)
    
    conclusions_matin = [
        "Passez une excellente journée.",
        "Que votre journée soit des plus productives.",
        "Bon courage pour vos objectifs du jour.",
        "Je reste en veille active. Excellente journée à vous."
    ]
    conclusion = random.choice(conclusions_matin)
    
    phrase_vocale = f"{intro_vocale} {meteo_conseil} {transition} {phrase_programme} {annonce_mails} {citation} {conclusion}"
    
    return jsonify({
        "status": "success",
        "sous_titre": titre_complet,
        "corps": corps,
        "phrase_vocale": phrase_vocale
    })


@app.route('/rapport/emails', methods=['GET'])
@require_api_key
@rate_limit(max_requests=10, window_seconds=60)
def route_emails():
    """
    Email audit route protected by API Key authentication and rate limiting.
    """
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
        "status": "success",
        "phrase_vocale": phrase_vocale
    })

# ------------------------------------------------------------------------------
# Administrative Routes (Requiring Admin Privileges & Strict Limits)
# ------------------------------------------------------------------------------
@app.route('/admin/system-status', methods=['GET'])
@require_admin
@rate_limit(max_requests=5, window_seconds=60)
def admin_status():
    """
    Protected administrative health and configuration audit report.
    """
    env_checks = {
        "BRUCE_API_KEY_CONFIGURED": bool(os.environ.get("BRUCE_API_KEY")),
        "ADMIN_API_KEY_CONFIGURED": bool(os.environ.get("ADMIN_API_KEY")),
        "GMAIL_CREDENTIALS_SET": bool(os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_PASS")),
        "ICAL_FEED_CONFIGURED": bool(os.environ.get("ADE_ICAL_URL")),
        "DRIVE_FEED_CONFIGURED": bool(os.environ.get("DRIVE_CSV_URL")),
        "DEBUG_MODE_DISABLED": not app.config.get("DEBUG", False),
        "SERVER_TIME_UTC": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify({
        "status": "authorized",
        "scope": "admin",
        "security_audit": env_checks
    }), 200


@app.route('/admin/audit-logs', methods=['GET'])
@require_admin
@rate_limit(max_requests=5, window_seconds=60)
def admin_audit_logs():
    """
    Protected endpoint to retrieve recent security audit logs.
    """
    logs = get_recent_audit_logs(limit=30)
    return jsonify({
        "status": "authorized",
        "count": len(logs),
        "audit_logs": logs
    }), 200

# ------------------------------------------------------------------------------
# Application Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Debug mode is explicitly turned off for security
    app.run(host="0.0.0.0", port=port, debug=False)
