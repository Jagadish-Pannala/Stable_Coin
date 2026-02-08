import http.client
from dotenv import load_dotenv
import os 
load_dotenv()
import json
conn = http.client.HTTPSConnection("api.tenderly.co")

ACCESS_KEY = os.getenv("TENDERLY_ACCESS_TOKEN")
TENDERLY_ACCOUNT = os.getenv("TENDERLY_ACCOUNT")
TENDERLY_PROJECT = os.getenv("TENDERLY_PROJECT")
MAIN_WALLET_ADDRESS = os.getenv("MAIN_WALLET_ADDRESS")
VNET_ID = os.getenv("VNET_ID")

headers = {
    'Accept': "application/json",
    'X-Access-Key': ACCESS_KEY
}

###### getting all the contracts of the project ####
# conn.request("GET", f"/api/v1/account/{TENDERLY_ACCOUNT}/project/{TENDERLY_PROJECT}/contracts?accountType=contract", headers=headers)

# res = conn.getresponse()
# data = res.read()

# print(data.decode("utf-8"))

 ####getting the balance of the main wallet address on the ethereum mainnet ####
# conn.request("GET", f"/api/v1/account/{TENDERLY_ACCOUNT}/project/{TENDERLY_PROJECT}/wallet/{MAIN_WALLET_ADDRESS}/network/1", headers=headers)

# res = conn.getresponse()
# data = res.read()

# print(data.decode("utf-8"))

##### getting all virtual testents of the project ######
# conn.request("GET", f"/api/v1/account/{TENDERLY_ACCOUNT}/project/{TENDERLY_PROJECT}/vnets", headers=headers)

# res = conn.getresponse()
# data = res.read()

# print(data.decode("utf-8"))

##### GETTING ALL TRANSACTIONS(10 Transaction 1 page) ######

# endpoint = f"/api/v1/account/{TENDERLY_ACCOUNT}/project/{TENDERLY_PROJECT}/vnets/{VNET_ID}/transactions"

# conn.request("GET", endpoint, None, headers)

# res = conn.getresponse()
# data = res.read()

# print(data.decode("utf-8"))

## GETTING ALL PAGES TRANSACTIONS ###

page = 1
all_txns = []

while True:
    endpoint = f"/api/v1/account/{TENDERLY_ACCOUNT}/project/{TENDERLY_PROJECT}/vnets/{VNET_ID}/transactions?limit=100&page={page}"


    conn.request("GET", endpoint, None, headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode())

    if not data:   # empty list = no more transactions
        break

    all_txns.extend(data)
    page += 1

print("len", len(all_txns))
print(all_txns)
