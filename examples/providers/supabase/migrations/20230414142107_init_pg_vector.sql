create extension vector;

create table if not exists documents (
    id text primary key default gen_random_uuid()::text,
    source text,
    source_id text,
    content text,
    document_id text,
    author text,
    url text,
    created_at timestamptz default now(),
    embedding vector(1536)
);

create index ix_documents_document_id on documents using btree ( document_id );
create index ix_documents_source on documents using btree ( source );
create index ix_documents_source_id on documents using btree ( source_id );
create index ix_documents_author on documents using btree ( author );
create index ix_documents_created_at on documents using brin ( created_at );

alter table documents enable row level security;

create or replace function match_page_sections(in_embedding vector(1536)
                                            , in_match_count int default 3
                                            , in_document_id text default '%%'
                                            , in_source_id text default '%%'
                                            , in_source text default '%%'
                                            , in_author text default '%%'
                                            , in_start_date timestamptz default '-infinity'
                                            , in_end_date timestamptz default 'infinity')
returns table (id text
            , source text
            , source_id text
            , document_id text
            , url text
            , created_at timestamptz
            , author text
            , content text
            , embedding vector(1536)
            , similarity float)
language plpgsql
as $$
#variable_conflict use_variable
begin
return query
select
    documents.id,
    documents.source,
    documents.source_id,
    documents.document_id,
    documents.url,
    documents.created_at,
    documents.author,
    documents.content,
    documents.embedding,
    (documents.embedding <#> in_embedding) * -1 as similarity
from documents

where in_start_date <= documents.created_at and 
    documents.created_at <= in_end_date and
    (documents.source_id like in_source_id or documents.source_id is null) and
    (documents.source like in_source or documents.source is null) and
    (documents.author like in_author or documents.author is null) and
    (documents.document_id like in_document_id or documents.document_id is null)

order by documents.embedding <#> in_embedding

limit in_match_count;
end;
$$;