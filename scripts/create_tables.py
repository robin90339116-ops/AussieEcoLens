# =============================================================
# DEPRECATED (2026-06-05): this script creates the OLD schema
# (EcoLensFiles / EcoLensTags) which the team no longer uses.
# Team-wide schema is now Module D's: infra/dynamodb/schema.md
# (table AussieEcoLensFiles, PK file_id, GSI checksum-index +
# owner_id-index; notifications table AussieEcoLensNotificationsSub).
#
# The new files table was created on the demo account with:
#
# aws dynamodb create-table \
#   --table-name AussieEcoLensFiles \
#   --attribute-definitions AttributeName=file_id,AttributeType=S AttributeName=checksum,AttributeType=S AttributeName=owner_id,AttributeType=S \
#   --key-schema AttributeName=file_id,KeyType=HASH \
#   --global-secondary-indexes '[{"IndexName":"checksum-index","KeySchema":[{"AttributeName":"checksum","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}},{"IndexName":"owner_id-index","KeySchema":[{"AttributeName":"owner_id","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
#   --billing-mode PAY_PER_REQUEST \
#   --region us-east-1
# =============================================================

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
