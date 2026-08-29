# ASTRA v0.0.20 RC — Review Notes

This remains an uncommitted review candidate on `DEV-need-check` based on `a2203c1`.
It includes the complete v0.0.19 audit/Slack work plus the v0.0.20 identity and
Conversation Learning Inbox additions. Nothing has been pushed.

## Highest-value Windows checks

1. Start `run_astra_gui.bat`, choose Erik, and create a local PIN.
2. Confirm `who am i` reports Erik and the title bar shows Erik.
3. Save a harmless Erik-only fact/preference, then use **Lock / switch**.
4. Create Petr's PIN and confirm Erik's fact/preference is absent.
5. Switch back to Erik and confirm it is present again.
6. Confirm the visible chat is cleared on every switch and Eyes stops while locked.
7. With Ollama active, have a short ordinary conversation and run
   `self learning scan`; inspect every candidate with `self learning review`.
8. Approve one harmless `memory_note`, reject the rest, restart, and confirm the
   approved note exists only under the same profile.
9. Run `python -m pytest -q` locally before approving a push.

## Security boundaries

- Never type a PIN into chat or commit `data/`.
- Profile PINs prevent accidental mixing; they are not filesystem encryption.
- A local administrator can still read the JSON runtime stores.
- Conversation scan suggestions are untrusted until explicitly approved.
