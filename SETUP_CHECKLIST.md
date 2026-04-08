# Work Computer Setup Checklist

Everything you need to do to get margin-tool running on your work machine.

## Prerequisites

- [ ] Python 3.9+ installed (`python3 --version` to check)
- [ ] Git installed and authenticated with GitHub
- [ ] Access to the shared drive where the margin spreadsheet gets dropped

## Step 1: Clone the repo

```bash
git clone https://github.com/bajor3k/margin-tool.git
cd margin-tool
```

## Step 2: Install the tool

```bash
pip install -e .
```

Verify it worked:

```bash
margin-tool --help
```

## Step 3: Set up your config file

```bash
cp config.yaml.example config.yaml
```

Open `config.yaml` and update:

- [ ] `margin_file` — full path to where the margin spreadsheet lands (e.g. `//server/share/margin_calls.xlsx`)
- [ ] `advisor_file` — full path to your advisor lookup CSV/Excel
- [ ] `error_types` — the exact error type values from the spreadsheet that should trigger processing
- [ ] `jira.base_url` — your Jira instance URL (e.g. `https://yourcompany.atlassian.net`)
- [ ] `jira.project_key` — the Jira project key for margin tickets
- [ ] `outlook.tenant_id` — your Azure AD tenant ID
- [ ] `outlook.sender` — the email address to send from

## Step 4: Set up your secrets

```bash
cp .env.example .env
```

Open `.env` and fill in:

- [ ] `JIRA_API_TOKEN` — generate at https://id.atlassian.com/manage-profile/security/api-tokens
- [ ] `JIRA_USER_EMAIL` — your Jira account email
- [ ] `GRAPH_CLIENT_ID` — from your Azure AD app registration
- [ ] `GRAPH_CLIENT_SECRET` — from your Azure AD app registration
- [ ] `GRAPH_TENANT_ID` — your Azure AD tenant ID

## Step 5: Azure AD app registration (for Outlook emails)

You need an Azure AD app with permission to send email. If this isn't set up yet:

- [ ] Go to Azure Portal > App registrations > New registration
- [ ] Name it something like "Margin Tool"
- [ ] Under API permissions, add `Mail.Send` (Application permission, not Delegated)
- [ ] Get admin consent for the permission
- [ ] Create a client secret under Certificates & secrets
- [ ] Copy the Client ID, Client Secret, and Tenant ID into your `.env`

## Step 6: Prepare the advisor lookup file

- [ ] Export your advisor report with columns: Account Number, Firm Name, Email
- [ ] Save it as CSV or Excel at the path you set in `config.yaml`

## Step 7: Add email attachments

- [ ] Copy any resolution PDFs into the `attachments/` folder
- [ ] List them in `config.yaml` under `attachments:`

## Step 8: Test it

```bash
# Dry run first — no API calls, just shows what would happen
margin-tool run --dry-run
```

- [ ] Verify it reads the margin spreadsheet correctly
- [ ] Verify it matches accounts to advisors
- [ ] Verify the right error types are being filtered

Once that looks good, run it for real:

```bash
margin-tool run
```

## Quick reference

| Command | What it does |
|---------|-------------|
| `margin-tool run --dry-run` | Preview full pipeline |
| `margin-tool run` | Create tickets + send emails |
| `margin-tool tickets` | Jira tickets only |
| `margin-tool emails` | Outlook emails only |
| `margin-tool duplicates` | Review flagged duplicates |
| `margin-tool duplicates --clear` | Clear duplicates after review |
