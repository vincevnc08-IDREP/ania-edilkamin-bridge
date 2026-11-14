# Compiler les deux firmwares

## Pré-requis

Git, Python, CMake, Ninja, west et la chaîne Zephyr Xtensa ESP32-S3. Référence de développement : west 1.5.0 et Zephyr SDK 1.0.1. Les versions de Zephyr, du HAL et du SDR doivent correspondre à `west.yml` ; ne pas remplacer par la dernière version officielle au hasard.

Les instructions supposent un répertoire parent `ania-workspace/`, avec le dépôt dans `ania-workspace/ania-edilkamin-bridge/`.

```sh
mkdir -p ania-workspace
cd ania-workspace
git clone https://github.com/vincevnc08-IDREP/ania-edilkamin-bridge.git
python3 -m venv .venv
. .venv/bin/activate
pip install west==1.5.0 cmake ninja
west init -l ania-edilkamin-bridge
west update
west zephyr-export
pip install -r modules/zephyr/scripts/requirements.txt
west blobs fetch hal_espressif esp-sdr-zephyr
```

Installer le [Zephyr SDK](https://github.com/zephyrproject-rtos/sdk-ng/releases) et définir `ZEPHYR_SDK_INSTALL_DIR` vers son dossier. Le SDK et ses outils doivent être exécutables sur votre système ; le poste de référence utilise aussi des outils x86_64 sous Rosetta.

## Nano ESP32 — radio

```sh
west build -b ania_nano/esp32s3/procpu ania-edilkamin-bridge/radio -d build/radio
```

Sortie : `build/radio/zephyr/zephyr.bin`. Le profil des formes d’onde est dans `radio/src/waveforms.h` ; les CRC attendus sont inclus dans ce profil. **Il est propre à l’installation de référence.** La compilation n’est pas une procédure d’appairage.

Pour flasher avec les outils Zephyr, identifier explicitement le port USB-C de la Nano ESP32, puis utiliser le runner de la carte :

```sh
west flash -d build/radio --esp-device PORT_USB_ESP32
```

Vérifier les options du runner avec `west flash -d build/radio -H` selon la version installée. Ne pas confondre les ports des deux cartes.

## Nano 33 IoT — réseau

Référence : Arduino CLI 1.6.0, core SAMD 1.8.14, WiFiNINA 1.9.1.

```sh
arduino-cli core update-index
arduino-cli core install arduino:samd@1.8.14
arduino-cli lib install 'WiFiNINA@1.9.1'
cd ania-edilkamin-bridge
cp nano33_gateway/secrets.example.h nano33_gateway/secrets.h
```

Renseigner localement SSID, mot de passe et un jeton aléatoire de 32 caractères minimum. Générer par exemple le jeton avec `python3 -c 'import secrets; print(secrets.token_hex(32))'`. Ce jeton sera également dans le fichier privé `link.token` du serveur. Ne pas le partager dans Git.

```sh
arduino-cli compile --fqbn arduino:samd:nano_33_iot --output-dir build/iot nano33_gateway
arduino-cli board list
arduino-cli upload --fqbn arduino:samd:nano_33_iot --port PORT_USB_IOT --input-dir build/iot nano33_gateway
```

Le fichier compilé contient les identifiants : il reste privé. Aucun binaire préconfiguré de l’installation n’est fourni. La compilation et les tests du dépôt ne nécessitent pas de reprogrammer une installation déjà en service.
