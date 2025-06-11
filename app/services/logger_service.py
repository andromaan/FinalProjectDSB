import logging
from colorlog import ColoredFormatter

# Налаштування форматтера з табуляцією та кольорами
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)s%(reset)s:     %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    reset=True,  # Повернення до стандартного кольору (білий) для повідомлення
    style="%",
)

# Налаштування обробника
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Налаштування логера
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False