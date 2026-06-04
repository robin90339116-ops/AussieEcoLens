# scripts/create_tables.py
import boto3

dynamodb = boto3.client('dynamodb', region_name='us-east-1')

# 创建主表
dynamodb.create_table(
    TableName='EcoLensFiles',
    KeySchema=[
        {'AttributeName': 'file_url', 'KeyType': 'HASH'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'file_url', 'AttributeType': 'S'},
        {'AttributeName': 'file_hash', 'AttributeType': 'S'},
        {'AttributeName': 'thumbnail_url', 'AttributeType': 'S'},
    ],
    GlobalSecondaryIndexes=[
        {
            'IndexName': 'hash-index',
            'KeySchema': [{'AttributeName': 'file_hash', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'}
        },
        {
            'IndexName': 'thumbnail-index',
            'KeySchema': [{'AttributeName': 'thumbnail_url', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'}
        }
    ],
    BillingMode='PAY_PER_REQUEST'
)
print("EcoLensFiles table created")

# 创建标签表
dynamodb.create_table(
    TableName='EcoLensTags',
    KeySchema=[
        {'AttributeName': 'species', 'KeyType': 'HASH'},
        {'AttributeName': 'file_url', 'KeyType': 'RANGE'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'species', 'AttributeType': 'S'},
        {'AttributeName': 'file_url', 'AttributeType': 'S'},
    ],
    BillingMode='PAY_PER_REQUEST'
)
print("EcoLensTags table created")
