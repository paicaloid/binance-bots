import os

from binance.client import Client
from dotenv import find_dotenv, load_dotenv

from utils.helpers import get_balances, get_open_orders, get_symbol_info

load_dotenv(
    find_dotenv(filename=".env.local", raise_error_if_not_found=True),
    override=True,
)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")


class BinanceAPI:
    def __init__(self, symbol: str):
        self.client = Client(api_key=API_KEY, api_secret=API_SECRET)
        self.symbol_info = get_symbol_info(
            client=self.client,
            symbol=symbol,
        )
        self.balances = get_balances(client=self.client)
        self.check_portfolio()

    def check_portfolio(self):
        base_asset = self.symbol_info.base_asset
        base_asset_vol = float(self.balances.get(base_asset).get("free"))
        lot_size_min_qty = self.symbol_info.lot_size_filter.min_qty
        if base_asset_vol > lot_size_min_qty:
            raise ValueError(
                f"Base asset volume {base_asset_vol} is greater"
                + f" than lot size min qty {lot_size_min_qty}"
                + "please adjust your portfolio"
            )

        orders = get_open_orders(client=self.client, symbol=self.symbol_info.symbol)
        if orders:
            raise ValueError(
                f"Open orders for {self.symbol_info.symbol} found"
                + " please cancel them"
            )


if __name__ == "__main__":
    b_api = BinanceAPI(symbol="OPUSDT")
