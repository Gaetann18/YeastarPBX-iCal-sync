import requests
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os


class YeastarAPI:
    REQUEST_DELAY = 2
    last_request_time = None

    def __init__(self, pbx_url, client_id, client_secret, config_model=None):
        self.pbx_url = pbx_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.config_model = config_model
        self.access_token = None
        self.token_expires_at = None

        if self.config_model:
            self.access_token = self.config_model.access_token
            self.token_expires_at = self.config_model.token_expires_at

    def _rate_limit(self):
        if YeastarAPI.last_request_time is not None:
            elapsed = time.time() - YeastarAPI.last_request_time
            if elapsed < self.REQUEST_DELAY:
                sleep_time = self.REQUEST_DELAY - elapsed
                time.sleep(sleep_time)
        YeastarAPI.last_request_time = time.time()

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'User-Agent': 'OpenAPI'
        }

    def authenticate(self):
        self._rate_limit()

        url = f"{self.pbx_url}/openapi/v1.0/get_token"
        payload = {
            "username": self.client_id,
            "password": self.client_secret
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get('errcode') == 0:
                self.access_token = data['access_token']
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=data['access_token_expire_time'])
                if self.config_model:
                    from app.models import db
                    self.config_model.access_token = self.access_token
                    self.config_model.token_expires_at = self.token_expires_at
                    db.session.commit()

                return True, "Authentification réussie"
            else:
                return False, f"Erreur API: {data.get('errmsg', 'Erreur inconnue')}"

        except requests.exceptions.RequestException as e:
            return False, f"Erreur de connexion: {str(e)}"

    def _ensure_valid_token(self):
        if self.config_model:
            self.access_token = self.config_model.access_token
            self.token_expires_at = self.config_model.token_expires_at

        if not self.access_token or not self.token_expires_at:
            return self.authenticate()

        if datetime.utcnow() + timedelta(minutes=5) >= self.token_expires_at:
            return self.authenticate()

        return True, "Token valide"

    def get_extensions(self):
        success, message = self._ensure_valid_token()
        if not success:
            return None, message

        self._rate_limit()

        url = f"{self.pbx_url}/openapi/v1.0/extension/search"
        params = {'access_token': self.access_token}

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get('errcode') == 0:
                return data.get('data', []), "Extensions récupérées"
            else:
                return None, f"Erreur API: {data.get('errmsg', 'Erreur inconnue')}"

        except requests.exceptions.RequestException as e:
            return None, f"Erreur de connexion: {str(e)}"

    def update_extension_status(self, extension_id, status):
        success, message = self._ensure_valid_token()
        if not success:
            return False, message

        self._rate_limit()

        url = f"{self.pbx_url}/openapi/v1.0/extension/update"
        params = {'access_token': self.access_token}
        payload = {
            "id": extension_id,
            "presence_status": status
        }

        try:
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=self._get_headers(),
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get('errcode') == 0:
                return True, "Statut mis à jour"
            else:
                return False, f"Erreur API: {data.get('errmsg', 'Erreur inconnue')}"

        except requests.exceptions.RequestException as e:
            return False, f"Erreur de connexion: {str(e)}"


class CryptoService:
    @staticmethod
    def get_or_create_key():
        key_file = 'instance/secret.key'

        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            os.makedirs('instance', exist_ok=True)
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    @staticmethod
    def encrypt(data: str) -> str:
        key = CryptoService.get_or_create_key()
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        key = CryptoService.get_or_create_key()
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()
