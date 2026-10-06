import logging
import os


class Logger:

    @staticmethod
    def get_logger(log_file: str):

        log_directory = os.path.dirname(log_file)

        if log_directory:
            os.makedirs(log_directory, exist_ok=True)

        logger = logging.getLogger("postgres_oracle_backup")

        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()

        console_handler.setFormatter(formatter)

        # File handler
        file_handler = logging.FileHandler(
            log_file,
            encoding="utf-8"
        )

        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger