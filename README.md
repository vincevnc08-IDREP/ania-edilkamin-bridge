# ANIA · Radio Bridge

**Une passerelle radio expérimentale pour piloter la consigne d’un Edilkamin Ania depuis Home Assistant.**

Deux Arduino Nano empilées, une liaison Wi-Fi et un boîtier imprimable. Documentation en français, code source et tests inclus.

![Boîtier ANIA](enclosure/apercu.png)

> **Prototype validé sur une seule installation.** Le profil radio fourni provient de cette télécommande : il ne constitue pas un appairage universel. Ne pas flasher en supposant une compatibilité avec tous les poêles Edilkamin. Le boîtier est vérifié numériquement, pas encore imprimé et ajusté physiquement.

## Fonctions

| Fonction | État |
|---|---|
| Lecture de la consigne avec confirmation radio | Implémentée et testée |
| Boutons + et − | Implémentés et testés |
| Saisie d’une consigne de 10 à 25 °C | Séquence de pas confirmés |
| Affichage de la dernière valeur et de sa fraîcheur | Implémenté |
| Marche / arrêt, puissance P1 / P2 / P3 | **Non implémentés** |
| Température ambiante, état réel de combustion | **Non validés** |
| Déchiffrement du firmware Edilkamin | **Non réalisé** |

## Architecture

![Architecture](docs/assets/architecture.png)

```mermaid
flowchart LR
 HA[Home Assistant] <-->|HTTP authentifié · LAN| S[Serveur Python / Docker]
 S <-->|TCP Wi-Fi authentifié| I[Nano 33 IoT]
 I <-->|SPI + READY| E[Nano ESP32]
 E <-->|Radio expérimentale · 2480 MHz| P[Poêle Ania]
```

La Nano ESP32 utilise sa radio pour le poêle. La Nano 33 IoT assure le Wi-Fi réseau. **Un serveur reste nécessaire** ; ce projet n’est pas un appareil ESPHome autonome.

## Parcours conseillé

1. Lire [l’étude simplifiée](docs/ETUDE.md) et les limites du profil radio.
2. Vérifier [le matériel et l’empilage](docs/MATERIEL.md).
3. [Compiler les firmwares](docs/COMPILATION.md), avec ses propres identifiants.
4. [Installer la passerelle et Home Assistant](docs/INSTALLATION.md).
5. Imprimer d’abord [le gabarit du boîtier](enclosure/gabarit_essai.stl).

## Dans ce dépôt

- `radio/` : firmware Zephyr ESP32-S3, décodeur et client Python.
- `nano33_gateway/` : firmware Arduino Nano 33 IoT, protocole SPI.
- `server/` : API HTTP, confirmation et déduplication des commandes.
- `ha_bundle/` : package HA, script Python et carte Lovelace.
- `enclosure/` : STL, source OpenSCAD, rendus et notice.
- `tests/` : tests hors matériel ; [mesures et limites](docs/VALIDATION.md).

Composants livrés : firmware radio/passerelle v13, service issu de v14, carte HA v6. La numérotation du dépôt commence séparément à `0.1.0`.

## Fiabilité

![Mesures expérimentales](docs/assets/mesures.png)

Une demande de température n’est jamais présentée comme une mesure confirmée. Les commandes relatives ne sont pas répétées aveuglément après une coupure. Les réponses sont contrôlées par CRC et consensus ; une séquence s’arrête en cas d’incertitude.

La qualité de réception et le placement restent déterminants. Des changements ont été confirmés en environ 3 secondes, mais ce n’est pas une garantie de délai. Les erreurs radio/SPI résiduelles ne sont pas éliminées.

## Licence et crédits

Code original sous **GPL-3.0-or-later** ; voir [LICENSE](LICENSE) et [crédits](THIRD_PARTY.md). Projet indépendant, sans affiliation ni validation officielle d’Edilkamin ou d’Arduino. Aucun firmware propriétaire Edilkamin, mot de passe réseau ou jeton de l’installation n’est distribué.

## Documentation détaillée

[API](docs/API.md) · [Validation](docs/VALIDATION.md) · [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md) · [Historique](CHANGELOG.md)
