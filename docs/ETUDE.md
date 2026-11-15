# Étude simplifiée

## Pourquoi deux cartes ?

L’approche retenue exploite les fonctions SDR expérimentales de la radio ESP32-S3. Dans cette implémentation, elles ne coexistent pas avec le Wi-Fi réseau normal. Une Nano 33 IoT séparée transporte donc les commandes et réponses par Wi-Fi, puis UART.

## Du signal à la consigne

1. Capturer les émissions de la télécommande pendant une action connue.
2. Comparer les captures et rechercher préambule, codage et contrôle d’intégrité.
3. Reproduire les formes d’onde +, − et relâchement, sans répétition automatique d’une commande incertaine.
4. Décoder les réponses du poêle et confirmer la consigne par deux interrogations neutres distinctes concordantes.

Le décodeur applique un filtre FIR de 65 coefficients, un discriminateur de phase et quatre phases d’échantillonnage. Il recherche un motif SOP de 64 bits et utilise un dictionnaire de 32 chips, avec une variante de corrélation souple. Les longueurs acceptées sont 7 et 16 ; le contrôle CRC16 utilise le polynôme 0xA001, une initialisation 0x2828 et un XOR final 0xFFFF. Un CRC32 protège également le transport compact.

Ces choix décrivent le profil observé, pas une spécification officielle CYRF6936/Edilkamin. Les formes d’onde de `radio/src/waveforms.h` sont celles de l’installation étudiée. Elles peuvent contenir des champs d’identité/appairage : **le dépôt n’offre pas encore de générateur d’appairage pour un autre poêle**. Leur publication sert à reproduire l’étude ; leur compilation ne démontre pas leur compatibilité avec un autre appareil.

## Confirmé, hypothétique, inconnu

| Sujet | Conclusion |
|---|---|
| + / − et retour de consigne | Effets observés sur l’installation de référence |
| Confirmation par deux réponses | Mise en œuvre et contrôlée dans le logiciel |
| Gain radio | Indice logiciel, pas une puissance mesurée en dBm |
| Silence de 30 ms avant émission | Mesure d’atténuation possible des interférences ; causalité non prouvée |
| M/A et P1/P2/P3 | Transitions observées, lecture HA conditionnée au consensus |
| Power 3 s | Démarrage observé ; extinction Nano et état physique non validés |
| Autres cartes LX32/LX64 | Compatibilité non démontrée |
| Firmware ATmega64 / codec OMNICARD | Piste historique non aboutie ; aucune clé validée ni déchiffrement revendiqué |

## Fiabilisation

La liaison UART (230400 bauds, 8N1) utilise des blocs de 64 octets, CRC32, identifiant de démarrage, séquence et acquittement. Répéter un bloc de transport ne doit pas répéter une émission radio. Le service conserve les identifiants des demandes dans SQLite. Après redémarrage, une action inachevée reste indéterminée.

Une consigne cible est une succession de pas d’un degré, chaque pas devant être confirmé. Aucun ordre marche/arrêt n’est exposé. Les mécanismes de sécurité propres au poêle ne sont pas modifiés.

## Références

- [esp-sdr](https://github.com/ESPARGOS/esp-sdr)
- [esp-sdr-zephyr](https://github.com/cyber-murmel/esp-sdr-zephyr)
- [esp32-sdr-trx](https://github.com/jochenhammes/esp32-sdr-trx)
- [Matériel SDR](https://sdrmm.com/docs/hardware)

Les dépendances effectivement utilisées sont épinglées dans `west.yml`. Les autres liens sont des références de recherche, pas des dépendances installées.

Les essais récents et leurs limites sont détaillés dans [Modes et Power](MODES_POWER.md).
