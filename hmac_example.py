import requests
from requests.auth import AuthBase
import hmac
import hashlib
from datetime import datetime


# Class to perform HMAC encoding
class AuthHmacMetosGet(AuthBase):
    # Creates HMAC authorization header for Metos REST service GET request.
    def __init__(self, apiRoute, publicKey, privateKey):
        self._publicKey = publicKey
        self._privateKey = privateKey
        self._method = 'GET'
        self._apiRoute = apiRoute

    def __call__(self, request):
        dateStamp = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        print("timestamp: ", dateStamp)
        request.headers['Date'] = dateStamp
        msg = (self._method + self._apiRoute + dateStamp + self._publicKey).encode('utf-8')
        signature = hmac.new(
            self._privateKey.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()
        request.headers['Authorization'] = f'hmac {self._publicKey}:{signature}'
        return request


# Endpoint of the API, version for example: v1
apiURI = 'https://api.fieldclimate.com/v2'

# HMAC Authentication credentials
publicKey = 'e27ff5b65209c24072989f66c86a6d8d83cdcb151a1badef'
privateKey = 'd0856dd8848ad9441801f0e5cb5745e63d3247684a5d4d9f'

# Service/Route that you wish to call
apiRoute = '/user'

auth = AuthHmacMetosGet(apiRoute, publicKey, privateKey)
response = requests.get(apiURI + apiRoute, headers={'Accept': 'application/json'}, auth=auth)

# Print response JSON
print(response.json())
