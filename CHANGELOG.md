# Historique

## 2026-11-15 — Transport UART et réactivité

- UART 230400 bauds sur le câblage existant ; blocs CRC32 et déduplication conservés.
- Contrôles des formes d’onde mis en cache avec invalidation sur erreur.
- Reconnexion bornée pour les lectures, aucun rejeu automatique des touches.
- Pas P1/P2/P3 conditionnés à un écran de réglage récent.
- Schémas actualisés ; [mesures et limites](docs/UPDATE_UART.md).
- Aucun changement de boîtier dans cette mise à jour.

## Documentation enrichie

- Spectre et cascade issus d’une capture radio réelle, avec données dérivées et scripts de rendu.
- Zoom temporel sur le préambule et explication des limites de mesure.
- Aperçu de la vraie carte HA avec données fictives, guide et démonstration locale.

## 0.1.0 — Première distribution du prototype

- Sources des deux firmwares et dépendances SDR épinglées.
- Passerelle HTTP avec déduplication, cache confirmé et consigne cible.
- Package et carte Home Assistant avec valeur connue et fraîcheur distinctes.
- Boîtier paramétrique, STL, gabarit et aperçu.
- Étude simplifiée, procédures et limites de validation.

## 0.2.0 — 2026-11-14 (expérimental)

- Auto/P1/P2/P3 : ondes M/A, lecture des menus, contrôles de mode et intégration HA.
- Power unique de 3 s : démarrage observé, extinction Nano encore non validée ; aucun état marche/arrêt inventé.
- Déduplication durable et temporisation de 60 s, sans répétition après erreur.
- Correction de l’écriture 32 bits du transport SPI et tests de bornes.
- Carte HA v8, API et étude mises à jour ; boîtier et relevés radio conservés.
