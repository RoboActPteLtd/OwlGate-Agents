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

### Tests

The deterministic core runs with **no external dependencies** (stdlib `unittest`,
also discoverable by `pytest`):

```bash
PYTHONPATH=src python -m unittest discover -s tests   # or: pytest
```

### RiskAgent at a glance

`RiskAgent` is implemented and deterministic — selection by source-glob matching,
risk score as a transparent weighted blend (tag severity, churn, coverage gap,
breadth) so a human can audit and override the number at the gate.

```python
from owlgate_agents import RiskAgent

result = RiskAgent().run({
    "diff": [{"path": "src/routes/api/contacts/+server.ts", "lines": 18}],
    "catalogue": "catalogues/sample-app.json",
})
print(result.to_dict())
# {'suites': ['api/contacts'], 'score': ..., 'high_risk': ..., 'untested': [], 'rationale': '...'}
```

## License

[Apache 2.0](./LICENSE)
