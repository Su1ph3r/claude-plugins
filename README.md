# su1ph3r Claude Code Plugins

Custom Claude Code plugin marketplace.

## Plugins

### bug-hunter

Multi-agent bug hunting for Claude Code. Launches parallel specialist agents across 8 bug categories, deduplicates and scores findings, runs a regression guard, and produces a prioritized report.

**Usage:**

```
/bug-hunter:bughunt                     # Diff-based scan, top 5 agents
/bug-hunter:bughunt --full              # Full codebase, top 5 agents
/bug-hunter:bughunt --thorough          # All 8 agents, diff-based
/bug-hunter:bughunt --security          # Deep security audit only
/bug-hunter:bughunt src/auth/           # Specific path
/bug-hunter:bughunt --thorough --full   # All agents, full codebase
```

**Agents:**

| Agent | Hunts For |
|---|---|
| `logic-hunter` | Off-by-ones, wrong comparisons, inverted conditions, unreachable code |
| `error-handler` | Silent failures, swallowed exceptions, empty catches, fallback masking |
| `edge-case-finder` | Null paths, empty collections, boundary values, overflow, Unicode |
| `security-scanner` | Injection, auth bypass, path traversal, SSRF, hardcoded secrets |
| `race-condition-detector` | Shared mutable state, TOCTOU, deadlocks, async pitfalls |
| `resource-leak-hunter` | Unclosed files/connections, missing cleanup, thread leaks |
| `api-contract-checker` | Type mismatches, wrong arg order, schema drift, return value misuse |
| `state-bug-finder` | Stale state, missing UI updates, cache invalidation, state machine bugs |
| `regression-guard` | Test coverage gaps, downstream consumers, public API breaks, fix risk |

## Installation

Add this marketplace to Claude Code:

```
/plugins marketplace add su1ph3r/claude-plugins
```

Then install a plugin:

```
/plugins install bug-hunter
```
