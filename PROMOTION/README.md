# AgentPub MCP 4-Directory Submission

AgentPub `io.github.sampson/agentpub` v0.1.4 is the Win11 single-file
implementation. To get LLM-aware agents (Claude Desktop, Cursor, Windsurf,
Cline) to discover AgentPub, the MCP server entry must be present in
4 public MCP directories. This directory contains ready-to-paste
form-field payloads for each.

## How to submit (sampson / CZ)

For each directory:

1. Open the URL
2. Register / log in (sampson: use the sampson119 GitHub account)
3. Paste the form fields from each `1_pulsemcp.md` / `2_glama.md` / `3_smithery.md` / `4_mcpso.md`
4. Submit
5. Reply in the PR / issue / sampson's CZ session with the resulting public URL

## Live endpoint to reference

- Win11 app: http://127.0.0.1:7701 (local)
- Public via ngrok: sampson needs to add 7701 tunnel to ngrok config
  (see `~/AppData/Roaming/ngrok/ngrok.yml` in Win11) and re-auth

## File map

- `1_pulsemcp.md` — PulseMCP submission form fields
- `2_glama.md` — Glama submission form fields
- `3_smithery.md` — Smithery (CLI preferred, form fallback) fields
- `4_mcpso.md` — MCP.so submission form fields
- `SUBMIT_GUIDE.md` — sampson's step-by-step
