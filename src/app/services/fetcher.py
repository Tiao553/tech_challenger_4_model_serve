import os
import json
import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from app.config.logger import setup_logger
# from app.services.s3_utils import upload_file_to_s3, download_file_from_s3

logger = setup_logger("logs/fetcher.log")


def read_checkpoint_json(checkpoint_path: str) -> Optional[Dict[str, datetime]]:
    """
    Lê do arquivo de checkpoint o último timestamp processado.
    Retorna um dicionário com os timestamps ou None se o arquivo não existir ou estiver vazio/corrompido.
    """

        # Checa se o arquivo existe antes de abrir
    if not os.path.exists(checkpoint_path):
        return None
    
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        ts_first = payload.get("start_timestamp")
        ts_last = payload.get("last_timestamp")

        if not ts_first or not ts_last:
            raise KeyError("Chave first_timestamp ou last_timestamp ausente")
        return {"start_timestamp": datetime.strptime(ts_first, "%Y-%m-%d %H:%M:%S"),
                "last_timestamp":  datetime.strptime(ts_last,  "%Y-%m-%d %H:%M:%S")
            }
    
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Arquivo corrompido ou formato errado: logar e retornar None
        logger.warning(f"Aviso: não foi possível ler checkpoint JSON em '{checkpoint_path}': {e}")
        return None

def write_checkpoint_json(checkpoint_path: str, new_first: datetime, new_last: datetime) -> None:
    """
    Grava (ou sobrescreve) o arquivo de checkpoint com o timestamp.
    """
    logger.info(f'Gravando checkpoint com last_timestamp = {new_last} e start_timestamp = {new_first}')


    payload = {
        "start_timestamp": new_first.strftime("%Y-%m-%d %H:%M:%S"),
        "last_timestamp":  new_last.strftime("%Y-%m-%d %H:%M:%S"),
    }

    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
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

    timestamp_exec = datetime.now().isoformat()
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
    evo = pd.DataFrame(data["data_evolution"])
    evo["datetime"] = pd.to_datetime(evo["datetime"], format="%Y-%m-%d %H:%M:%S")

    menor_ts_lote = evo["datetime"].min()
    maior_ts_lote= evo["datetime"].max()

    # Verifica se o arquivo já existe
    if not os.path.exists(evo_path):

        os.makedirs(os.path.dirname(evo_path), exist_ok=True)
        evo.to_csv(evo_path, index=False)

        write_checkpoint_json(checkpoint_path,
                              new_first=menor_ts_lote,
                              new_last=maior_ts_lote)
        
        logger.info(f"• Criando {symbol}_evolution com {len(evo)} linhas.")
        logger.info(f"  -> Checkpoint inicial: first={menor_ts_lote}, last={maior_ts_lote}")


        logger.info(f"• Criando {symbol}_metadata com metadados iniciais.")
        # Grava metadados (primeiro lote)
        info = {k: data[k] for k in data if k != "data_evolution"}
        info_df = pd.DataFrame([{**{"timestamp": timestamp_exec}, **info}])
        write_header = not os.path.isfile(meta_path)
        info_df.to_csv(meta_path, mode="a", header=write_header, index=False)

        return
    else:
        chk = read_checkpoint_json(checkpoint_path)
        if chk:
            saved_first = chk["start_timestamp"]
            saved_last  = chk["last_timestamp"]

        else:
            # Se não conseguir ler, forçamos a considerar CSV existente:
            # 1) Lê a primeira linha de dados (logo após o cabeçalho)
            with open(evo_path, "r", encoding="utf-8") as f:
                header = f.readline()               # descarta linha de cabeçalho
                first_data = f.readline().strip()   # primeira linha de dados
                if not first_data:
                    raise ValueError(f"O CSV '{evo_path}' está vazio ou sem linhas de dados.")
                # Supõe que o CSV está separado por vírgula e que 'datetime' é a primeira coluna
                ts_first_str = first_data.split(",")[0]
                saved_first = datetime.strptime(ts_first_str, "%Y-%m-%d %H:%M:%S")

            with open(evo_path, "rb") as f:
                # Vai pular para o final do arquivo menos 1024 bytes
                # (suficiente para a maioria das linhas; aumente se suas linhas forem muito longas)
                try:
                    f.seek(-1024, os.SEEK_END)
                except OSError:
                    # Se o arquivo tiver menos de 1024 bytes, volta pro início
                    f.seek(0, os.SEEK_SET)

                # Lê tudo a partir desse ponto e pega a última linha não vazia
                linhas = f.read().decode("utf-8", errors="ignore").splitlines()
                # Remove linhas vazias do final
                while linhas and not linhas[-1].strip():
                    linhas.pop()
                if not linhas:
                    raise ValueError(f"O CSV '{evo_path}' parece não ter linhas legíveis.")
                last_data = linhas[-1]
                ts_last_str = last_data.split(",")[0]
                saved_last = datetime.strptime(ts_last_str, "%Y-%m-%d %H:%M:%S")


    #Filtra apenas as linhas novas (timestamp > saved_last)
    novos = evo[evo["datetime"] > saved_last].copy()



    if not novos.empty:
        novos = novos.sort_values("datetime")
        cols_para_csv = [c for c in novos.columns if c != "datetime"]

        with open(evo_path, "a", newline="", encoding="utf-8") as f:
            novos[cols_para_csv].to_csv(f, header=False, index=False)


        novo_maior_ts = novos["datetime"].max()
        novo_menor_ts = novos["datetime"].min()

        # Se o novo lote traz dados anteriores ao saved_first, atualiza first
        updated_first = min(saved_first, novo_menor_ts)

        # Se o novo lote traz dados posteriores ao saved_last, atualiza last
        updated_last = max(saved_last, novo_maior_ts)

        write_checkpoint_json(checkpoint_path,
                                  new_first=updated_first,
                                  new_last=updated_last)

        logger.info(
                f"• Adicionadas {len(novos)} linhas em '{symbol}_evolution.csv'.\n"
                f"  -> First salvo: {saved_first}  |  Last salvo: {saved_last}\n"
                f"  -> Menor do lote novo: {novo_menor_ts}  |  Maior do lote novo: {novo_maior_ts}\n"
                f"  -> Checkpoint atualizado: first={updated_first}, last={updated_last}"
            )
    else:
        logger.info("• Nenhuma linha nova para adicionar (já processado).")


    # Salva metadados
    info = {k: data[k] for k in data if k != "data_evolution"}
    info_df = pd.DataFrame([{**{"timestamp": timestamp_exec}, **info}])
    write_header = not os.path.isfile(meta_path)
    info_df.to_csv(meta_path, mode="a", header=write_header, index=False)
