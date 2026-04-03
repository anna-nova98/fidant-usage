-- Migration: init_usage_schema
-- Creates the three core tables for the Fidant usage analytics system.

-- Users table: stores account info and subscription tier
CREATE TABLE "users" (
    "id"         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email"      TEXT NOT NULL,
    "name"       TEXT,
    "plan_tier"  TEXT NOT NULL DEFAULT 'starter',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- Daily usage events: raw turn lifecycle events (reserve -> commit)
CREATE TABLE "daily_usage_events" (
    "id"           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id"      INTEGER NOT NULL,
    "date_key"     TEXT NOT NULL,
    "request_id"   TEXT NOT NULL,
    "status"       TEXT NOT NULL,
    "reserved_at"  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "committed_at" DATETIME,
    "created_at"   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Daily usage cache: precomputed per-user per-day aggregates
-- Avoids scanning raw events on every stats request.
-- Invalidated after CACHE_STALE_MINUTES (see usage.py).
CREATE TABLE "daily_usage_cache" (
    "id"              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id"         INTEGER NOT NULL,
    "date_key"        TEXT NOT NULL,
    "committed_count" INTEGER NOT NULL,
    "reserved_count"  INTEGER NOT NULL,
    "computed_at"     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX "daily_usage_cache_user_id_date_key_key"
    ON "daily_usage_cache"("user_id", "date_key");
