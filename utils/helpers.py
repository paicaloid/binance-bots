from binance.client import Client
from pydantic import BaseModel


class PriceFilter(BaseModel):
    min_price: float
    max_price: float
    tick_size: float


class LotSizeFilter(BaseModel):
    min_qty: float
    max_qty: float
    step_size: float


class MarketLotSizeFilter(BaseModel):
    min_qty: float
    max_qty: float
    step_size: float


class NotionalFilter(BaseModel):
    min_notional: float
    max_notional: float


class Symbol(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    price_filter: PriceFilter
    lot_size_filter: LotSizeFilter
    market_lot_size_filter: MarketLotSizeFilter
    notional_filter: NotionalFilter


def get_balances(client: Client) -> dict:
    balance_list = client.get_account().get("balances")
    return {item.get("asset"): item for item in balance_list}


def get_symbol_info(client: Client, symbol: str) -> Symbol:
    info = client.get_symbol_info(symbol=symbol)
    if info is None:
        raise ValueError("Symbol not found")

    filters = {item.get("filterType"): item for item in info.get("filters")}

    return Symbol(
        symbol=info.get("symbol"),
        base_asset=info.get("baseAsset"),
        quote_asset=info.get("quoteAsset"),
        price_filter=PriceFilter(
            min_price=float(filters.get("PRICE_FILTER").get("minPrice")),
            max_price=float(filters.get("PRICE_FILTER").get("maxPrice")),
            tick_size=float(filters.get("PRICE_FILTER").get("tickSize")),
        ),
        lot_size_filter=LotSizeFilter(
            min_qty=float(filters.get("LOT_SIZE").get("minQty")),
            max_qty=float(filters.get("LOT_SIZE").get("maxQty")),
            step_size=float(filters.get("LOT_SIZE").get("stepSize")),
        ),
        market_lot_size_filter=MarketLotSizeFilter(
            min_qty=float(filters.get("MARKET_LOT_SIZE").get("minQty")),
            max_qty=float(filters.get("MARKET_LOT_SIZE").get("maxQty")),
            step_size=float(filters.get("MARKET_LOT_SIZE").get("stepSize")),
        ),
        notional_filter=NotionalFilter(
            min_notional=float(filters.get("NOTIONAL").get("minNotional")),
            max_notional=float(filters.get("NOTIONAL").get("maxNotional")),
        ),
    )


def get_open_orders(client: Client, symbol: str) -> list:
    return client.get_open_orders(symbol=symbol)
