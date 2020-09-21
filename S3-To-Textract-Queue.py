import json
import urllib
import boto3
import os

snsTopicArn = os.environ['SNS_TOPIC_ARN']
roleArn = os.environ['ROLE_ARN']
region = os.environ['REGION']
jobTab = os.environ['JOB_TAG']

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    client = boto3.client('textract', 'us-east-2')

    client.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        NotificationChannel={
            'SNSTopicArn': snsTopicArn,
            'RoleArn': roleArn,
        },
        JobTag='Transcript'
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Entry Queue for OCR!')
    }
