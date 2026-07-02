# ops-dashboard

Flask app serving 3 operational dashboards with LLM-powered chat. Users ask natural language questions about scheduling, forecasting, or delay attribution — the app grounds the answer in the actual data, not hallucinated numbers.

## what makes this different from "chatbot with data"

Each dashboard has its own context builder that extracts the *relevant* data slice for the question. If you ask "which sites have the highest push delay?" it pulls the top 10 from the delay dataset, builds a prompt with those numbers, and the LLM answers from that context. No vector DB, no RAG — just structured data selection + prompt engineering.

30K char context cap prevents hallucination. Array-of-arrays JSON format (40% smaller than objects). Stateless — history sent with each request.

## decisions

- No database. JSON loaded into memory at startup. Refreshes on server reload.
- Pluggable LLM backend — mock for local dev, real SDK in production. Same interface.
- `/health` is unauthenticated (load balancer needs it).
- Per-dashboard context builders because "relevant data" means different things for scheduling vs delay attribution.
