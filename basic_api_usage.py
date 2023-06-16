import requests
import json

url = 'http://127.0.0.1:8000/'

config = {"data_path": "data_integrity.xlsx"}

res = requests.get(url + "all_checks?data_path=data_integrity.xlsx") 
            
with open("api_response.json", "w") as f:
    json.dump(res.json(), f, indent=4)


