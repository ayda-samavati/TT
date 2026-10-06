import psycopg2
from psycopg2 import sql

from database.database import Database


class PostgresDatabase(Database):
    def __init__(self, config, logger):
        super().__init__(config, logger, "postgres", "PostgreSQL")

    def connect(self):
        self.logger.info("Connecting to PostgreSQL...")

        self.connection = psycopg2.connect(
            host=self.database_config["host"],
            port=self.database_config["port"],
            dbname=self.database_config["database"],
            user=self.database_config["username"],
            password=self.database_config["password"]
        )

        self.logger.info("PostgreSQL connection established.")

    def get_columns(self):
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            ORDER BY ordinal_position
        """

        cursor = self.connection.cursor()

        try:
            cursor.execute(
                query,
                (
                    self.database_config["schema"],
                    self.database_config["table"]
                )
            )

            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_streaming_cursor(self, columns):
        query = sql.SQL("SELECT {} FROM {}.{}").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.Identifier(self.database_config["schema"]),
            sql.Identifier(self.database_config["table"])
        )
        

        where_condition = self.database_config["where_condition"]
        if where_condition:
            query += sql.SQL(where_condition)

        cursor = self.connection.cursor(
            name="postgres_backup_cursor"
        )
        self.logger.info(
        "Executing query: %s",
        query.as_string(self.connection))

        cursor.itersize = self.config["backup"]["batch_size"]
        cursor.execute(query)

        return cursor

    def truncate_table(self):
        query = sql.SQL("TRUNCATE TABLE {}.{}").format(
            sql.Identifier(self.database_config["schema"]),
            sql.Identifier(self.database_config["table"])
        )

        cursor = self.connection.cursor()

        try:
            self.logger.info("Truncating PostgreSQL target table...")
            cursor.execute(query)
        finally:
            cursor.close()

    def insert_batch(self, columns, rows):
        query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
            sql.Identifier(self.database_config["schema"]),
            sql.Identifier(self.database_config["table"]),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(
                sql.Placeholder()
                for _ in columns
            )
        )

        cursor = self.connection.cursor()

        try:
            cursor.executemany(query, rows)
        finally:
            cursor.close()

    def get_row_count(self):
        query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(self.database_config["schema"]),
            sql.Identifier(self.database_config["table"])
        )

        cursor = self.connection.cursor()

        try:
            cursor.execute(query)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
