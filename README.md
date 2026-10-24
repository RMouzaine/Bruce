<p align="center">
  <img src="./banner.svg" width="100%" alt="Bruce AI Assistant">
</p>

# Projet Bruce : AI Assistant

**Créateur :** RMouzaine  
**Statut du système :** en maintenance

**Version :** 1.0  

---

## Présentation Générale

Bruce est une interface d'assistance personnelle centralisée, conçue pour automatiser et dicter le flux d'informations quotidiennes de son créateur. Pensé avec une personnalité stricte, clinique et professionnelle, le système connecte des bases de données hétérogènes (universitaires, professionnelles, personnelles) pour générer des rapports vocaux instantanés via les appareils iOS.

Ce projet démontre une capacité à concevoir une architecture backend légère, à manipuler des requêtes HTTP et à contourner des contraintes matérielles (latence réseau, serveurs en veille) par l'ingénierie système.

## Architecture Technique

* **Backend :** API RESTful développée en Python (framework Flask).
* **Hébergement Cloud :** Déployé sur Render (PaaS).
* **Interface Client (Frontend) :** Apple iOS (Application Raccourcis / Siri).
* **Stabilité et Haute Disponibilité :** Stratégie Keep-Alive via UptimeRobot pour envoyer des requêtes Ping toutes les 5 minutes, empêchant la mise en veille du serveur et annulant la latence de démarrage (Cold Start).

## Fonctionnalités Centrales

### 1. Le Rapport Matinal (/rapport/matin)
Un briefing complet généré à la demande, qui compile :
* **Météorologie :** Requête API vers Open-Meteo avec recommandations vestimentaires conditionnelles.
* **Logistique Universitaire :** Parsing dynamique de l'emploi du temps (IUT d'Orléans) via un flux iCal contourné par Google Agenda pour des performances optimales.
* **Logistique Professionnelle :** Extraction et lecture d'un fichier Google Sheets (format CSV public) ciblant la semaine en cours pour déterminer les horaires de travail en Drive.
* **Logistique Sportive :** Paramétrage conditionnel des jours de coaching (U10-U11) et de matchs.

### 2. Le Rapport de Communication (/rapport/emails)
Un audit automatisé de la boîte de réception Gmail :
* **Connexion sécurisée :** Via le protocole IMAP4_SSL.
* **Extraction et décodage :** Lecture (RFC822) des 10 derniers messages non lus.
* **Filtre anti-bruit :** Rejet systématique des newsletters, spams et communications automatisées (Apple, Zalando, etc.).
* **Tri algorithmique :** Catégorisation intelligente isolant les opportunités stratégiques (Cybersécurité, Aéronautique, Recrutement) des correspondances classiques.

## Liens et Endpoints Utiles

### Endpoints de l'API (Routage Flask)
* **Serveur Racine :** `https://jarvis-api-kbox.onrender.com`
* **Génération du Briefing Matin :** `/rapport/matin`
* **Génération de l'Audit E-mail :** `/rapport/emails`

### Ressources Externes et Bases de Données
* **Console de déploiement :** [Render Dashboard](https://dashboard.render.com)
* **Système Keep-Alive :** [UptimeRobot](https://uptimerobot.com)
* **Base Horaires Drive (Lecture Seule / CSV) :** [Google Sheets Public Export](https://docs.google.com/spreadsheets/d/e/2PACX-1vSHx5JoIBSJXZuYY22hS9ToHWcgy2Vyuw1cPtm_gIfw-I73RZOQ47HHh56ut9SOHInnWPZoUp90asvp/pub?gid=961193327&single=true&output=csv)
* **API Météo :** [Open-Meteo API](https://open-meteo.com)
