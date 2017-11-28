import re
import uuid
import time
import datetime
import json
import boto3

from boto3.dynamodb.conditions import Key, Attr

# Add Dynamo Region and Table
dynamodb = boto3.resource('dynamodb', 'us-west-1')
gg_tx = dynamodb.Table('gg_transaction')
gg_info = dynamodb.Table('gg_donor')
gg_donor_event = dynamodb.Table('gg_donor_event')
sns_client = boto3.client('sns')


def pub_to_endpoint(endpoint, data):
    item = dict(data)
    if re.match(r"[^@]+@[^@]+\.[^@]+", endpoint):
        item['donor_email'] = endpoint
        item['event_id'] = str(uuid.uuid4())
        item['timestamp'] = int(time.time() * 1000)
        # write to dynamoDB
        gg_donor_event.put_item(Item=item)
        pub_to_sns(item)
    else:
        raise ValueError('Put to db erred' + str(item))


def data_to_msg(data):
    try:
        return "Dear {},\n".format(data['donor_name']) + \
               "Charity {} just posted an update at {} ". \
                   format(data['charity_id'],
                          datetime.datetime.fromtimestamp(data['timestamp'] / 1000)
                          .strftime('%Y-%m-%d %H:%M:%S')) + \
               " as quoted below:\n    " + \
               data['message'] + "\n" + \
               ("A picture is also uploaded at {}\n".format(data['media_url']) if 'media_url' in data else '') + \
               "We depend on your generous donation for a better future\nThanks for making the world better a better place to live.\n" + \
               "\n\nSincerely,\n Global Giving"
    except:
        raise ValueError(str(data))


def pub_to_sns(data):
    message = data_to_msg(data)
    response = sns_client.publish(
        TargetArn='arn:aws:sns:us-west-1:878174247419:send-email-step-for-bulgaria-foundation',
        Message=message
    )


def lambda_handler(event, context):
    if 'Records' in event:
        for rec in event['Records']:
            if 'Sns' in rec:
                sns = rec['Sns']
                if 'Message' in sns:
                    message = json.loads(sns['Message'])
                    # raise ValueError(str(message))
                    message_handler(message)
                else:
                    raise ValueError('No Message field in Sns: ' + str(sns))
            else:
                raise ValueError('No Sns field in record: ' + str(rec))
    else:
        raise ValueError('No Records field in event: ' + str(event))


def message_handler(client_message):
    if 'message' not in client_message:
        raise ValueError('client_message is missing message field: ' + str(client_message))
    msg = client_message['message']
    charity_id = client_message['charity_id']
    media_url = client_message[
        'media_url'] if 'media_url' in client_message else 'https://globalgivinghack-images.s3.amazonaws.com/ingest-images/Step_for_Bulgaria_Foundation/636b0a47-2351-48db-82e7-f1731df82d1b.png'
    # check if we have their number
    gg_tx_response = gg_tx.scan(FilterExpression=Attr('charity_id').eq(charity_id))

    # a new user
    if gg_tx_response['Count'] > 0:
        for item in gg_tx_response['Items']:
            donor_id = item['donor_email']
            donor_name = 'John Doe'
            donor_info_response = gg_info.scan(
                FilterExpression=Attr('donor_email').eq(donor_id))
            if donor_info_response['Count'] > 0:
                donor = donor_info_response['Items'][0]
                update_via = donor['update_via']
                endpoint = donor['donor_email']
                if 'Name' in donor:
                    donor_name = donor['Name']
                data = {'message': msg, 'charity_id': charity_id, 'donor_name': donor_name,
                        'media_url': media_url}
                pub_to_endpoint(endpoint, data)
            else:
                raise ValueError('No Donor found: ' + donor_id)
    else:
        raise ValueError('No donor transaction found for: ' + charity_id)


if __name__ == '__main__':
    item = {'donor_email': 'abc@gmail.com', 'event_id': '3343', 'timestamp': 123434343,
            'message': 'I am good'}
    print data_to_msg({})
