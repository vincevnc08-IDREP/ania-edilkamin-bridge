# API locale

Toutes les requêtes nécessitent `Authorization: Bearer <jeton API>`. Transport HTTP sur réseau local de confiance, sans TLS intégré.

| Méthode | Chemin | Usage |
|---|---|---|
| GET | `/v1/state` | Consigne et fraîcheur |
| GET | `/v1/capabilities` | Fonctions exposées |
| POST | `/v1/command` | +, − ou cible |
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
