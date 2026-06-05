import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'AussieEcoLensFiles'))

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        checksum = body.get('checksum') or body['file_hash']

        response = table.query(
            IndexName='checksum-index',
            KeyConditionExpression='checksum = :c',
            ExpressionAttributeValues={':c': checksum}
        )

        if response['Items']:
            item = response['Items'][0]
            return {
                'statusCode': 409,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'duplicate': True,
                    'message': 'File already exists',
                    'file_id': item['file_id'],
                    'existing_file': item.get('original_url', '')
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
