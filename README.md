# Tado-Kasa
***Simple AWS Lambda Python script to turn on/off a smart plug if Tado humidity is over a threshold***

**Requirements:**
TADO Smart Thermostat and Tado account

TP-Link HS110 Smart Plug and Kasa cloud account

A dehumidifier to plug into the smart plug

Amazon Web Services account

**How it works:**
- A cloud watch event is run every 4 hours (or whenever you choose).
- The event triggers the Python Lambda script (with KMS keys to encrypt the account passwords)
- The Tado's humidity will be read from the cloud account
- The smart plug will be activated if the humidity is over a certain threshold
- It will be shut off if the humidity drops below the threshold when the script is runs again

The humidity and plug's responses are recorded in the AWS Cloud Watch logs

**Configuration:**
All configuration is handled by AWS Lambda's environment variables

- HUMIDITY_THRESHOLD = provide a float
- TADO_USERNAME = plain text username (your email)
- TADO_PASSWORD = your Tado account's password, be sure to enabled KMS encryption the script assumes you did!
- KASA_USERNAME = plain text username (your email)
- KASA_PASSWORD = your Kasa account's password, be sure to enabled KMS encryption the script assumes you did!
- KASA_DEVICE_ALIAS = the device's alias as set in the iOS or Android Kasa app, this is a simple plain text name for your plug, make it unique or the script will pick the first one
- KASA_REGION_URL = Your region's URL for your account (this was tested with "https://eu-wap.tplinkcloud.com/")
