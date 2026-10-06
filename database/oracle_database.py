import re

import oracledb

from database.database import Database


class OracleDatabase(Database):
    def __init__(self, config, logger):
        super().__init__(config, logger, "oracle", "Oracle")

    @staticmethod
    def _identifier(value):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_$#]*", value):
            raise ValueError(f"Invalid Oracle identifier: {value!r}")
        return value

    @staticmethod
    def _quoted_identifier(value):
        escaped_value = value.replace('"', '""')
        return f'"{escaped_value}"'

    def _qualified_table(self):
        schema = self._identifier(self.database_config["schema"])
        table = self._identifier(self.database_config["table"])
        return f"{schema}.{table}"

    def connect(self):
        self.logger.info("Connecting to Oracle...")

        oracledb.defaults.fetch_lobs = False
        oracledb.init_oracle_client(lib_dir=self.database_config["client_lib_dir"])

        self.connection = oracledb.connect(
            user=self.database_config["username"],
            password=self.database_config["password"],
            dsn=self.database_config["dsn"])

        self.logger.info("Oracle connection established.")

    def get_columns(self):
        query = """
            SELECT column_name
            FROM all_tab_columns
            WHERE owner = :owner
              AND table_name = :table_name
            ORDER BY column_id
        """

        cursor = self.connection.cursor()

        try:
            cursor.execute(
                query,
                owner=self.database_config["schema"].upper(),
                table_name=self.database_config["table"].upper()
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_streaming_cursor(self, columns):
        selected_columns = ", ".join(
            self._quoted_identifier(column)
            for column in columns
        )
        query = (
            f"SELECT {selected_columns} "
            f"FROM {self._qualified_table()}"
        )
        where_condition = self.database_config["where_condition"]
        if where_condition:
            query += f"{where_condition}"

        cursor = self.connection.cursor()
        cursor.arraysize = self.config["backup"]["batch_size"]
        cursor.execute(query)

        return cursor

    def truncate_table(self):
        query = f"TRUNCATE TABLE {self._qualified_table()}"

        cursor = self.connection.cursor()

        try:
            self.logger.info("Truncating Oracle target table...")
            cursor.execute(query)
        finally:
            cursor.close()

    def insert_batch(self, columns, rows):
        oracle_columns = ", ".join(
            self._quoted_identifier(column)
            for column in columns
        )
        bind_variables = ", ".join(
            f":{index + 1}"
            for index in range(len(columns))
        )

        query = (
            f"INSERT INTO {self._qualified_table()} "
            f"({oracle_columns}) VALUES ({bind_variables})"
        )

        cursor = self.connection.cursor()

        try:
            cursor.executemany(query, rows)
        finally:
            cursor.close()

    def get_row_count(self):
        query = f"SELECT COUNT(*) FROM {self._qualified_table()}"
        cursor = self.connection.cursor()

        try:
            cursor.execute(query)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
