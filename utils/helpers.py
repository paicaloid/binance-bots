import pandas as pd
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


def get_kline_1H(
    client: Client,
    symbol: str,
    limit: int,
) -> list:
    return client.get_klines(
        symbol=symbol,
        interval=Client.KLINE_INTERVAL_1HOUR,
        limit=limit,
    )


def kline_list_to_df(
    kline_list: list,
) -> pd.DataFrame:
    df = pd.DataFrame(
        kline_list,
        columns=[
            "unix_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset",
            "trades",
            "taker_buy_base",
            "take_buy_quote",
            "ignore",
        ],
    )
    df["datetime"] = pd.to_datetime(df["unix_time"], unit="ms", utc=True)
    df["datetime"] = df["datetime"].dt.tz_convert("Asia/Bangkok")
    df = df.set_index("datetime")
    df = df.drop(columns=["unix_time", "close_time", "ignore"])
    df = df.astype(float)
    df["trades"] = df["trades"].astype(int)

    return df[:-1]


def unicornfy_to_dataframe(kline: dict) -> pd.DataFrame:
    df = pd.DataFrame([kline])
    df["datetime"] = pd.to_datetime(df["kline_start_time"], unit="ms", utc=True)
    df["datetime"] = df["datetime"].dt.tz_convert("Asia/Bangkok")
    df = df.set_index("datetime")
    df = df.drop(
        [
            "kline_start_time",
            "kline_close_time",
            "symbol",
            "interval",
            "first_trade_id",
            "last_trade_id",
            "is_closed",
            "ignore",
        ],
        axis=1,
    )
    df = df.rename(
        columns={
            "open_price": "open",
            "close_price": "close",
            "high_price": "high",
            "low_price": "low",
            "base_volume": "volume",
            "number_of_trades": "trades",
            "quote": "quote_asset",
            "taker_by_base_asset_volume": "taker_buy_base",
            "taker_by_quote_asset_volume": "take_buy_quote",
        }
    )
    df = df.astype(float)
    df["trades"] = df["trades"].astype(int)
    return df


def place_order_market_buy(
    client: Client,
    symbol: str,
    quote_order_qty: float,
) -> dict:
    return client.create_order(
        symbol=symbol,
        side=Client.SIDE_BUY,
        type=Client.ORDER_TYPE_MARKET,
        quoteOrderQty=quote_order_qty,
    )


def place_order_market_sell(
    client: Client,
    symbol: str,
    quantity: float,
) -> dict:
    return client.create_order(
        symbol=symbol,
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=quantity,
    )


def get_current_price(client: Client, symbol: str) -> float:
    return float(client.get_symbol_ticker(symbol=symbol).get("price"))


"""
order = client.create_order(
    symbol="OPUSDT",
    side=SIDE_SELL,
    type=ORDER_TYPE_TAKE_PROFIT_LIMIT,
    timeInForce=TIME_IN_FORCE_GTC,
    quantity=9,
    stopPrice='1.400',
    price='1.384',
    trailingDelta='200'
)
"""
