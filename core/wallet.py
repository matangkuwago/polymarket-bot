import json
import dataclasses
import requests
from dataclasses import dataclass, field
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
from core.config import Config


@dataclass
class Wallet:

    funder_address: str
    private_key: str
    signature_type: int

    # for storing polymarket client object
    _clob_client: ClobClient = field(init=False, repr=False, default=None)

    @property
    def clob_client(self) -> ClobClient:
        if self._clob_client is not None:
            return self._clob_client
        try:
            if self.signature_type in (1, 2):
                if not self.funder_address:
                    raise ValueError(
                        "FUNDER_ADDRESS required when SIGNATURE_TYPE=1 or 2")
                self._clob_client = ClobClient(
                    host=Config.CLOB_API,
                    key=self.private_key,
                    chain_id=Config.CHAIN_ID,
                    signature_type=self.signature_type,
                    funder=self.funder_address,
                )
            else:
                self._clob_client = ClobClient(
                    host=Config.CLOB_API,
                    key=self.private_key,
                    chain_id=Config.CHAIN_ID,
                )

            # Derive API credentials
            creds = self._clob_client.create_or_derive_api_creds()
            self._clob_client.set_api_creds(creds)
            return self._clob_client
        except Exception as e:
            raise RuntimeError(f"Failed to init ClobClient: {e}")

    def portfolio_value(self) -> float:
        portfolio_url = f"https://data-api.polymarket.com/value?user={self.funder_address}"
        response = requests.get(url=portfolio_url)
        if response and response.status_code == 200:
            data = response.json()
            return float(data[0]["value"])

        response.raise_for_status()

    def available_balance(self) -> float:
        collateral = self.clob_client.get_balance_allowance(
            params=BalanceAllowanceParams(
                asset_type=AssetType.COLLATERAL, signature_type=self.signature_type)
        )

        if collateral and 'balance' in collateral:
            return float(collateral['balance']) / Config.USDC_TICK_SIZE

        raise ValueError(
            f"Unable to get available balance for wallet {self.funder_address}")

    def total_balance(self) -> float:
        return self.portfolio_value() + self.available_balance()


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            data = dataclasses.asdict(o)
            if "_clob_client" in data:
                del data["_clob_client"]
            return data
        return super().default(o)


class WalletManager:

    def __init__(self, wallet_config_file: str = Config.WALLET_SETTINGS_FILE):
        self.wallet_config_file = wallet_config_file
        try:
            self.wallets = {}
            with open(self.wallet_config_file, 'r') as f:
                _wallets = json.load(f)
                for id, wallet_data in _wallets.items():
                    self.wallets[id] = Wallet(**wallet_data)
        except FileNotFoundError as e:
            self.wallets = {}
        except json.JSONDecodeError:
            self.wallets = {}

    def _assert_wallet_id_does_not_exist(self, id: str):
        if id in self.wallets:
            raise ValueError(f"Wallet ID exist: {id}!")

    def _assert_wallet_id_exists(self, id: str):
        if id not in self.wallets:
            raise ValueError(f"Wallet ID does not exist: {id}!")

    def _save(self):
        with open(self.wallet_config_file, 'w') as f:
            json.dump(self.wallets, f, indent=4, cls=EnhancedJSONEncoder)

    def add_wallet(self, id: str, funder_address: str, private_key: str, signature_type: int):
        self._assert_wallet_id_does_not_exist(id)
        self.wallets[id] = Wallet(
            funder_address=funder_address,
            private_key=private_key,
            signature_type=signature_type
        )
        self._save()

    def update_wallet(self, id: str, funder_address: str, private_key: str, signature_type: int):
        self._assert_wallet_id_exists(id)
        self.wallets[id].funder_address = funder_address
        self.wallets[id].private_key = private_key
        self.wallets[id].signature_type = signature_type
        self._save()

    def get_wallet(self, id: str) -> Wallet:
        self._assert_wallet_id_exists(id)
        return self.wallets[id]
