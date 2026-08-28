# Slack changelog setup

ASTRA posts a deterministic, versioned changelog after every GitHub push. The
message headline uses the current `config.json` version (for example
`ASTRA v0.0.21 changelog`) and the body uses the real feature/fix bullets from
`docs/CHANGELOG_PENDING_<version>.md`. Repository, branch, commit, file, and
component metadata remains attached below the release content. It does not call
an AI model and therefore consumes no model tokens.

Before pushing a new version, keep these values synchronized:

1. `config.json` → `version`
2. `pyproject.toml` → `project.version`
3. `docs/CHANGELOG_PENDING_<version>.md` → concrete `##` sections and `-` bullets

The `Verification` and manual-check sections are intentionally omitted from the
Slack feature summary. If the matching changelog file is absent, the workflow
still posts a versioned commit/file fallback instead of inventing release notes.

## One-time setup

1. In the intended Slack workspace, create or open a Slack app with **Incoming
   Webhooks** enabled.
2. Add a webhook to the channel where the team wants ASTRA changelogs.
3. In the GitHub repository, open **Settings → Secrets and variables → Actions**.
4. Create a repository secret named `SLACK_WEBHOOK_URL` and paste the webhook URL
   as its value.
5. Push a small test commit. The **Slack changelog** workflow should post one
   message containing the ASTRA version and concrete changelog bullets to the
   selected channel.

The webhook URL must never be committed to the repository. The workflow only
reads it from GitHub Actions secrets. If the secret is absent, pushes and tests
continue normally and the Slack step reports that the optional integration was
skipped.
