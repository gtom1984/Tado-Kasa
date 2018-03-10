import os
import json
import logging
import boto3
from base64 import b64decode
from botocore.vendored import requests

HUMIDITY_THRESHOLD = float(os.environ['HUMIDITY_THRESHOLD'])

TADO_USERNAME = os.environ['TADO_USERNAME']
TADO_PASSWORD = boto3.client('kms').decrypt(CiphertextBlob=b64decode(os.environ['TADO_PASSWORD']))['Plaintext'].decode("UTF-8")

KASA_USERNAME = os.environ['KASA_USERNAME']
KASA_PASSWORD = boto3.client('kms').decrypt(CiphertextBlob=b64decode(os.environ['KASA_PASSWORD']))['Plaintext'].decode("UTF-8")
KASA_DEVICE_ALIAS = os.environ['KASA_DEVICE']
KASA_REGION_URL = os.environ['KASA_URL']

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


def lambda_handler(event, context):
    humidity = get_humidity(get_tado_token(TADO_USERNAME, TADO_PASSWORD))
    kasa_device = get_kasa_device(get_kasa_token(KASA_USERNAME, KASA_PASSWORD), KASA_DEVICE_ALIAS)
    kasa_token = get_kasa_token(KASA_USERNAME, KASA_PASSWORD)

    if humidity > HUMIDITY_THRESHOLD:
        return "Humidity: " + str(humidity) + " " + set_kasa_device(kasa_token, kasa_device, 1)
    else:
        return "Humidity: " + str(humidity) + " " + set_kasa_device(kasa_token, kasa_device, 0)
