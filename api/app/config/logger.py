import logging

def setup_logger(name: str) -> logging.Logger:
    """
    Configura um logger com o nome especificado.
    Se o logger já existir, retorna o logger existente.
    Se não existir, cria um novo logger com um handler padrão que envia logs para stdout.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()  # envia para stdout (console)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger("s3_utils")
