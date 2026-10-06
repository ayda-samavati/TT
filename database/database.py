from abc import ABC, abstractmethod


class Database(ABC):
    """Common database connection behavior."""

    def __init__(self, config, logger, config_key, name):
        self.config = config
        self.logger = logger
        self.database_config = config[config_key]
        self.name = name
        self.connection = None

    @abstractmethod
    def connect(self):
        """Create the database connection."""

    @abstractmethod
    def get_columns(self):
        """Return table columns in their database order."""

    @abstractmethod
    def get_streaming_cursor(self, columns):
        """Return a cursor that reads the selected columns."""

    @abstractmethod
    def truncate_table(self):
        """Remove all rows from the configured table."""

    @abstractmethod
    def insert_batch(self, columns, rows):
        """Insert a batch of rows into the configured table."""

    @abstractmethod
    def get_row_count(self):
        """Return the configured table row count."""

    def commit(self):
        if self.connection:
            self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("%s connection closed.", self.name)
