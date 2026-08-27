# Slack changelog setup

ASTRA can post a deterministic changelog after every GitHub push. It summarizes
the branch, commits, changed files, and affected components directly from the
GitHub push event. It does not call an AI model and therefore consumes no model
tokens.

## One-time setup

1. In the intended Slack workspace, create or open a Slack app with **Incoming
   Webhooks** enabled.
2. Add a webhook to the channel where the team wants ASTRA changelogs.
3. In the GitHub repository, open **Settings → Secrets and variables → Actions**.
4. Create a repository secret named `SLACK_WEBHOOK_URL` and paste the webhook URL
   as its value.
5. Push a small test commit. The **Slack changelog** workflow should post one
   message to the selected channel.

The webhook URL must never be committed to the repository. The workflow only
reads it from GitHub Actions secrets. If the secret is absent, pushes and tests
continue normally and the Slack step reports that the optional integration was
skipped.
