# Réception V25 et réactivité des modes

## État à retenir pour les prochaines interventions

**La réactivité n’est pas encore satisfaisante.** La télécommande reste la référence. Ne pas présenter cette mise à jour comme instantanée ou comme une fiabilisation complète. Priorité suivante : réduire les échanges et les retours manqués, sans modifier le câblage et sans remplacer une confirmation réelle par un affichage optimiste.

## Modifications installées

Le décodeur tolère 12 erreurs au lieu de 10 sur les préambules SOP de 64 chips. Le CRC, le décodage des données et la confirmation par deux interrogations distinctes restent inchangés. Les optimisations mathématiques expérimentales et les buffers en RAM interne ne sont pas inclus.

Le serveur réutilise un état confirmé récent avec des limites de fraîcheur adaptées. Une lecture HTTP ne déclenche plus des interrogations concurrentes lorsque le moniteur est actif. Les touches relatives restent conditionnées à la lecture du menu et du niveau. Aucun rejeu automatique après résultat incertain.

La carte autorise une sélection explicite Auto/P1/P2/P3 même si le dernier état est ancien, tout en bloquant les pas de température périmés et les états connus OFF/extinction. Rafraîchissement HA : 2 secondes. Le firmware Nano IoT ne change pas par rapport à la version UART précédente. Mettre à jour ESP32, serveur, package et carte HA ; recharger la ressource JavaScript pour éviter le cache navigateur.

## Mesures du 15 novembre 2026

Sur 572 captures archivées : 455 trames avant, 469 après, aucune trame précédemment décodée perdue. Les 14 supplémentaires sont également reconnues par un décodeur Python indépendant. Aucun paquet accepté sur 100 captures de bruit déterministe. Les captures privées ne sont pas distribuées : cette comparaison est un résultat de laboratoire, pas un test reproductible à partir du dépôt seul.

Deux séries successives de 80 interrogations ont fourni respectivement 50 et 70 réponses. La réception varie dans le temps : ne pas attribuer toute cette différence au firmware. Le décodage reste proche de 164 ms.

| Transition finale | Requête API → confirmation radio |
|---|---:|
| Auto → P2 | 5,56 s |
| P2 → P1 | 2,18 s |
| P1 → P3 | 4,91 s |
| P3 → Auto 17 °C | 1,51 s |

Une seule séquence, sans mesure du rendu navigateur ni comparaison chronométrée avec la télécommande. Toutes ces demandes ont été confirmées. Retour final : Auto 17 °C. Aucun Power envoyé pendant ces essais.

## Pistes essayées et non retenues

- Décalage de fréquence : aucune trame supplémentaire sur huit captures.
- Ralentissement des interrogations : bénéfice non isolé de la variabilité radio.
- Approximations atan / filtre entier : seulement environ 4 / 9 ms gagnées, complexité injustifiée.
- Grands buffers internes : chevauchement des banques réservées à la radio, refus de compilation.

## Validation hors matériel

Exécuter les commandes de [VALIDATION.md](VALIDATION.md), plus `node tests/test_card_stale.cjs`. Les tests ne remplacent pas des mesures radio prolongées. Le boîtier n’est pas modifié dans cette publication.
