# run_fetcher.py
from app.services.fetcher import fetch_and_save

if __name__ == "__main__":
    # Exemplo: roda sempre com esses parâmetros
    # Você pode parametrizar via argparse ou variáveis de ambiente, se quiser.
    PATH = "data"
    SYMBOL = "TSLA"
    START = None
    END   = None
    INTERVAL = "1m"
    PERIOD   = "1d"
    AUTO_ADJUST = True

    fetch_and_save(
        path=PATH,
        symbol=SYMBOL,
        start_date=START,
        end_date=END,
        interval=INTERVAL,
        period=PERIOD,
        auto_adjust=AUTO_ADJUST,
        api_url="http://127.0.0.1:8000/stock-data"
    )
