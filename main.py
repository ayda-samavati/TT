import sys
import yaml

from logger import Logger
from database.oracle_database import OracleDatabase
from database.postgres_database import PostgresDatabase


CONFIG_FILE = "config.yml"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_transfer_databases(config, logger):
    postgres_database = PostgresDatabase(config, logger)
    oracle_database = OracleDatabase(config, logger)
    direction = config["backup"].get("direction","postgres_to_oracle").lower()

    if direction == "postgres_to_oracle":
        return postgres_database, oracle_database

    if direction == "oracle_to_postgres":
        return oracle_database, postgres_database

    raise ValueError(
        "backup.direction must be 'postgres_to_oracle' "
        "or 'oracle_to_postgres'.")


def run_backup():
    config = load_config()
    logger = Logger.get_logger(config["backup"].get("log_file", "logs/backup.log"))
    source_database, target_database = get_transfer_databases(config, logger)

    try:
        # ====================================================
        # Connect to databases
        # ====================================================
        source_database.connect()
        target_database.connect()

        # ====================================================
        # Match source and target columns
        # ====================================================

        logger.info("Reading source and target table structures...")
        source_columns = source_database.get_columns()

        if not source_columns:
            raise RuntimeError("No columns found in the source table.")

        available_target_columns = {
            column.casefold(): column
            for column in target_database.get_columns()
        }

        if not available_target_columns:
            raise RuntimeError("No columns found in the target table.")

        missing_columns = [
            column
            for column in source_columns
            if column.casefold() not in available_target_columns
        ]

        if missing_columns:
            raise RuntimeError(
                "Columns missing from target table: "
                + ", ".join(missing_columns)
            )

        target_columns = [
            available_target_columns[column.casefold()]
            for column in source_columns
        ]

        # ====================================================
        # Prepare target and source cursor
        # ====================================================

        target_database.truncate_table()
        target_database.commit()

        logger.info(
            "Starting transfer from %s to %s...",
            source_database.name,
            target_database.name
        )
        source_cursor = source_database.get_streaming_cursor(
            source_columns
        )
        batch_size = config["backup"]["batch_size"]
        total_rows = 0
        batch_number = 0

        # ====================================================
        # Process batches
        # ====================================================

        while True:

            rows = source_cursor.fetchmany(batch_size)

            if not rows:
                break

            batch_number += 1
            target_database.insert_batch(target_columns, rows)
            target_database.commit()
            total_rows += len(rows)

            logger.info(
                "Batch %d completed | "
                "Batch rows: %d | "
                "Total rows: %d",
                batch_number,
                len(rows),
                total_rows
            )

        source_cursor.close()

        # ====================================================
        # Validation
        # ====================================================

        logger.info("Validating backup...")

        target_count = target_database.get_row_count()
        
        logger.info("Source rows copied: %d", total_rows)
        logger.info("Target rows: %d", target_count)

        if total_rows != target_count:

            raise RuntimeError(
                f"Row count mismatch! "
                f"Source={total_rows}, "
                f"Target={target_count}"
            )

        # ====================================================
        # SUCCESS
        # ====================================================

        logger.info(
            "========================================"
        )

        logger.info(
            "BACKUP COMPLETED SUCCESSFULLY"
        )

        logger.info(
            "Total rows: %d",
            total_rows
        )

        logger.info(
            "========================================"
        )

    except Exception as error:

        logger.exception(
            "BACKUP FAILED: %s",
            error
        )

        target_database.rollback()

        sys.exit(1)

    finally:

        source_database.close()
        target_database.close()


if __name__ == "__main__":
    run_backup()