# owlgate-agents

The agentic brain of **OwlGate** — three coded agents that reason about a change
and decide whether it is safe to ship. Deployed as UiPath **coded agents** and
orchestrated by [`owlgate-platform`](../owlgate-platform).

## Agents

| Agent | Input | Output |
| :--- | :--- | :--- |
| **RiskAgent** | a diff (changed files) + the test catalogue | impacted suites + a risk score |
| **HealingAgent** | a failed test + failure context | a proposed fix (patch) + re-run request |
| **GateAgent** | run results + heal results + risk | a **go / no-go** verdict + rationale |

## Stack

- Python 3.11+, **LangGraph** for agent control flow.
- Packaged as a UiPath coded agent (`uip codedagent`), run on AI units.
- The HealingAgent delegates patch authoring to a **coding agent** (Claude Code via
  UiPath for Coding Agents).

## Design conventions

- **Object-oriented** — one class per agent, sharing an `Agent` base.
- **Exception-driven** — failures raise typed exceptions from `errors.py`; callers
  never branch on sentinel return values.

## Develop

```bash
uv sync                 # or: pip install -e .
uip codedagent run risk --input examples/diff.json
uip codedagent pack && uip codedagent publish
```

## License

[MIT](./LICENSE)
