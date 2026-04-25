# Gotchas

- Public observations intentionally hide legal actions. Agents must reason from rules and state.
- Queued plans stop at reveal boundaries so agents can replan after new board state appears.
- Warden control is automatic and should stay bounded by visible clues, scripts, or dread budget.
- `classic_dynamic` changes turn rhythm; default DungeonGrid behavior remains AP-based.
- Fixed seeds are expected to be deterministic for a fixed action sequence.
- Use `private_state_json()` only for debugging, baselines, and eval infrastructure.
