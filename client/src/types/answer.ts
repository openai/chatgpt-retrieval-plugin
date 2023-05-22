type Answer = {
    query: string;
    results: [{
      embedding?: [],
      id: string,
      metadata: {
        author?: string,
        created_at?: string,
        document_id?: string,
        source?: string,
        source_id?: string,
        url?: string,
      },
      score: number,
      text: string,
    }]
}