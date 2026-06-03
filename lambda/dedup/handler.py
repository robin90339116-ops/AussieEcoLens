# lambda/dedup/handler.py
import boto3
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('EcoLensFiles')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        file_hash = body['file_hash']

        response = table.query(
            IndexName='hash-index',
            KeyConditionExpression='file_hash = :hash',
            ExpressionAttributeValues={':hash': file_hash}
        )

        if response['Items']:
            return {
                'statusCode': 409,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'duplicate': True,
                    'message': 'File already exists',
                    'existing_file': response['Items'][0]['file_url']
                })
            }

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'duplicate': False})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }