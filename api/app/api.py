from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from app.services.stock_data import get_stock_data
from app.services.fetcher import fetch_and_save_s3
from app.services.preditict import pipe_to_predict
from app.config.logger import setup_logger

logger = setup_logger("stock_data_api")
router = APIRouter()

@router.get("/")
def root():
    return {"message": "API ativa"}
    
@router.get("/stock-data-prediction")
def stock_data_endpoint(
    symbol: str = Query(...),
    start_date: str = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("1m"),
    period: Optional[str] = Query(None),
    auto_adjust: bool = Query(True),
):
    try:
        end_date_str = end_date or datetime.today().strftime('%Y-%m-%d')
        try:
            msg = fetch_and_save_s3(symbol, start_date, end_date_str, interval, period, auto_adjust)
            if 200 in msg:
                return pipe_to_predict(symbol, start_date, end_date_str)
        except  Exception as e:
            logger.error(f"Erro ao buscar dados do Yahoo Finance: {e}")
            raise {"error": str(e)}
    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"error": str(e)}