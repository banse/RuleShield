# Docs: Add CrewAI integration guide

**Labels:** `good first issue`, `help wanted`, `documentation`, `integrations`

## Description

Write a guide showing how to use RuleShield with CrewAI. Since CrewAI uses LLM providers that support OpenAI-compatible endpoints, users can point their CrewAI agents at the RuleShield proxy to get automatic cost savings on all LLM calls. This is especially valuable for CrewAI because multi-agent workflows multiply the number of LLM calls, making cost optimization critical.

## Why this is useful

CrewAI is a popular multi-agent framework where multiple AI agents collaborate on tasks. Each agent makes its own LLM calls, and many of those calls involve simple coordination messages ("I understand the task", "Proceeding to the next step", etc.) that are perfect candidates for rule interception. A clear integration guide helps CrewAI users realize significant savings on their multi-agent workflows.

## Where to look in the codebase

### Existing documentation pages

**Directory:** `dashboard/src/routes/docs/`

The dashboard has a built-in docs section:
- `dashboard/src/routes/docs/+page.svelte` -- Getting started
- `dashboard/src/routes/docs/api/+page.svelte` -- API reference
- `dashboard/src/routes/docs/architecture/+page.svelte` -- Architecture overview
- `dashboard/src/routes/docs/hermes/+page.svelte` -- Hermes integration guide
- (If issue #8 is completed first) `dashboard/src/routes/docs/langchain/+page.svelte` -- LangChain guide

The docs layout with sidebar navigation is at `dashboard/src/routes/docs/+layout.svelte`.

### Proxy details

**File:** `ruleshield/proxy.py`

RuleShield runs on `localhost:8347` by default and exposes `/v1/chat/completions` (OpenAI-compatible).

## What to build

Create a new Svelte page at `dashboard/src/routes/docs/crewai/+page.svelte`.

### Guide outline

1. **Why RuleShield + CrewAI** -- Multi-agent = many LLM calls = high costs. Rule interception catches the repetitive coordination messages.
2. **Prerequisites** -- RuleShield running, CrewAI installed
3. **Configuration** -- Set `OPENAI_BASE_URL` or configure the LLM object directly
4. **Full working example** -- A simple two-agent crew that uses the RuleShield proxy
5. **Monitoring savings** -- How to verify cost savings with `ruleshield stats` and the dashboard
6. **Tips for multi-agent optimization** -- Which patterns to add rules for (agent handoff messages, task confirmations, etc.)

### Example Python script to include

```python
import os
from crewai import Agent, Task, Crew, LLM

# Point CrewAI at the RuleShield proxy
llm = LLM(
    model="openai/gpt-4o",
    base_url="http://localhost:8347/v1",  # RuleShield proxy
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Define agents
researcher = Agent(
    role="Research Analyst",
    goal="Find key facts about a given topic",
    backstory="You are an experienced research analyst.",
    llm=llm,
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Write a clear summary based on research findings",
    backstory="You are a skilled technical writer.",
    llm=llm,
    verbose=True,
)

# Define tasks
research_task = Task(
    description="Research the benefits of LLM cost optimization for enterprises.",
    expected_output="A list of 5 key benefits with brief explanations.",
    agent=researcher,
)

write_task = Task(
    description="Write a one-paragraph summary based on the research findings.",
    expected_output="A concise paragraph summarizing the benefits.",
    agent=writer,
)

# Create and run the crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True,
)

result = crew.kickoff()
print(result)

# Check your savings: run `ruleshield stats` in another terminal
```

### Styling

Follow the same Svelte component structure and Tailwind classes used in existing docs pages. Use `dashboard/src/routes/docs/hermes/+page.svelte` as a template for the page structure.

## Acceptance criteria

- [ ] File `dashboard/src/routes/docs/crewai/+page.svelte` exists and renders correctly
- [ ] The page is accessible at `/docs/crewai` when the dashboard is running
- [ ] Contains a working Python example showing CrewAI integration with at least 2 agents
- [ ] Explains how to configure the LLM to point at the RuleShield proxy
- [ ] Includes a section on monitoring savings after running a crew
- [ ] Follows the same visual style as existing docs pages
- [ ] The docs sidebar navigation in `+layout.svelte` includes a link to the CrewAI page
- [ ] Code examples are syntactically correct Python

## Estimated difficulty

**Easy** -- Documentation and Svelte page creation. No backend changes. Follow the pattern of existing docs pages.

## Helpful links and references

- [Existing Hermes integration docs](../../dashboard/src/routes/docs/hermes/+page.svelte) -- Template to follow
- [Docs layout](../../dashboard/src/routes/docs/+layout.svelte) -- Sidebar navigation to update
- [Proxy source](../../ruleshield/proxy.py) -- Proxy endpoint details
- CrewAI documentation: https://docs.crewai.com/
- CrewAI LLM configuration: https://docs.crewai.com/concepts/llms
