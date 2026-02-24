-- Run this in Supabase SQL Editor
create table if not exists questions (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default now(),
  session_id text not null,
  phone_number text not null,
  question text not null,
  status text not null default 'pending',
  answer text,
  error text
);

create index if not exists questions_session_id_idx on questions(session_id);
create index if not exists questions_phone_number_idx on questions(phone_number);
