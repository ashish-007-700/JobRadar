-- JobRadar — Section 4: add telegram_channel_id to channels
-- Run this if your Supabase project already has the channels table from
-- supabase/schema.sql without this column. A fresh project can just run the
-- current supabase/schema.sql instead.

alter table channels add column if not exists telegram_channel_id bigint;
