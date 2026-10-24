<p align="center"><strong>Fiche Technique</strong>

<p align="center">
  <img src="./banner.svg" width="100%" alt="Bruce AI Assistant">
</p>

# Bruce : AI Personnel Assistant

> API Python qui regroupe planning, horaires, météo et e-mails en briefings vocaux, déclenchés chaque jour à 7h et 10h sur iOS.

> **[Voir la démonstration interactive](https://rmouzaine.github.io/Bruce-AIAssistant/)**

**Auteur :** RMouzaine

**Statut :** en cours de maintenance

**Version :** v1.1

**Stack :** Python · Flask · Render · iOS Raccourcis · UptimeRobot · HTML/CSS/JS (Frontend)

---

> ## Problème

Planning, horaires de travail, météo, mails : quatre applications à ouvrir chaque matin.

>## Solution

Une API centralise ces sources. Chaque jour à 7h, une automatisation iOS appelle l'API, récupère un texte prêt à lire et le fait énoncer par l'iPhone. 

L'architecture est agnostique et sur-mesure : elle s'adapte à n'importe quelle routine (heures de conduite, freelance, cours de yoga, entraînements sportifs) par simple configuration des modules de collecte.

---

>## Architecture

```text
┌────────────────┐                  ┌──────────────────────┐
│ Automatisation │ tous les jours   │  Raccourci iOS       │
│ iOS · 7h       │ ───────────────► │                      │
└────────────────┘                  └──────────┬───────────┘
                                               │ GET /rapport/...
                                               ▼
                                     ┌──────────────────────┐
                                     │  API Flask (Render)  │
                                     └──┬────┬────┬────┬────┘
                                        │    │    │    │
                        ┌───────────────┘    │    │    └──────────────┐
                        ▼                    ▼    ▼                   ▼
                 Planning (iCal)      Google Sheets   Open-Meteo    Gmail (IMAP)
                                      (export CSV)    (météo)
```

>## Architecture Technique

- **Backend :** API RESTful développée en Python (framework Flask).
- **Hébergement Cloud :** Déployé sur Render (PaaS).
- **Interface Client (Frontend) :** Apple iOS (Application Raccourcis / Siri) et interface Web de démonstration.
- **Stabilité et Haute Disponibilité :** Stratégie Keep-Alive via UptimeRobot pour envoyer des requêtes Ping toutes les 5 minutes, empêchant la mise en veille du serveur et annulant la latence de démarrage (Cold Start).

>## Fonctionnalités

### `GET /rapport/matin` : briefing du matin

- **Météo** : conditions actuelles (Open-Meteo) et conseil adapté.
- **Cours** : flux iCal filtré sur la journée, fuseau Europe/Paris.
- **Horaires de travail** : Google Sheets en CSV, détection de la semaine puis du jour.
- **Agenda sportif et annexes** : intégration dynamique d'activités personnalisées.
- **Anticipation logistique** : analyse temporelle (Regex) triant les activités chronologiquement pour détecter et signaler les chevauchements ou les temps de trajet critiques (< 25 min).
- **Variété** : intro, citation et conclusion aléatoires.

### `GET /rapport/emails` : boîte de réception

- Connexion IMAP sur SSL, identifiants en variables d'environnement.
- 10 derniers messages non lus.
- Messages promotionnels comptés, non lus à voix haute.
- Tri par mots-clés : professionnel d'un côté, autres de l'autre.
- Décodage des en-têtes (accents, UTF-8).

---

>## Défis techniques

- **Cold start** : Render met le serveur en veille et le premier appel dure près d'une minute. Un ping UptimeRobot toutes les 5 minutes l'évite.
- **Tableur irrégulier** : saisie manuelle, cellules vides, « 00:00 » pour les repos. Un parseur tolérant retrouve la semaine puis les créneaux.
- **Synchronisation et Conflits** : extraire des données temporelles de formats hétérogènes (iCal, CSV brut, texte) pour permettre à l'algorithme de calculer les intervalles de transit.
- **Fuseaux horaires** : serveur en UTC, événements en heure de Paris. Conversion avec `pytz`.
- **Écrire pour l'oreille** : heures, listes et transitions reformulées pour la synthèse vocale.

---

>## Compétences acquises

- Concevoir et déployer une API légère
- Consommer des sources variées : iCal, CSV, JSON, IMAP
- Gérer des contraintes réelles : veille, latence, fuseaux, conflits logistiques
- Identifier les failles de sécurité de son propre projet
- Concevoir une interface front-end statique (Pages) pour vulgariser l'architecture backend

---

>## Pistes d'amélioration

- [ ] Authentification de l'API par jeton
- [ ] Lecture des mails sans les marquer comme lus
- [ ] Tri des mails plus fiable
- [ ] Réponse aux mails à la voix
- [ ] Rapport du soir
