# Sécurité et données privées

Ne jamais publier `secrets.h`, les jetons, les captures personnelles ni un firmware Wi-Fi compilé avec de vrais identifiants. Les binaires sont volontairement ignorés par Git.

L’API HTTP et le transport TCP sont authentifiés mais non chiffrés : réseau local de confiance uniquement. Ne pas les exposer directement à Internet. Utiliser un VPN pour l’accès distant. Un jeton d’API distinct du jeton entre serveur et Nano est recommandé.

Avant de partager un diagnostic, retirer les identifiants, adresses réseau et données d’appairage. Signaler les défauts sans publier de secrets dans une issue publique.
