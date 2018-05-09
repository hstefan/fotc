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
