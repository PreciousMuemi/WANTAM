-- Run this SQL in your Supabase SQL Editor (SQL > New Query)
-- Create documents table with vector column

create table if not exists documents (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default now(),
  source_url text not null,
  document_title text not null,
  chunk_id integer not null,
  text text not null,
  page_number integer not null,
  token_count integer,
  embedding vector(3072)
);

-- Create index for faster similarity search
create index if not exists documents_embedding_idx 
  on documents using ivfflat (embedding vector_cosine_ops) 
  with (lists = 100);

-- Create index for URL lookups
create index if not exists documents_source_url_idx 
  on documents(source_url);

-- Create RPC function for vector similarity search
create or replace function match_documents (
  query_embedding vector(3072),
  match_count int default 5
)
returns table (
  id bigint,
  text text,
  source_url text,
  document_title text,
  chunk_id int,
  page_number int,
  similarity float
) language sql stable
as $$
  select
    documents.id,
    documents.text,
    documents.source_url,
    documents.document_title,
    documents.chunk_id,
    documents.page_number,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.embedding is not null
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;

-- Grant permissions
grant execute on function match_documents(vector, int) to anon, authenticated;
