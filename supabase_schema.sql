-- Guardian Database Schema
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor → New Query)

-- 1. Users table
create table if not exists users (
  user_id text primary key,
  created_at timestamptz default now()
);

-- 2. Analysis runs
create table if not exists analysis_runs (
  run_id text primary key,
  user_id text references users(user_id),
  created_at timestamptz default now(),
  health_score integer,
  total_monthly_at_risk float,
  executive_summary text,
  status text default 'pending'
);

-- 3. Findings
create table if not exists findings (
  id uuid default gen_random_uuid() primary key,
  run_id text references analysis_runs(run_id),
  user_id text references users(user_id),
  type text,
  subtype text,
  merchant text,
  rupee_impact float,
  severity text,
  explanation text,
  action text,
  resolved boolean default false,
  created_at timestamptz default now()
);

-- 4. Resolved actions
create table if not exists resolved_actions (
  id uuid default gen_random_uuid() primary key,
  finding_id uuid references findings(id),
  user_id text,
  resolved_at timestamptz default now(),
  rupee_saved float,
  notes text
);

-- 5. User Income (NEW)
create table if not exists user_income (
  user_id        text primary key references users(user_id),
  monthly_income float not null,
  updated_at     timestamptz default now()
);

-- 6. Goals (NEW)
create table if not exists goals (
  goal_id        uuid default gen_random_uuid() primary key,
  user_id        text references users(user_id),
  name           text not null,
  goal_type      text not null default 'saving',
  target_amount  float not null,
  saved_amount   float default 0,
  surplus_pct    float not null,
  is_active      bool default true,
  created_at     timestamptz default now()
);

-- 7. Goal Snapshots (NEW)
create table if not exists goal_snapshots (
  id                   uuid default gen_random_uuid() primary key,
  run_id               text references analysis_runs(run_id),
  goal_id              uuid references goals(goal_id),
  months_at_current    float,
  months_at_balanced   float,
  months_at_conservative float,
  biggest_lever_category text,
  biggest_lever_days_saved int,
  snapshot_date        timestamptz default now()
);

-- Enable Row Level Security
alter table users enable row level security;
alter table analysis_runs enable row level security;
alter table findings enable row level security;
alter table resolved_actions enable row level security;
alter table user_income enable row level security;
alter table goals enable row level security;
alter table goal_snapshots enable row level security;

-- Allow full access via service key
create policy "Service key full access" on users for all using (true);
create policy "Service key full access" on analysis_runs for all using (true);
create policy "Service key full access" on findings for all using (true);
create policy "Service key full access" on resolved_actions for all using (true);
create policy "Service key full access" on user_income for all using (true);
create policy "Service key full access" on goals for all using (true);
create policy "Service key full access" on goal_snapshots for all using (true);

-- 8. User Provider Config (NEW - BYOK)
create table if not exists user_provider_config (
  user_id       text primary key references users(user_id),
  provider      text not null,    -- 'google' | 'openai' | 'openrouter' | 'mistral'
  model_id      text not null,    -- the selected model string
  api_key       text not null,    -- stored as-is (user's own key, BYOK)
  exa_api_key   text default '',
  updated_at    timestamptz default now()
);

alter table user_provider_config enable row level security;
create policy "Service key full access" on user_provider_config for all using (true);
