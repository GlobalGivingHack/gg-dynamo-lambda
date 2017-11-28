import re
import uuid
import time
import boto3

from boto3.dynamodb.conditions import Key, Attr
from boto3.session import Session

# # create Twilio session
# # Add Twilio Keys
# account_sid = "account_sid"
# auth_token = "auth_token"
# client = TwilioRestClient(account_sid, auth_token)

# create an S3 & Dynamo session
s3 = boto3.resource('s3')
session = Session()
# Add Dynamo Region and Table
dynamodb = boto3.resource('dynamodb', 'us-west-1')
gg_tx = dynamodb.Table('gg_transaction')
gg_info = dynamodb.Table('gg_donor')
gg_donor_event = dynamodb.Table('gg_donor_event')


def pub_to_endpoint(endpoint, data):
    item = dict(data)
    if re.match(r"[^@]+@[^@]+\.[^@]+", endpoint):
        item['donor_email'] = endpoint
        item['event_id'] = str(uuid.uuid4())
        item['timestamp'] = int(time.time() * 1000)
        # write to dynamoDB
        gg_donor_event.put_item(Item=item)
    else:
        raise ValueError('Put to db erred' + str(item))


def lambda_handler(event, context):
    if 'message' not in event:
        raise ValueError('Event is mising fields: ' + str(event))
    message = event['message']
    charity_id = event['charity_id']
    # check if we have their number
    gg_tx_response = gg_tx.scan(FilterExpression=Attr('charity_id').eq(charity_id))

    # a new user
    if gg_tx_response['Count'] > 0:
        for item in gg_tx_response['Items']:
            donor_id = item['donor_email']
            donor_info_response = gg_info.scan(
                FilterExpression=Attr('donor_email').eq(donor_id))
            if donor_info_response['Count'] > 0:
                donor = donor_info_response['Items'][0]
                update_via = donor['update_via']
                endpoint = donor['donor_email']
                data = {'message': message, 'charity_id': charity_id}
                pub_to_endpoint(endpoint, data)
            else:
                raise ValueError('No Donor found: ' + donor_id)
    else:
        raise ValueError('No donor transaction found for: ' + charity_id)
