"""
Raw MySQL connection management via PyMySQL - no ORM.

There is no separate "SQLAlchemy database" - every value the app reads or
writes lives in real MySQL tables (see schema.sql). This file is only the
thin connection layer: it opens a PyMySQL connection per request and hands
it to the repository layer (app/repositories/notification_repository.py),
which is the only place that writes SQL.
"""
import pymysql
import pymysql.cursors

from app.config import get_settings

settings = get_settings()


def _connect():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


class Database:
    """Thin wrapper around one PyMySQL connection for the lifetime of a
    single request. Every query anywhere in the app goes through
    `execute()` - there is no ORM generating SQL behind the scenes."""

    def __init__(self, connection):
        self._conn = connection

    def execute(self, sql: str, params=None):
        cursor = self._conn.cursor()
        cursor.execute(sql, params or ())
        return cursor

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def get_db():
    """FastAPI dependency: one connection per request, rolled back on
    error, always closed afterward."""
    connection = _connect()
    db = Database(connection)
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create the two tables if they don't exist yet. Same DDL as
    schema.sql, run directly through PyMySQL - kept in sync by hand since
    there is no ORM to generate it."""
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id          VARCHAR(36)  NOT NULL PRIMARY KEY,
                    title       VARCHAR(255) NOT NULL,
                    message     TEXT         NOT NULL,
                    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_deliveries (
                    id                   VARCHAR(36)  NOT NULL PRIMARY KEY,
                    notification_id      VARCHAR(36)  NOT NULL,
                    channel              VARCHAR(20)  NOT NULL,
                    destination          VARCHAR(255) NOT NULL,
                    status               VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
                    provider             VARCHAR(50)  NOT NULL,
                    provider_message_id  VARCHAR(255) NULL,
                    retry_count          INT          NOT NULL DEFAULT 0,
                    error_message        TEXT         NULL,
                    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_notification_deliveries_notification
                        FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
                    INDEX idx_notification_deliveries_notification_id (notification_id),
                    INDEX idx_notification_deliveries_channel (channel),
                    INDEX idx_notification_deliveries_status (status),
                    INDEX idx_notification_deliveries_provider_message_id (provider_message_id)
                ) ENGINE=InnoDB
                """
            )
        connection.commit()
    finally:
        connection.close()
