# llm-prompt-registry

A from-scratch prompt registry for LLM applications: versioning, A/B routing, evaluation, and instant rollback — with a web dashboard.

No frameworks. No LangChain. Just Python, YAML, and deliberate engineering decisions.

---

## Why this exists

In most LLM apps, prompts are hardcoded inside application code:

```python
prompt = "You are a helpful support agent. Answer: {user_text}"
```

That means every wording change requires a code change → PR → CI → deploy. Prompt iteration becomes the slowest part of shipping an AI product.

A **prompt registry** fixes this by decoupling prompt text from application code. Prompts become managed, versioned configuration. The application asks the registry for the *active* prompt at runtime — so changing production behavior becomes a UI click, not a deploy.

## How it helps software

The registry is the **control plane** for prompt behavior; your application is the **data plane** that consumes it:

1. **Humans** use the dashboard to draft, evaluate, and deploy prompts.
2. **Software** fetches the active prompt by name at runtime and never hardcodes text.

```python
# Production app code — no prompt text, just a lookup
template = registry.get("support_bot", user_text=user_text)
response = llm.call(template)
```

Because the app always resolves the active version at call time:

- **Deploying** a new prompt = flipping a pointer. No code deploy, no restart.
- **A bad prompt** = one-click rollback to the last known-good version.
- **A risky change** = A/B test on a slice of traffic before full rollout.

In a full production deployment, this engine sits behind an HTTP API (e.g., FastAPI) with a cache layer, and apps poll or subscribe for changes. This repo implements the core engine and workflow that such a service wraps.

## The workflow

```
Draft → Save Version → Evaluate → Deploy / A/B test → Rollback if needed
```

1. **Edit** a prompt in the dashboard's template editor.
2. **Save as New Version** — creates `v3.yaml` next to `v1`, `v2`… history is immutable.
3. **Run Evaluations** — the prompt is tested against sample inputs; Gemini (LLM-as-a-Judge) scores quality and reports latency, token usage, and estimated cost.
4. **Deploy to Active** — flips the active pointer in `config.yaml`. Every consumer now gets the new version.
5. **Rollback** — the audit log records every change; rollback restores the previous active version instantly.

## Features

- **Versioning** — immutable YAML versions (`v1`, `v2`, …) with metadata (author, timestamp).
- **Deterministic A/B routing** — traffic split by MD5 hash of `user_id`, so the same user always sees the same variant. No database needed.
- **Instant rollback** — append-only `audit_log.json` enables one-step revert.
- **LLM-as-a-Judge evals** — automated quality scoring via the Gemini API.
- **Cost & latency metrics** — token counts and estimated spend per evaluation run.
- **Streamlit dashboard** — non-engineers can manage prompts without touching code.

## Project structure

```
llm-prompt-registry/
├── app.py            # Streamlit dashboard (control plane UI)
├── registry.py       # Core engine: versioning, routing, rollback
├── evaluator.py      # LLM-as-a-Judge eval harness + metrics (Gemini)
├── main.py           # CLI demo of the registry engine
├── config.yaml       # Active-version pointers + A/B config
├── audit_log.json    # Append-only change history
├── requirements.txt
└── prompts/
    ├── welcome_email/
    │   ├── v1.yaml
    │   └── v2.yaml
    └── summarize_article/
        ├── v1.yaml
        └── v2.yaml
```

## Getting started

### 1. Install

```bash
git clone https://github.com/BLVCK-MAMBA-6/llm-prompt-registry.git
cd llm-prompt-registry
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file with a [Google AI Studio](https://aistudio.google.com/app/apikey) API key:

```
GEMINI_API_KEY=your_key_here
```

> Note: the registry engine itself needs **no API key**. The key only powers the evaluation harness.

### 3. Run

```bash
# Web dashboard
streamlit run app.py

# CLI demo
python main.py
```

## Using the registry in code

```python
from registry import PromptRegistry

registry = PromptRegistry()

# Fetch the active prompt, formatted with variables
prompt = registry.get("welcome_email", user_name="Sarah", company_name="Acme")

# A/B routing: deterministic per user
prompt = registry.get("welcome_email", user_id="user_001",
                      user_name="Sarah", company_name="Acme")

# Promote a version, roll back if needed
registry.change_version("welcome_email", "v2")
registry.rollback("welcome_email")
```

## Design decisions (and tradeoffs)

- **YAML files over a database** — human-readable, Git-diffable, zero setup. *Tradeoff:* not safe for concurrent writes; production would swap in Postgres/Redis.
- **Hash-based A/B routing** — stateless and deterministic. *Tradeoff:* changing the split percentage can reshuffle users between variants.
- **In-process evals** — simple and synchronous. *Tradeoff:* production would run evals asynchronously in CI on pull requests.

## Roadmap (production hardening)

- [ ] FastAPI data-plane layer (`GET /prompts/{name}/active`)
- [ ] Redis caching + webhook/pub-sub propagation on deploy
- [ ] Variable-schema validation on deploy (block prompts that break the app's contract)
- [ ] CI eval gates (run `evaluator.py` automatically on PRs)
- [ ] Auth / RBAC on the dashboard

## License

GPL-3.0
