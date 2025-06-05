import os
import json
import requests
import pandas as pd
from datetime import datetime
from typing import Optional
from app.config.logger import setup_logger

logger = setup_logger("logs/fetcher.log")


def read_last_checkpoint(checkpoint_path: str) -> Optional[datetime]:
    """
    Lê do arquivo de checkpoint o último timestamp processado.
    Retorna None se o arquivo não existir ou estiver vazio/corrompido.
    """
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        ts_str = payload.get("last_timestamp")
        if ts_str:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        logger.warning(f"Erro ao ler o checkpoint em '{checkpoint_path}'.")
        return None
    return None

def write_checkpoint(checkpoint_path: str, timestamp) -> None:
    """
    Grava (ou sobrescreve) o arquivo de checkpoint com o timestamp.
    """
    logger.info(f'write timestamp: {datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S")}')
    last_timestamp = datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S")
    payload = {
        "last_timestamp": last_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def fetch_and_save(path:str,
                   symbol: str,
                   api_url: str,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   interval: str = "1m",
                   period: Optional[str] = "1d",
                   auto_adjust: bool = True,):

    logger.info(f"[fetch_and_save] Símbolo={symbol}, de {start_date} até {end_date}, intervalo:({interval}), período:({period}), auto_adjust:({auto_adjust})")

    timestamp = datetime.now().isoformat()
    evo_path = f"{path}/{symbol}_evolution.csv"
    meta_path = f"{path}/{symbol}_metadata.csv"
    checkpoint_path = f"{path}/{symbol}_checkpoint.json"

    params = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "interval": interval,
        "period": period,
        "auto_adjust": str(auto_adjust),
    }
    resp = requests.get(api_url, params=params)
    resp.raise_for_status()
    data = resp.json()

    #salvar dados históricos
    #impedir que o ultimo dado entre de forma repetida
    evo = pd.DataFrame(data["data_evolution"])
    if not os.path.exists(evo_path):
        evo.to_csv(evo_path, index=False)
        maior_ts = evo["datetime"].max()
        write_checkpoint(checkpoint_path, maior_ts)
        logger.info(f"• Criando {symbol}_evolution.csv com {len(evo)} linhas.")
    else:
        last_ts = read_last_checkpoint(checkpoint_path)
        if last_ts is not None:
            evo["datetime"] = pd.to_datetime(evo["datetime"], format="%Y-%m-%d %H:%M:%S")
            novos = evo[evo["datetime"] > last_ts].copy()
        else:
            # Se não conseguiu ler JSON (inexistente ou inválido), processa tudo como “novo”
            novos = evo.copy()

    if not novos.empty:
        novos = novos.sort_values("datetime")
        cols_para_csv = [c for c in novos.columns if c != "datetime"]

        with open(evo_path, "a", newline="", encoding="utf-8") as f:
            novos[cols_para_csv].to_csv(f, header=False, index=False)

        novo_maior_ts = novos["datetime"].max()
        write_checkpoint(checkpoint_path, novo_maior_ts)

        logger.info(
            f"• Adicionadas {len(novos)} linhas novas a '{symbol}_evolution.csv'. "
            f"Checkpoint JSON atualizado para {novo_maior_ts}."
        )
    else:
        logger.info("• Nenhuma linha nova para adicionar (já processado).")


    # Salva metadados
    info = {k: data[k] for k in data if k != "data_evolution"}
    info_df = pd.DataFrame([{**{"timestamp": timestamp}, **info}])
    write_header = not os.path.isfile(meta_path)
    info_df.to_csv(meta_path, mode="a", header=write_header, index=False)
