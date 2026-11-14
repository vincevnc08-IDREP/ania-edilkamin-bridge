# Installation réseau et Home Assistant

## 1. Préparer le serveur

Linux avec Docker, sur le même réseau que la Nano 33 IoT. Réserver son adresse dans le routeur. Les commandes ci-dessous partent de la racine du dépôt ; remplacer les variables par les adresses de votre installation.

```sh
mkdir -p private data
chmod 700 private
# Écrire dans private/link.token le même jeton que dans secrets.h.
python3 -c 'import secrets; print(secrets.token_hex(32))' > private/bridge.token
chmod 600 private/*.token
# Le conteneur s’exécute en UID/GID 1000 : adapter les droits du dossier à cet UID.
sudo chown -R 1000:1000 private data
docker build -f server/Dockerfile -t ania-radio:0.2.0 .
export ANIA_GATEWAY_HOST='ADRESSE_NANO_IOT'
export ANIA_SERVER_IP='ADRESSE_LAN_SERVEUR'
docker run -d --name ania-radio --restart unless-stopped --read-only \
  --tmpfs /tmp:rw,nosuid,size=16m --cap-drop ALL \
  --security-opt no-new-privileges \
  -e ANIA_GATEWAY_HOST -e ANIA_TX_GAIN=10 \
  -p "$ANIA_SERVER_IP:18766:18766" \
  -v "$PWD/private:/private" -v "$PWD/data:/data" \
  --log-opt max-size=10m --log-opt max-file=3 ania-radio:0.2.0
```

Le jeton `bridge.token` protège l’API ; `link.token` protège le lien Nano. Ils ont des rôles différents. Vérifier les journaux avec `docker logs --tail 50 ania-radio`. Le serveur doit être capable de joindre la Nano sur TCP 18765.

## 2. Installer dans Home Assistant

Copier le contenu de `ha_bundle/scripts/`, `ha_bundle/packages/` et `ha_bundle/www/` vers les dossiers homonymes sous `/config/`. Copier le jeton API du serveur dans `/config/ania_bridge.token` et écrire l’URL `http://ADRESSE_LAN_SERVEUR:18766` dans `/config/ania_bridge.url`.

Activer les packages, en fusionnant avec la configuration existante :

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Vérifier la configuration HA avant redémarrage. En mode de gestion des ressources Lovelace par l’interface, ajouter manuellement `/local/ania-remote.js?v=8` en module JavaScript si nécessaire. Ne pas enregistrer la ressource deux fois.

Ajouter une carte manuelle :

```yaml
type: custom:ania-remote
entity: sensor.ania_consigne
enable_commands: false
max_age_seconds: 90
```

Commencer en lecture seule. Après vérification du bon poêle, de la fraîcheur et de la consigne, passer `enable_commands` à `true`. La carte présente +, −, le champ de consigne cible et le bouton Valider. Les anciens identifiants personnalisés d’une installation existante ne sont pas automatiquement migrés.

## 3. Comprendre les états

- `confirmed` : consigne observée et confirmée, avec sa date réelle.
- `stale` : dernière consigne connue conservée, mais trop ancienne ou liaison incertaine.
- `in_progress` : séquence de consigne cible en cours.
- `indeterminate` : résultat incertain ; ne pas supposer que l’ordre a été ignoré.
- `unavailable` : aucune observation exploitable.

Un affichage immédiat de la demande ne prouve pas son exécution. La consigne observée reste distincte de la cible saisie.

## 4. Dépannage

| Symptôme | Vérification |
|---|---|
| Pas de connexion réseau | Alimentation, SSID, mot de passe, adresse réservée, TCP 18765 |
| Erreur d’authentification | Bon jeton au bon endroit, pas d’espaces supplémentaires |
| Valeur périmée | Rapprocher la passerelle, éloigner du métal, vérifier la réception |
| Pas de changement de consigne | Profil radio compatible, réponses confirmées, alimentation et SPI |
| Carte inconnue dans HA | Ressource JavaScript chargée et cache navigateur actualisé |
| Échecs malgré le gain élevé | Placement et antenne avant hausse du gain ; indice non calibré en dBm |

Ne pas automatiser des répétitions de +/− pour masquer une liaison défaillante. Auto/P1/P2/P3 nécessitent un retour frais. Power · 3 s est une touche de bascule manuelle, sans état physique déduit ; voir [les limites des essais](MODES_POWER.md).
