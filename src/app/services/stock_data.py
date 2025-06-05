from app.config.logger import setup_logger

import logging
import time
from datetime import datetime
from typing import List, Optional, Union

import yfinance as yf

logger = setup_logger("logs/stock_data.log")

def normalize_date_field(field: Union[List[int], int, None]) -> Optional[Union[str, List[str]]]:
    """Normaliza timestamps (ou listas) para strings 'YYYY-MM-DD HH:MM:SS' UTC."""
    if isinstance(field, list):
        return [datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") for ts in field]
    if isinstance(field, (int, float)):
        return datetime.utcfromtimestamp(field).strftime("%Y-%m-%d %H:%M:%S")
    return None


def get_stock_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d",
    period: Optional[str] = None,
    auto_adjust: bool = True,
) -> dict:
    """
    Retorna histórico e informações gerais de um ticker usando yfinance.
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(f"[get_stock_data] Símbolo={symbol} de {start_date} até {end_date} intervalo:({interval}) periodo:({period}) auto_adjust:({auto_adjust})")

    ticker = yf.Ticker(symbol)
    df = ticker.history(
        start=start_date,
        end=end_date,
        interval=interval,
        period=period,
        auto_adjust=auto_adjust,
        actions=False,
    )
    time.sleep(1)

    if df.empty:
        logger.error("Nenhum dado histórico retornado")
        raise ValueError(f"Nenhum dado histórico encontrado para {symbol}")

    # Corrige timezone do índice do DataFrame
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
        logger.info("Timezone do índice do DataFrame foi definido como UTC")
    else:
        df.index = df.index.tz_convert("UTC")
        logger.info("Timezone do índice do DataFrame foi convertido para UTC")

    info = ticker.info
    ex_div = normalize_date_field(info.get("exDividendDate"))
    earnings = normalize_date_field(info.get("earningsDate"))

    data_evolution = []
    for dt, row in df.iterrows():
        data_evolution.append({
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })

    result = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "interval": interval,
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "quoteType": info.get("quoteType"),
        "marketState": info.get("marketState"),
        "regularMarketPrice": info.get("regularMarketPrice"),
        "regularMarketChange": info.get("regularMarketChange"),
        "regularMarketChangePercent": info.get("regularMarketChangePercent"),
        "regularMarketOpen": info.get("regularMarketOpen"),
        "regularMarketPreviousClose": info.get("regularMarketPreviousClose"),
        "regularMarketDayHigh": info.get("dayHigh"),
        "regularMarketDayLow": info.get("dayLow"),
        "regularMarketVolume": info.get("volume"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "averageDailyVolume3Month": info.get("averageDailyVolume3Month"),
        "averageDailyVolume10Day": info.get("averageDailyVolume10Day"),
        "marketCap": info.get("marketCap"),
        "enterpriseValue": info.get("enterpriseValue"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "priceToBook": info.get("priceToBook"),
        "pegRatio": info.get("pegRatio"),
        "beta": info.get("beta"),
        "dividendRate": info.get("dividendRate"),
        "dividendYield": info.get("dividendYield"),
        "exDividendDate": ex_div,
        "earningsDate": earnings,
        "totalRevenue": info.get("totalRevenue"),
        "grossProfits": info.get("grossProfits"),
        "ebitda": info.get("ebitda"),
        "totalCash": info.get("totalCash"),
        "totalDebt": info.get("totalDebt"),
        "data_evolution": data_evolution,
    }

    logger.info(f"[get_stock_data] Retornando dados de {symbol}")
    return result
