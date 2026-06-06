# lambda/presigned/handler.py
import boto3
import json
import os
import uuid
from botocore.config import Config

# Force SigV4 execution to avoid cross-region authentication hiccups
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
BUCKET = os.environ.get('BUCKET_NAME', 'aussie-ecolens-35346906')

def lambda_handler(event, context):
    # Set default CORS headers to prevent cross-origin blocks
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'PUT')  # Default to upload behavior if not specified

        # ==========================================
        # CASE 1: READ FILE OPERATIONS (GET)
        # ==========================================
        if action == 'GET':
            s3_url_or_key = body.get('s3_url') or body.get('file_key')
            if not s3_url_or_key:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Missing s3_url or file_key parameter'})
                }
            
            # Clean up the key if it was passed as a full URL path
            file_key = s3_url_or_key.split(f"{BUCKET}/")[-1] if f"{BUCKET}/" in s3_url_or_key else s3_url_or_key
            # Strip alternative direct domain structural formats if present
            file_key = file_key.split("://")[-1] if "://" in file_key else file_key

            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET, 'Key': file_key},
                ExpiresIn=3600
            )
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'presigned_url': presigned_url})
            }

        # ==========================================
        # CASE 2: WRITE FILE OPERATIONS (PUT)
        # ==========================================
        filename = body['filename']
        content_type = body.get('content_type', 'application/octet-stream')
        custom_prefix = body.get('prefix')

        ext = filename.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif']:
            prefix = 'uploads/images'
        elif ext in ['mp4', 'avi', 'mov', 'mkv', 'wmv']:
            prefix = 'uploads/videos'
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Unsupported file type'})
            }

        if custom_prefix:
            allowed_prefixes = {'uploads/images', 'uploads/videos', 'temp'}
            if custom_prefix.strip('/') not in allowed_prefixes:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'prefix not allowed'})
                }
            prefix = custom_prefix

        file_hash = body.get('file_hash') or body.get('checksum')
        unique_name = f"{file_hash}_{filename}" if file_hash else f"{uuid.uuid4().hex}_{filename}"
        file_key = f"{prefix}/{unique_name}"

        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}) or {}
        owner_id = claims.get('sub') or claims.get('email')

        params = {
            'Bucket': BUCKET,
            'Key': file_key,
            'ContentType': content_type
        }
        upload_headers = {}
        if owner_id:
            params['Metadata'] = {'owner-id': owner_id}
            upload_headers['x-amz-meta-owner-id'] = owner_id

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params=params,
            ExpiresIn=3600
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'upload_url': presigned_url,
                'file_key': file_key,
                'bucket': BUCKET,
                'upload_headers': upload_headers
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
