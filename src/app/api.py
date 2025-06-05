from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from app.services.stock_data import get_stock_data
from app.config.logger import setup_logger

logger = setup_logger("logs/api.log")
router = APIRouter()

@router.get("/stock-data")
def stock_data_endpoint(
    symbol: str = Query(...),
    start_date: str = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("1d"),
    period: Optional[str] = Query(None),
    auto_adjust: bool = Query(True),
):
    try:
        end_date_str = end_date or datetime.today().strftime('%Y-%m-%d')
        return get_stock_data(symbol, start_date, end_date_str, interval, period, auto_adjust)
    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"error": str(e)}
