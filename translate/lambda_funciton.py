from googletrans import Translator
translator = Translator()

def lambda_handler(event, context):
    # TODO implement
    translation = translator.translate("Hello from Lambda", dest="ko")

    return translation.text

