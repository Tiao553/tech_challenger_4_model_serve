import boto3
import json
import io
import pandas as pd
from app.config.logger import setup_logger  # Importa a função setup_logger do arquivo config

logger = setup_logger("s3_utils")

s3 = boto3.client("s3")

def read_json_from_s3(bucket: str, key: str) -> dict:
    logger.info(f"Attempting to read JSON from s3://{bucket}/{key}")
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        logger.info(f"Successfully read JSON from s3://{bucket}/{key}")
        return data
    except s3.exceptions.NoSuchKey:
        logger.warning(f"Object not found: s3://{bucket}/{key}")
        return None
    except Exception as e:
        logger.error(f"Error reading JSON from s3://{bucket}/{key}: {e}", exc_info=True)
        raise

def write_json_to_s3(bucket: str, key: str, data: dict) -> None:
    logger.info(f"Writing JSON to s3://{bucket}/{key}")
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        )
        logger.info(f"Successfully wrote JSON to s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"Error writing JSON to s3://{bucket}/{key}: {e}", exc_info=True)
        raise

def read_csv_from_s3(bucket: str, key: str) -> pd.DataFrame:
    logger.info(f"Attempting to read CSV from s3://{bucket}/{key}")
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(io.BytesIO(obj["Body"].read()))
        logger.info(f"Successfully read CSV from s3://{bucket}/{key} (rows: {len(df)})")
        return df
    except Exception as e:
        logger.error(f"Error reading CSV from s3://{bucket}/{key}: {e}", exc_info=True)
        raise

def write_csv_to_s3(bucket: str, key: str, df: pd.DataFrame, mode: str = "w") -> None:
    logger.info(f"Writing CSV to s3://{bucket}/{key} (mode={mode})")
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue().encode("utf-8"))
        logger.info(f"Successfully wrote CSV to s3://{bucket}/{key} (rows: {len(df)})")
    except Exception as e:
        logger.error(f"Error writing CSV to s3://{bucket}/{key}: {e}", exc_info=True)
        raise
