import os
import json
import logging
import boto3
import time
from base64 import b64decode
from botocore.vendored import requests

HUMIDITY_THRESHOLD = float(os.environ['HUMIDITY_THRESHOLD'])
CURRENT_ALERT = os.environ['CURRENT_ALERT']

TADO_USERNAME = os.environ['TADO_USERNAME']
TADO_PASSWORD = boto3.client('kms').decrypt(CiphertextBlob=b64decode(os.environ['TADO_PASSWORD']))['Plaintext'].decode("UTF-8")

KASA_USERNAME = os.environ['KASA_USERNAME']
KASA_PASSWORD = boto3.client('kms').decrypt(CiphertextBlob=b64decode(os.environ['KASA_PASSWORD']))['Plaintext'].decode("UTF-8")
KASA_DEVICE_ALIAS = os.environ['KASA_DEVICE']
KASA_REGION_URL = os.environ['KASA_URL']
SENDER = "Dehumidifier <" + os.environ['SENDER_EMAIL'] + ">"
RECIPIENT = os.environ['RECIPIENT_EMAIL']
AWS_REGION = os.environ['AWS_REGION']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_tado_token(username, password):
    data = {'username': username,
            'password': password,
            'scope': 'home.user',
            'grant_type': 'password',
            'client_id': 'public-api-preview',
            'client_secret': '4HJGRffVR8xb3XdEUQpjgZ1VplJi6Xgw'
            }

    # Get TADO OAUTH Token
    response = requests.post("https://auth.tado.com/oauth/token",
                             data=data)

    json_data = json.loads(response.text)
    return json_data['access_token']


def get_humidity(token):
    headers = {"Authorization": "Bearer " + token}

    # Get Home ID
    response = requests.get("https://my.tado.com/api/v2/me", headers=headers)
    json_data = json.loads(response.text)
    home_id = str(json_data['homes'][0]['id'])

    # Get Humidity
    response = requests.get("https://my.tado.com/api/v2/homes/" + home_id + "/zones/1/state", headers=headers)
    json_data = json.loads(response.text)
    return json_data['sensorDataPoints']['humidity']['percentage']


def get_kasa_token(username, password):
    # Get Kasa OAUTH Token
    data = {'method': 'login',
            'params': {"appType": "Kasa_Android",
                       "cloudUserName": username,
                       "cloudPassword": password,
                       "terminalUUID": "MY_UUID_v4"
                       }
            }

    response = requests.post(KASA_REGION_URL,
                             json=data)

    data = json.loads(response.text)
    return data['result']['token']


def get_kasa_device(token, alias):
    response = requests.post(KASA_REGION_URL + "?token=" + token, json={"method": "getDeviceList"})

    data = json.loads(response.text)
    device_list = data['result']['deviceList']

    # Get smart plug device ID
    for device in device_list:
        if device['alias'] == alias:
            return {'id': device['deviceId'], 'url': device['appServerUrl']}

    return None


def set_kasa_device(token, device, state=0):
    # IMPORTANT: The device is very picky about the JSON format for the actual commands
    data = {
        "method": "passthrough",
        "params": {
            "deviceId": device['id'],
            "requestData": "{\"system\":{\"set_relay_state\":{\"state\":" + str(state) + "}}}"
        }
    }
    response = requests.post(device['url'] + "?token=" + token, json=data)
    return response.text


def get_kasa_device_state(token, device):
    # IMPORTANT: The device is very picky about the JSON format for the actual commands
    data = {
        "method": "passthrough",
        "params": {
            "deviceId": device['id'],
            "requestData": "{\"system\":{\"get_sysinfo\":{}}}"
        }
    }
    response = requests.post(device['url'] + "?token=" + token, json=data)
    data = json.loads(response.text)
    data_unformated = data['result']['responseData'].replace("\\", "")
    data_formated = json.loads(data_unformated)
    return data_formated['system']['get_sysinfo']['relay_state']


def get_kasa_device_power_usage(token, device):
    # IMPORTANT: The device is very picky about the JSON format for the actual commands
    data = {
        "method": "passthrough",
        "params": {
            "deviceId": device['id'],
            "requestData": "{\"emeter\":{\"get_realtime\":{}}}"
        }
    }
    response = requests.post(device['url'] + "?token=" + token, json=data)
    data = json.loads(response.text)
    data_unformated = data['result']['responseData'].replace("\\", "")
    data_formated = json.loads(data_unformated)
    return data_formated['emeter']['get_realtime']['current']


def send_email(region, sender, recipient, message):
    # The subject line for the email.
    SUBJECT = "Tado-Kasa Alert"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = (message)

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=region)

    client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=sender,
        )


def lambda_handler(event, context):
    try:
        tado_token = get_tado_token(TADO_USERNAME, TADO_PASSWORD)
        humidity = get_humidity(tado_token)
        
        kasa_token = get_kasa_token(KASA_USERNAME, KASA_PASSWORD)
        kasa_device = get_kasa_device(kasa_token, KASA_DEVICE_ALIAS)
        kasa_device_state = get_kasa_device_state(kasa_token, kasa_device)

        if humidity > HUMIDITY_THRESHOLD:
            # Turn on if over threshold
            send_email(AWS_REGION, SENDER, RECIPIENT, "Humidity over threshold, activating dehumidifier")
            
            if kasa_device_state == 0:
                set_kasa_device(kasa_token, kasa_device, 1)
                result = "device turned on"
            else:
                result = "device already running"

            # Wait 30 seconds before checking current
            time.sleep(30)
            current = get_kasa_device_power_usage(kasa_token, kasa_device)
    
            # Turn off and email if current is low
            if current < float(CURRENT_ALERT):
                send_email(AWS_REGION, SENDER, RECIPIENT, "Dehumidifer might need water emptied")
                set_kasa_device(kasa_token, kasa_device, 0)
                result = "device turned off because of low current"
      
            return "Humidity: " + str(humidity) + " " + result
        else:
            # Turn off if below threshold
            if kasa_device_state == 1:
                result = "device turned off"
                set_kasa_device(kasa_token, kasa_device, 0)
            else:
                result = "device already off"

            return "Humidity: " + str(humidity) + " " + result
    except Exception as ex:
        send_email(AWS_REGION, SENDER, RECIPIENT, str(ex))
