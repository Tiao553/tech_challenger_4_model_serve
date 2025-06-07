import json
import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Tuple
from app.config.logger import setup_logger
from app.services.stock_data import get_stock_data


from app.services.s3_utils import (
    read_json_from_s3,
    write_json_to_s3,
    read_csv_from_s3,
    write_csv_to_s3,
)

logger = setup_logger("fetcher")

# Exemplo de bucket e prefixo (pode vir de config/variável ambiente)
BUCKET_NAME = "tech-challanger-4-prd-raw-zone-593793061865"


def read_checkpoint_s3(bucket: str, key: str) -> Optional[Dict[str, datetime]]:

    """
    Lê checkpoint JSON do S3.
    Retorna dicionário com timestamps ou None.
    """
    payload = read_json_from_s3(bucket, key)
    if not payload:
        return None
    try:
        ts_first = payload.get("start_timestamp")
        ts_last = payload.get("last_timestamp")
        if not ts_first or not ts_last:
            raise KeyError("Chave start_timestamp ou last_timestamp ausente")
        return {
            "start_timestamp": datetime.strptime(ts_first, "%Y-%m-%d %H:%M:%S"),
            "last_timestamp": datetime.strptime(ts_last, "%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        logger.warning(f"Erro ao ler checkpoint JSON do S3 em {key}: {e}")
        return None

def write_checkpoint_s3(bucket: str, key: str, new_first: datetime, new_last: datetime) -> None:
    """
    Grava checkpoint JSON no S3.
    """
    logger.info(f'Gravando checkpoint no S3 com last_timestamp = {new_last} e start_timestamp = {new_first}')
    payload = {
        "start_timestamp": new_first.strftime("%Y-%m-%d %H:%M:%S"),
        "last_timestamp": new_last.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_json_to_s3(bucket, key, payload)

def fetch_and_save_s3(symbol: str,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      interval: str = "1m",
                      period: Optional[str] = "1d",
                      auto_adjust: bool = True) -> Tuple[str, int]:
    try:
        logger.info(f"[fetch_and_save_s3] Símbolo={symbol}, de {start_date} até {end_date}, intervalo:({interval}), período:({period}), auto_adjust:({auto_adjust})")

        timestamp_exec = datetime.now().isoformat()

        evo_key = f"fetch/{symbol}_evolution.csv"
        meta_key = f"fetch/{symbol}_metadata.csv"
        checkpoint_key = f"checkpoint/{symbol}_checkpoint.json"

        data = get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            period=period,
            auto_adjust=auto_adjust,
        )

        evo = pd.DataFrame(data["data_evolution"])
        evo["datetime"] = pd.to_datetime(evo["datetime"], format="%Y-%m-%d %H:%M:%S")

        menor_ts_lote = evo["datetime"].min()
        maior_ts_lote = evo["datetime"].max()

        try:
            evo_existente = read_csv_from_s3(BUCKET_NAME, evo_key)
            arquivo_existe = True
        except Exception as e:
            logger.warning(f"[S3 Read] Arquivo {evo_key} não encontrado ou erro ao ler: {str(e)}")
            arquivo_existe = False

        if not arquivo_existe:
            write_csv_to_s3(BUCKET_NAME, evo_key, evo)
            write_checkpoint_s3(BUCKET_NAME, checkpoint_key, menor_ts_lote, maior_ts_lote)

            logger.info(f"• Criando {symbol}_evolution.csv com {len(evo)} linhas.")
            logger.info(f"  -> Checkpoint inicial: first={menor_ts_lote}, last={maior_ts_lote}")

            logger.info(f"• Criando {symbol}_metadata.csv com metadados iniciais.")
            info = {k: data[k] for k in data if k != "data_evolution"}
            info_df = pd.DataFrame([{**{"timestamp": timestamp_exec}, **info}])
            write_csv_to_s3(BUCKET_NAME, meta_key, info_df)

            return f"Dados iniciais do símbolo '{symbol}' gravados com sucesso.", 200

        # Checkpoint existente
        chk = read_checkpoint_s3(BUCKET_NAME, checkpoint_key)
        if chk:
            saved_first = chk["start_timestamp"]
            saved_last = chk["last_timestamp"]
        else:
            saved_first = pd.to_datetime(evo_existente["datetime"]).min()
            saved_last = pd.to_datetime(evo_existente["datetime"]).max()

        novos = evo[evo["datetime"] > saved_last].copy()

        if not novos.empty:
            novos = novos.sort_values("datetime")
            df_atualizado = pd.concat([evo_existente, novos], ignore_index=True)
            write_csv_to_s3(BUCKET_NAME, evo_key, df_atualizado)

            novo_maior_ts = novos["datetime"].max()
            novo_menor_ts = novos["datetime"].min()

            updated_first = min(saved_first, novo_menor_ts)
            updated_last = max(saved_last, novo_maior_ts)

            write_checkpoint_s3(BUCKET_NAME, checkpoint_key, updated_first, updated_last)

            logger.info(
                f"• Adicionadas {len(novos)} linhas em '{symbol}_evolution.csv'.\n"
                f"  -> First salvo: {saved_first}  |  Last salvo: {saved_last}\n"
                f"  -> Menor do lote novo: {novo_menor_ts}  |  Maior do lote novo: {novo_maior_ts}\n"
                f"  -> Checkpoint atualizado: first={updated_first}, last={updated_last}"
            )
        else:
            logger.info("• Nenhuma linha nova para adicionar (já processado).")

        try:
            meta_existente = read_csv_from_s3(BUCKET_NAME, meta_key)
            info = {k: data[k] for k in data if k != "data_evolution"}
            info_df = pd.DataFrame([{**{"timestamp": timestamp_exec}, **info}])
            meta_atualizado = pd.concat([meta_existente, info_df], ignore_index=True)
            write_csv_to_s3(BUCKET_NAME, meta_key, meta_atualizado)
        except Exception as e:
            logger.warning(f"[S3 Meta Write] Criando novo metadata para {symbol}: {str(e)}")
            info = {k: data[k] for k in data if k != "data_evolution"}
            info_df = pd.DataFrame([{**{"timestamp": timestamp_exec}, **info}])
            write_csv_to_s3(BUCKET_NAME, meta_key, info_df)

        return f"Dados de '{symbol}' atualizados com sucesso.", 200

    except Exception as e:
        logger.error(f"[fetch_and_save_s3] Falha no processamento do símbolo '{symbol}': {str(e)}", exc_info=True)
        return f"Erro interno ao processar o símbolo '{symbol}'.", 500





