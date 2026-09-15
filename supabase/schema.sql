-- JobRadar — Section 2: Supabase schema
-- Run this once in the Supabase SQL editor (or via `supabase db push`) for a new project.

create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- channels ------------------------------------------------------------

create table if not exists channels (
  id uuid primary key default gen_random_uuid(),
  channel_username text not null unique,
  channel_name text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger channels_set_updated_at
before update on channels
for each row execute function set_updated_at();

-- jobs ------------------------------------------------------------

create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  company text,
  title text,
  location text,
  experience text,
  qualification text,
  batch text,
  salary text,
  skills text[],
  employment_type text,
  telegram_message_id bigint,
  telegram_channel text,
  telegram_message_url text,
  original_apply_url text,
  final_apply_url text,
  posted_at timestamptz,
  discovered_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  content_hash text
);

create trigger jobs_set_updated_at
before update on jobs
for each row execute function set_updated_at();

create index if not exists jobs_posted_at_idx on jobs (posted_at);
create index if not exists jobs_telegram_channel_idx on jobs (telegram_channel);

-- fetch_runs ------------------------------------------------------------

create table if not exists fetch_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  requested_date date not null,
  status text not null default 'running',
  channels_processed integer not null default 0,
  messages_processed integer not null default 0,
  jobs_detected integer not null default 0,
  jobs_saved integer not null default 0,
  errors jsonb not null default '[]'::jsonb
);
