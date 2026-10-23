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
            
            if "date:" in texte_ligne0 and recherche_sem in texte_ligne0:
                dans_bonne_semaine = True
                continue
                
            if dans_bonne_semaine and "rayan" in texte_ligne0:
                valeurs_jours = ligne[2:] # On ignore le nom et le statut 'travail'
                jours_extraits = []
                i = 0
                
                # On parcourt dynamiquement les colonnes pour reconstruire les 7 jours
                while len(jours_extraits) < 7 and i < len(valeurs_jours):
                    val = valeurs_jours[i].strip()
                    if val == "00:00" or val == "":
                        jours_extraits.append("Repos")
                        i += 1 # Un jour de repos prend souvent 1 seule colonne
                    else:
                        if i + 1 < len(valeurs_jours):
                            debut = val
                            fin = valeurs_jours[i+1].strip()
                            jours_extraits.append(f"{debut} à {fin}")
                            i += 3 # Un jour travaillé prend 3 colonnes
                        else:
                            break
                            
                if offset_jour < len(jours_extraits):
                    return jours_extraits[offset_jour]
                else:
                    return "Erreur de décalage des colonnes"
                    
            if dans_bonne_semaine and "date:" in texte_ligne0 and recherche_sem not in texte_ligne0:
                break
                
        return f"Erreur : Semaine {semaine_actuelle} non trouvée dans le fichier."
        
    except Exception as e:
        return f"Erreur Drive: {str(e)}"
