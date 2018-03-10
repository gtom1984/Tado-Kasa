# Tado-Kasa
Simple AWS Lambda Python script to turn on/off a smart plug if Tado humidity is over a threshold

Requirements:
TADO Smart Thermostat and Tado account

TP-Link HS110 Smart Plug and Kasa cloud account

A dehumidifier to plug into the smart plug

Amazon Web Services account

How it works:
- A cloud watch event is run every 4 hours (or whenever you choose).
- The event triggers the Python Lambda script (with KMS keys to encrypt the account passwords)
- The Tado's humidity will be read from the cloud account
- The smart plug will be activated if the humidity is over a certain threshold
- It will be shut off if the humidity drops below the threshold when the script is runs again

The humidity and plug's responses are recorded in the AWS Cloud Watch logs
