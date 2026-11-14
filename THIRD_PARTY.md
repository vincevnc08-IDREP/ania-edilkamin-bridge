# Licences et provenance

Le code original du projet est distribué sous GPL-3.0-or-later, conformément aux en-têtes SPDX des firmwares. Le texte GPLv3 figure dans LICENSE. La documentation et les modèles de boîtier originaux sont également proposés sous GPL-3.0-or-later.

Dépendances externes non vendoriées : esp-sdr (GPLv3 ; respecter sa licence), Zephyr et les modules indiqués dans west.yml (licences propres à chacun), Arduino SAMD core, WiFiNINA, NumPy, SciPy et pyserial. Une distribution de binaires doit inclure les obligations de toutes les dépendances et le code source correspondant. Ce dépôt distribue les sources du projet, pas les firmwares propriétaires du fabricant.

Les révisions exactes des dépendances Zephyr/SDR sont figées dans west.yml. Arduino CLI 1.6.0, arduino:samd 1.8.14 et WiFiNINA 1.9.1 ont été utilisés sur l’installation de référence.
