# Phase 6 retrieval configuration check

This report records the reproducible chunk count/length comparison against the eight checked-in **synthetic demonstration policy** files. It is a structural configuration check, not a retrieval-quality benchmark. No labeled relevance set or real retailer policies are available.

| Chunk size (characters) | Overlap (characters) | Chunks | Mean chunk length (characters) |
| ---: | ---: | ---: | ---: |
| 350 | 50 | 26 | 237.3 |
| 600 | 100 | 25 | 244.8 |
| 900 | 150 | 25 | 244.8 |

The selected default is 600/100. The documents are short sectioned policy notes; the default avoids extra splits observed at 350 while retaining a modest overlap if a section grows. Since 600 and 900 produced equal chunk counts and the current corpus is short, the count comparison does not establish semantic or relevance superiority.

The current environment indexed 25 section documents into 25 chunks using `local-hash-v1-384` and `sqlite_cosine_fallback`. This embedding method uses lexical feature hashing and is explicitly **not semantic**. No embedding API key is configured. The retriever's unit tests exercise ranking and source references with temporary policies; there is no human-judged retrieval evaluation.

For an authorized deployment, evaluate policies and chunk settings against a labeled query-to-source set and a semantic embedding provider, then review retrieval failures with policy owners. The current index is local and rebuildable at `outputs/chroma` by default.
