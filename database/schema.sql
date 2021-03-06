CREATE SCHEMA fotc;

SET search_path = fotc;

---
--- Stores user data and configuration
---
CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY NOT NULL,
  last_active TIMESTAMP WITHOUT TIME ZONE,
  timezone TEXT
);

---
--- Placeholder for group-specific data
---
CREATE TABLE IF NOT EXISTS groups (
    id BIGINT PRIMARY KEY
);

---
--- Stores information about which users are known to be member of groups
---
CREATE TABLE IF NOT EXISTS group_users (
  id SERIAL PRIMARY KEY NOT NULL,
  user_id INT REFERENCES users NOT NULL,
  group_id INT REFERENCES groups NOT NULL
);

---
--- Migrate user_id and group_id to BIGINT, mistakes!
---
ALTER TABLE group_users ALTER COLUMN user_id TYPE bigint;
ALTER TABLE group_users ALTER COLUMN group_id TYPE bigint;

---
--- Stores reminders that are linked to specific messages that will be forwarded to a given
--- chat when the scheduled time arrives.
---
CREATE TABLE IF NOT EXISTS reminders (
  id SERIAL PRIMARY KEY NOT NULL,
  group_user_id BIGINT REFERENCES group_users (id) NOT NULL,
  message_ref TEXT,
  scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
  sent_on TIMESTAMP WITHOUT TIME ZONE
);

---
--- Stores references to messages associated as a quote of a user in a group
---
CREATE TABLE IF NOT EXISTS group_user_quotes (
    id SERIAL PRIMARY KEY NOT NULL,
    group_user_id BIGINT REFERENCES group_users (id) NOT NULL,
    message_ref TEXT NOT NULL,
    last_sent_on TIMESTAMP WITHOUT TIME ZONE
);

ALTER TABLE group_user_quotes ADD UNIQUE (group_user_id, message_ref);