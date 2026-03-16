# Docs: Add LangChain integration guide

**Labels:** `good first issue`, `help wanted`, `documentation`, `integrations`

## Description

Write a guide showing how to use RuleShield with LangChain. Since RuleShield acts as an OpenAI-compatible proxy, LangChain users only need to point their `OPENAI_BASE_URL` (or `base_url` parameter) at the RuleShield proxy to get automatic cost savings on all LLM calls -- no code changes to their chains or agents.

## Why this is useful

LangChain is one of the most widely used LLM frameworks. A clear integration guide lowers the barrier for LangChain users to try RuleShield and immediately see cost savings. Many developers discover tools through integration docs, so this page can be a significant driver of adoption.

## Where to look in the codebase

### Existing documentation pages

**Directory:** `dashboard/src/routes/docs/`

The dashboard has a built-in documentation section with these pages:
- `dashboard/src/routes/docs/+page.svelte` -- Docs index / getting started
- `dashboard/src/routes/docs/api/+page.svelte` -- API reference
- `dashboard/src/routes/docs/architecture/+page.svelte` -- Architecture overview
- `dashboard/src/routes/docs/hermes/+page.svelte` -- Hermes Agent integration

The docs layout is at `dashboard/src/routes/docs/+layout.svelte`.

### Proxy endpoint

**File:** `ruleshield/proxy.py`

RuleShield exposes an OpenAI-compatible endpoint at `/v1/chat/completions`. The proxy runs on `localhost:8347` by default (configurable via `RULESHIELD_PORT` env var or `~/.ruleshield/config.yaml`).

### How the proxy works

The proxy intercepts OpenAI-format requests, checks rules and cache, and either returns a cached/rule response or forwards to the upstream provider. This is completely transparent to the client -- it sees standard OpenAI API responses.

## What to build

Create a new Svelte page at `dashboard/src/routes/docs/langchain/+page.svelte` with the following content:

### Guide outline

1. **Prerequisites** -- RuleShield running (`ruleshield start`), LangChain installed
2. **Method 1: Environment variable** -- Set `OPENAI_BASE_URL=http://localhost:8347/v1`
3. **Method 2: Constructor parameter** -- Pass `base_url` to `ChatOpenAI()`
4. **Full working example** -- A complete Python script that builds a simple chain
5. **Verifying it works** -- How to check `ruleshield stats` to confirm requests are being intercepted
6. **Using with other providers** -- How to set `provider_url` in RuleShield config for Anthropic, etc.

### Example Python script to include

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Point LangChain at the RuleShield proxy
llm = ChatOpenAI(
    model="gpt-4o",
    base_url="http://localhost:8347/v1",  # RuleShield proxy
    api_key="your-openai-api-key",        # Still needs a real API key for passthrough
)

# Simple chain example
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
])

chain = prompt | llm

# This will be intercepted by a rule (greeting pattern)
response = chain.invoke({"input": "hello"})
print(response.content)

# This will pass through to the real LLM
response = chain.invoke({"input": "Explain the CAP theorem with examples"})
print(response.content)
```

### Styling

Follow the same Svelte component structure and Tailwind classes used in the existing docs pages. Look at `dashboard/src/routes/docs/hermes/+page.svelte` for the closest example of an integration guide.

## Acceptance criteria

- [ ] File `dashboard/src/routes/docs/langchain/+page.svelte` exists and renders correctly
- [ ] The page is accessible at `/docs/langchain` when the dashboard is running
- [ ] Contains a working Python example showing LangChain integration
- [ ] Shows both the environment variable method and the constructor parameter method
- [ ] Includes a "Verify it works" section explaining how to check `ruleshield stats`
- [ ] Follows the same visual style as existing docs pages (dark background, code blocks, consistent typography)
- [ ] The docs sidebar/navigation (in `+layout.svelte`) includes a link to the new LangChain page
- [ ] Code examples are syntactically correct Python that would run if the user has the right packages installed

## Estimated difficulty

**Easy** -- This is a documentation/Svelte page creation task. No backend changes needed. The main work is writing clear, accurate content and matching the existing docs styling.

## Helpful links and references

- [Existing Hermes integration docs](../../dashboard/src/routes/docs/hermes/+page.svelte) -- Closest template to follow
- [Docs layout](../../dashboard/src/routes/docs/+layout.svelte) -- Sidebar navigation
- [Proxy source](../../ruleshield/proxy.py) -- Understanding the proxy endpoints
- LangChain ChatOpenAI docs: https://python.langchain.com/docs/integrations/chat/openai/
- LangChain base_url parameter: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.BaseChatOpenAI.html
