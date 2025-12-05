from app.services.yeastar_api import YeastarAPI, CryptoService
from app.models import Config
import logging

logger = logging.getLogger(__name__)

class APIManager:
    _instance = None
    _api = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_api(self):
        if self._api is None:
            self._initialize_api()
        return self._api

    def _initialize_api(self):
        config = Config.query.first()
        if not config:
            logger.error("Configuration Yeastar non trouvée en base")
            return None

        client_secret = CryptoService.decrypt(config.client_secret_encrypted)
        self._api = YeastarAPI(
            config.pbx_url,
            config.client_id,
            client_secret,
            config_model=config
        )
        logger.info("Instance API Yeastar initialisée")

    def reset_api(self):
        self._api = None
        logger.info("Instance API Yeastar réinitialisée")
