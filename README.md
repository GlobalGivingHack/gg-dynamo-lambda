# gg-dynamo-lambda
Explanation of how-to deploy our lovely software.

## lambdas
gg_process_sms_incoming.py
Triggered by the twilio-apigateway API Gateway GET request to /addphoto when the charity sends a SMS / MMS via Twilio.
- Stores the SMS text in CharityMessages, along with the charity the number belongs to
- For an MMS, calls handle_media to store the image in an S3 bucket, and for the demo, adds a greyscale filter, but you could add a GlobalGiving watermark.  

Event data:
```javascript
{
    "body": "SMS text",
    "fromNumber": "SMS number sent from",
    "image": "For MMS, the URI of the attached image",
    "numMedia": "For MMS, how many images were attached"
 }
```

gg_notify_donors.py
Subscribes to an SNS Topic notifying an SMS was received.
- Sends a push to an SNS topic dedicated to that charity, whose subscribers are the email of the donors.
- Stores in gg_donor_event the list of donors for a charity along with the message sent, making it possible to show a donor their personal updates, as a future feature.

Event data:
- Records.Sns.Message contains the actual message, the rest is SNS meta data.
```javascript
{
  "Records": [
    {
      "EventVersion": "1.0",
      "EventSource": "aws:sns",
      "EventSubscriptionArn": "arn:aws:sns:us-west-1:878174247419:charity_sent_message:206c4ff7-343a-4e83-93c2-1db8890f245f",
      "Sns": {
        "SignatureVersion": "1",
        "Timestamp": "2017-11-28T01:03:57.976Z",
        "Signature": "TNvWgm/LmbVyR40xkQlgW6SxWFE3svvfvIf4SCMLegbv8muxYU5+PZ4oFF+IsnxcvlduVW4ytg+fNCFGVRTYnU5IyhqGhKCUtR/LKjriTlwc1NvWpvplX9okRyvq/iwnlxvbWOYBNxDQxdQ+mAotETVLEPvJHaBIn63vBEwER76jK1Q9FOenb0XE+eXXPLRAd+AeTTmQHBRa5r7eEZA13EWlboawJk5owg3+uKtKwFHQim52vUJg5VKkR9JLN5TN797S78DcJJPCoeUWRvJX9lm3WbWDk44vTEOyeMvbYiqG5ru6ZSsnrvOQ0U5YMMBh5jYCDfavXY5+rZVKmpXAVg==",
        "SigningCertUrl": "https://sns.us-west-1.amazonaws.com/SimpleNotificationService-433026a4050d206028891664da859041.pem",
        "MessageId": "22dbc559-ae6c-5d12-aa77-97cf16517ddd",
        "Message": "{\"charity_id\": \"Hurricane Harvey Relief Fund\", \"message\": \"Body body body\"}",
        "Subject": "None",
        "Type": "Notification",
        "UnsubscribeUrl": "https://sns.us-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-west-1:878174247419:charity_sent_message:206c4ff7-343a-4e83-93c2-1db8890f245f",
        "TopicArn": "arn:aws:sns:us-west-1:878174247419:charity_sent_message",
        "MessageAttributes": {}
      }
    }
  ]
}
```

## AWS architecture
[Architecture diagram](https://raw.githubusercontent.com/GlobalGivingHack/gg-dynamo-lambda/master/aws_architecture_diagram.png)
### DynamoDb
- CharityMessages is populated with the SMS and attachment sent by a charity. The UI renders this table.
- GlobalGiving maps the charity to the mobile # sending the message.
- gg_donor, gg_donor_event and gg_transaction were future ideas to store each message sent by a charity against their donors, for the personalised donor wall. gg_notify_donors uses these tables.

### SNS
- charity_sent_message is published to by gg_process_sms_incoming.py after the message is processed.
- send-email-step-for-bulgaria-foundation contains donor email subscriptions. gg_notify_donors publishes to it with the charity's message and attachment link.
     
### API Gateway
- twilio-apigateway invokes gg_process_sms_incoming.py when an SMS is sent by Twilio.