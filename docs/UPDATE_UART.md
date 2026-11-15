# Mise à jour UART — 15 novembre 2026

## Ce qui change

Les deux firmwares doivent être mis à jour ensemble : l’ancien transport SPI et le nouveau transport UART ne sont pas compatibles. Le service Python reste nécessaire, avec son client radio mis à jour. La carte HA et son API ne changent pas.

La liaison utilise les connexions existantes D11–D11 et D12–D12, à 230400 bauds, 8N1. D11 transmet de la Nano 33 IoT vers l’ESP32 ; D12 assure le retour. Aucun fil à croiser. D10, D13 et D2 restent inactifs. Le SPI interne de la Nano IoT vers son module Wi-Fi n’est pas modifié. Voir [le brochage](MATERIEL.md) et [la compilation](COMPILATION.md).

Les blocs de 64 octets conservent CRC32, identifiant de démarrage, séquence et acquittement. Une fenêtre glissante permet de retrouver les blocs après une désynchronisation. Les identifiants de requête évitent de réexécuter une émission radio lors d’une répétition du transport. Le nom historique `spi_link.c` est conservé, mais son implémentation est maintenant UART.

Les neuf formes d’onde sont vérifiées avant la première émission puis toutes les 60 secondes ; une erreur d’émission invalide ce contrôle. Le CRC de chaque bloc de transport reste vérifié. La pause du moniteur serveur passe de 800 à 250 ms. Une reconnexion est autorisée une seule fois pour le contrôle sans émission ou une interrogation neutre ; les commandes de touches ne sont jamais rejouées automatiquement.

Pour choisir P1/P2/P3, chaque pas +/− exige une confirmation récente de l’écran de réglage manuel, âgée d’au plus deux secondes. Une touche M courte réouvre cet écran si nécessaire. La lecture redondante juste avant le pas est supprimée. Une absence de confirmation reste un échec, pas un succès supposé.

## Mesures sur l’installation de référence

| Observation | Résultat | Limite |
|---|---|---|
| Transport UART | Plus de 164 000 blocs valides, aucun bloc rejeté pour CRC pendant la session mesurée | Ne garantit pas zéro erreur future ; les redémarrages ont produit des délais d’attente |
| 30 cycles statut + contrôle | Aucun échec, aucun nouveau délai UART | Test du transport, pas des changements de consigne |
| 30 interrogations avant optimisation | Médiane 0,519 s, maximum 0,560 s | Une interrogation ne garantit pas une trame utile |
| 30 interrogations après optimisation | Médiane 0,321 s ; un appel avec reconnexion a duré 10,50 s | Ce n’est pas le délai garanti d’une commande HA |

Ces résultats proviennent des journaux locaux des essais, non publiés car liés à l’installation. Ils ne constituent pas un benchmark indépendant reproductible sans matériel et profil radio compatibles. Les tests hors matériel vérifient séparément les règles de reprise, les confirmations et l’absence de rejeu.

La réception radio reste irrégulière à cinq mètres. Les essais de gain et de suspension du Wi-Fi n’ont pas démontré d’amélioration fiable. Les filtres expérimentaux ont été retirés ; la réception publiée conserve le sous-échantillonnage antérieur et le gain automatique. Aucun diagnostic certain d’interférence n’est établi.

Le format `POWER P3   +/-  ` enregistré contient bien **16 octets**. Le test de régression emploie la trame capturée `10504f5745522050332020202b2f2d2020b478`. L’hypothèse intermédiaire d’un écran de 15 octets était erronée et n’est pas intégrée.

## Reproduire les contrôles hors matériel

Depuis la racine du dépôt, après installation de `requirements.txt` :

```sh
python -m unittest discover -s radio -p 'test_*.py'
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_card.js
cc -Wall -Wextra tests/test_wire.c -o /tmp/ania-wire-test
/tmp/ania-wire-test
```

Pour comparer les performances sur matériel, relever séparément la durée des appels, les erreurs de transport, les trames décodées et les états effectivement confirmés. Garder fréquence, distance, placement et profil identiques entre essais ; conserver aussi les échecs et les reconnexions dans les statistiques.

**Statut :** amélioration du transport mesurée, amélioration perçue par l’utilisateur ; validation complète P1/P2/P3 dans HA encore à poursuivre. Power conserve l’appui de trois secondes et son délai de protection. Les diagnostics d’appui long M ne constituent pas une navigation de menu validée.
