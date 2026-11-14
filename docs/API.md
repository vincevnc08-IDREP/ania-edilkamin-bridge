# API locale

Toutes les requêtes nécessitent `Authorization: Bearer <jeton API>`. Transport HTTP sur réseau local de confiance, sans TLS intégré.

| Méthode | Chemin | Usage |
|---|---|---|
| GET | `/v1/state` | Consigne et fraîcheur |
| GET | `/v1/capabilities` | Fonctions exposées |
| POST | `/v1/command` | +, −, cible, mode ou Power |
| GET | `/v1/command/<request_id>` | Suivi / résultat mémorisé |

Corps d’une commande relative :

```json
{"command":"plus","request_id":"UUID_UNIQUE"}
```

Commande cible :

```json
{"command":"target","target_c":21,"request_id":"AUTRE_UUID_UNIQUE"}
```

Utiliser de vrais UUID uniques. Conserver l’identifiant pour consulter le résultat d’une même demande. Ne pas inventer un nouvel identifiant pour répéter une commande dont le résultat est incertain.

Une cible peut renvoyer HTTP 202 avec `status: in_progress`. Interroger ensuite le chemin de suivi ; ne pas renvoyer la commande. Les bornes sont 10–25 °C, avec des valeurs entières. La séquence s’arrête à la première incertitude et possède une limite temporelle de 120 secondes.

Le serveur peut renvoyer une valeur en cache encore fraîche (10 secondes maximum). `observed_at` décrit la mesure originale, pas l’heure de la requête HTTP. Il est donc normal que deux lectures successives aient le même horodatage.

Le fonctionnement détaillé et les codes d’erreur sont dans `server/app/bridge.py`. Cette première version expérimentale ne garantit pas encore une API stable entre versions majeures.

## Modes et Power

```json
{"command":"mode","mode":"P2","request_id":"UUID_UNIQUE_MODE"}
```

Modes autorisés : `AUTO`, `P1`, `P2`, `P3`. Retour `confirmed` uniquement après lecture concordante ; sans état préalable exploitable, la commande est refusée.

```json
{"command":"power","request_id":"UUID_UNIQUE_POWER"}
```

Power a une durée fixe de trois secondes, puis un relâchement. Réponse `status: sent`, `hold_ms: 3000`, `release_sent: true`, `power_state: null`. Ce n’est pas une confirmation d’allumage ou d’extinction. Le même identifiant ne réémet jamais. Une nouvelle demande pendant la temporisation est refusée avec HTTP 429 ; le délai minimal est de 60 secondes. Les commandes absolues `on` et `off` restent refusées.

Les variables `ANIA_MODES_ENABLED=0` et `ANIA_POWER_ENABLED=0` permettent de désactiver ces groupes de fonctions. Elles sont activées par défaut en 0.2.0 ; cela ne supprime pas les préconditions de lecture des modes.
