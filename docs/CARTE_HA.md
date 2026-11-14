# Carte Home Assistant

La carte est incluse dans le dépôt : [JavaScript](../ha_bundle/www/ania-remote.js), [package YAML](../ha_bundle/packages/ania.yaml), [script de liaison](../ha_bundle/scripts/ania_ha.py).

![Aperçu de la vraie carte avec données de démonstration](assets/ha_card.png)

**Cet aperçu utilise le véritable composant JavaScript, avec des données fictives.** Ce n’est pas une capture de l’installation personnelle et aucune commande n’est envoyée.

## Fonctions de l’interface

- Consigne observée sur le poêle, distincte de la cible saisie.
- Boutons + et − pour un degré à la fois.
- Champ « Nouvelle consigne » de 10 à 25 °C, validation par bouton ou Entrée.
- Indication de fraîcheur et suivi de la demande.
- Dernière valeur conservée, mais commandes suspendues si la liaison n’est plus confirmée.

Marche/arrêt et P1/P2/P3 ne sont pas implémentés. Leur mention dans l’interface indique une piste future, sans engagement de disponibilité.

## Installation

Suivre [le guide complet](INSTALLATION.md), puis ajouter :

```yaml
type: custom:ania-remote
entity: sensor.ania_consigne
enable_commands: true
max_age_seconds: 90
```

N’activer les commandes qu’après vérification de la liaison et du profil du poêle. Pour commencer en lecture seule, mettre `enable_commands: false`.

## Aperçu local sans HA

Depuis la racine du dépôt :

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Ouvrir `http://127.0.0.1:8765/docs/ha_preview.html`. La page montre côte à côte un état confirmé et un état périmé. Les actions sont simulées et ne peuvent joindre ni HA ni le poêle.

Pour régénérer la capture, garder ce serveur ouvert, puis dans un autre terminal :

```sh
npm install --no-save playwright
npx playwright install chromium
node scripts/screenshot_ha.cjs
```

Le script vérifie les boutons activés pour l’état confirmé et désactivés pour l’état périmé avant d’enregistrer l’image. Cela ne remplace pas un essai dans Home Assistant.
