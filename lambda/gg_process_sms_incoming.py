import boto3
import random
import StringIO
import urllib2
import uuid
import json
import time

from boto3.dynamodb.conditions import Key
from boto3.session import Session
from PIL import Image, ImageOps, ImageDraw
from twilio.rest import Client
from googletrans import Translator

# create Twilio session
# Add Twilio Keys
account_sid = "AC6e7b4be234c3fdf028d93dbc23765468"
auth_token = "dbd7e8fe77622e5eb41a30abe5eaf033"
phone_number = "+17255021401"
sns_completion_topic = "arn:aws:sns:us-west-1:878174247419:charity_sent_message"
client = Client(account_sid, auth_token)
translator = Translator()

# create an S3 & Dynamo session
s3 = boto3.resource('s3')
bucket = "globalgivinghack-images"

session = Session()
# Add Dynamo Region and Table
dynamodb = boto3.resource('dynamodb', 'us-west-1')
table_users = dynamodb.Table('GlobalGiving')
table_messages = dynamodb.Table('CharityMessages')

def get_user_details(from_number):
    response_dynamo = table_users.query(KeyConditionExpression=Key('fromNumber').eq(from_number))
    if response_dynamo['Count'] != 1:
        return None
    return (response_dynamo['Items'][0]['name'], response_dynamo['Items'][0]['language'], response_dynamo['Items'][0]['charity'])

def save_message(message_id, user, charity, message, media_url, timestamp):
    table_messages.put_item(Item={'message_id': message_id, 'user_id': user, 'charity_id': charity, 'message': message, 'media_url': media_url, 'timestamp':timestamp})


def handle_media(charity, message_id, pic_url):
    twilio_pic = urllib2.Request(pic_url, headers={'User-Agent': "Magic Browser"})
    image = urllib2.urlopen(twilio_pic)

    # Apply an Image filter
    im_buffer = image.read()
    im = Image.open(StringIO.StringIO(im_buffer))
    im = sample_filter(im)

    # Add to S3 Bucket
    key = "ingest-images/" + str(charity.replace(' ', '_')) + "/" + message_id + ".png"
    media_url = "https://s3.amazonaws.com/{0}/{1}".format(bucket, str(key))

    # build meta data
    m_data = {'charity': charity, 'url': media_url, 'message_id': message_id}
    output = StringIO.StringIO()
    im.save(output, format="PNG")
    im_data = output.getvalue()
    output.close()

    s3.Bucket(bucket).put_object(Key=key, Body=im_data, ACL='public-read', ContentType='image/png', Metadata=m_data)
    item_url = "https://{0}.s3.amazonaws.com/{1}".format(bucket, str(key))
    return item_url

def translate_message(message, lang):
   return translator.translate(message, src=lang, dest="en").text

def fire_sns(charity, media_url, message):
    message = {'charity_id': charity, 'message': message, 'media_url': media_url}
    client = boto3.client('sns')
    response = client.publish(
        TargetArn=sns_completion_topic,
        Message=json.dumps({"default": json.dumps(message)}),
        MessageStructure='json'
    )

def lambda_handler(event, context):

    message = event['body']
    from_number = event['fromNumber']
    pic_url = event['image']
    num_media = event['numMedia']

    # check if we have their number
    user, language, charity = get_user_details(from_number)
    if user == None:
        return "Cannot uniquely identify user"

    message = translate_message(message, language)

    message_id = str(uuid.uuid4());

    media_url = None
    if num_media != '0':
        media_url = handle_media(charity, message_id, pic_url)

    timestamp = int(time.time())
    save_message(message_id, user, charity, message, media_url, timestamp)
    fire_sns(charity, media_url, message)

    return "Thank you for your update"

def sample_filter(im):
    '''
    A simple filter to be applied to the image
    '''
    black = "#000099"
    white= "#99CCFF"
    filter_image = ImageOps.colorize(ImageOps.grayscale(im), black, white)
    return filter_image


