<p align="center">
  <img src="BruceAi/banner.svg" width="100%" alt="Bruce AI Assistant">
</p>

# BRUCE AI - Assistant Personnel Automatisé

**Auteur :** Rayan Mouzaine

**Statut :** Projet de Portfolio / Démonstrateur Technique

**Interface Web :** [Consulter l'architecture et la simulation](https://orayzis.github.io/Bruce-AIAssistant/)

## Contexte du projet

Ce projet répond à un défi logistique personnel : synchroniser de manière automatisée mon emploi du temps universitaire (IUT), mes horaires de travail (Auchan Drive) et mes engagements sportifs (Coaching U10).

Bruce est une API backend qui agrège ces sources de données hétérogènes, résout les conflits temporels, filtre mes correspondances, et formate ces informations pour un briefing vocal quotidien déclenché via un raccourci iOS.

Ce dépôt documente l'architecture du système et sert de démonstrateur de mes compétences en développement logiciel.

## Architecture Technique

* **Backend :** API RESTful développée en Python avec le framework Flask.
* **Base de données :** SQLite (mode WAL) assurant la persistance des journaux d'audit et la traçabilité des requêtes.
* **Sécurité :** Routes verrouillées par jetons d'authentification (Tokens), limitation de débit en mémoire (Rate Limiting) et requêtes paramétrées.
* **Infrastructure :** Hébergement cloud (PaaS) sur Render. Implémentation d'une stratégie Keep-Alive (UptimeRobot) pour annuler la latence de démarrage à froid (Cold Start).

## Modules et Fonctionnalités

### 1. Convergence des flux

Le serveur extrait et nettoie en temps réel des données issues de formats variés : agendas complexes (iCal), plannings collaboratifs (exports CSV) et API externes (Open-Meteo pour les relevés géolocalisés).

### 2. Moteur d'anticipation logistique

Un algorithme d'analyse temporelle trie chronologiquement les événements de la journée. Le système calcule les battements mathématiques entre chaque activité et génère une alerte préventive si un temps de transit est inférieur à 25 minutes.

### 3. Lecture furtive et Tri IMAP

Module de connexion sécurisée (IMAP sur SSL) conçu pour isoler les e-mails professionnels (candidatures, urgences) des flux promotionnels. Le scan est effectué de manière furtive pour protéger la confidentialité, sans jamais marquer les messages comme lus sur le serveur distant.

### 4. Restitution vocale (iOS)

L'API structure les données brutes en une chaîne textuelle optimisée pour le traitement du langage naturel. L'automatisation Apple (Raccourcis) interroge l'endpoint chaque matin pour énoncer le rapport de manière fluide.

## Compétences évaluables

* Développement backend en Python (Flask).
* Intégration, conception et sécurisation d'API REST.
* Parsing et manipulation de structures de données (JSON, CSV, iCal).
* Conception d'algorithmes de détection de conflits logistiques.
* Déploiement et maintien d'un serveur en production.
