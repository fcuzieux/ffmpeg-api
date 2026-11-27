# ffmpeg-api

Microservice local de conversion audio/vidéo basé sur FFmpeg, exposé en HTTP pour être appelé
depuis n8n (ou tout autre client) via le réseau Docker interne. Écoute sur le port **3103**.

Tout type d'input est accepté (mp4, mkv, mov, webm, mp3, ogg, m4a, wav…) : la piste vidéo est
ignorée (`-vn`) et seule la piste audio est extraite/convertie.

## Endpoints

- `GET /health` → `{"status": "ok", "ffmpeg": "/usr/bin/ffmpeg"}`
- `POST /convert` (multipart/form-data, champ `file`) → renvoie le fichier audio converti

| Paramètre (query) | Défaut    | Description                          |
|-------------------|-----------|--------------------------------------|
| `format`          | `wav`     | `wav`, `mp3`, `ogg`, `m4a`, `flac`   |
| `sample_rate`     | `16000`   | Hz, entre 8000 et 192000             |
| `channels`        | `1`       | entre 1 et 8                         |

Erreurs : `400` (format inconnu / fichier vide), `422` (échec ffmpeg, détail dans le body).

## Démarrage avec Docker

Ajouter dans le `docker-compose.yml` existant (même fichier que n8n), cf. `compose-snippet.yml` :

```yaml
services:
  ffmpeg-api:
    build: .
    container_name: ffmpeg-api
    restart: unless-stopped
    # PAS de section "ports:" : joignable uniquement depuis le réseau Docker interne
```

```bash
docker compose up -d --build ffmpeg-api
```

## Appel depuis n8n

Nœud **HTTP Request** (pas Webhook — celui-ci sert à recevoir, pas à appeler) :

- Method : `POST`
- URL : `http://ffmpeg-api:3103/convert?format=wav&sample_rate=16000&channels=1`
- Send Body : ON → Body Content Type : `Multipart-Form-Data`
- Body Parameters : Parameter Type `n8n Binary File`, Name `file`, Input Data Field Name `data`
- Options → Response → Response Format : `File` (le nœud reçoit le fichier converti en binaire)
- Options → Timeout : `120000` ms pour les longues vidéos

## Test manuel

```bash
curl -o out.wav -F "file=@video.mp4" "http://localhost:3103/convert?format=wav"
```

(pour ce test depuis l'hôte, publier temporairement `"3103:3103"` dans le compose)

## Sécurité

Ne jamais publier le port 3103 sur Internet : le service n'a aucune authentification. Il est
conçu pour rester joignable uniquement par les autres conteneurs du même réseau Docker.

## Développement local

```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 3103
```
