-- MySQL schema for the Notification Management Application.
-- Mirrors app/models/notification.py exactly. Run this directly against a
-- MySQL server for a production-style setup, or let the app create these
-- same tables for you automatically (see app/db.py: init_db) for local dev.

CREATE DATABASE IF NOT EXISTS notification_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE notification_db;

CREATE TABLE IF NOT EXISTS notifications (
  id          VARCHAR(36)  NOT NULL PRIMARY KEY,
  title       VARCHAR(255) NOT NULL,
  message     TEXT         NOT NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notification_deliveries (
  id                   VARCHAR(36)  NOT NULL PRIMARY KEY,
  notification_id      VARCHAR(36)  NOT NULL,
  channel              VARCHAR(20)  NOT NULL,               -- TEAMS / EMAIL / SLACK
  destination          VARCHAR(255) NOT NULL,
  status               VARCHAR(20)  NOT NULL DEFAULT 'PENDING', -- PENDING/SENT/DELIVERED/FAILED
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
) ENGINE=InnoDB;
