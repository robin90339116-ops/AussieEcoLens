# Route B (Oracle/OCI) Service Test Evidence

Service: FastAPI ml_service.py running on this OCI instance, models preloaded.

## /health
{"status":"ok","models_loaded":true,"load_error":null,"auth_required":true}

## Auth enforcement
- No token -> 401
- Bad token -> 403
- Valid token -> 200

## /v1/tag/s3 (presigned URL flow), Alectura_lathami_1
{"status":"ok","file_id":"4838f68beda023672f39c751958e5e51cdbb2c5b4c8c968c3769215f9d076354","file_type":"image","original_bucket":"aussie-ecolens-uploads","original_key":"uploads/Alectura_lathami_1.JPG","original_url":"https://aussie-ecolens-uploads.s3.amazonaws.com/uploads/Alectura_lathami_1.JPG","thumbnail_url":"https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg","checksum":null,"tags":{"australian brushturkey":1},"predictions":[{"scientific_name":"Alectura_lathami","confidence":0.9999760389328003,"source":"89d5513d6f3a48eba9e21a6ac513cb57-0","common_name":"australian brushturkey"}],"created_at":"2026-06-01T15:39:18Z","detections":1,"persisted":false}
