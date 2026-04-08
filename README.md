# Margin Call Automation Tool

CLI tool that processes margin call spreadsheets, creates Jira tickets, and emails financial advisors.

## Setup

### 1. Install Python dependencies

```bash
cd margin
pip install -e .
```

### 2. Configure

Copy the example files and fill in your values:

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

**config.yaml** — file paths, error types to filter, Jira project settings, email sender.

**.env** — API secrets (Jira token, Microsoft Graph credentials). Never commit this file.

### 3. Add your files

- Place your **advisor lookup** file (CSV or Excel) at the path specified in `config.yaml`
- The **margin spreadsheet** path in `config.yaml` should point to where the file gets dropped

### 4. Email attachments

Place any PDFs or documents you want attached to emails in the `attachments/` directory, and list them in `config.yaml`.

## Usage

```bash
# Preview what would happen (no API calls)
margin-tool tickets --dry-run
margin-tool emails --dry-run
margin-tool run --dry-run

# Create Jira tickets only
margin-tool tickets

# Send emails only
margin-tool emails

# Both tickets + emails
margin-tool run

# Review flagged duplicates
margin-tool duplicates

# Clear flagged duplicates after review
margin-tool duplicates --clear
```

### Options

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to config file (default: `config.yaml`) |
| `--dry-run` | Preview actions without making API calls |
| `-v, --verbose` | Enable debug logging |

## How It Works

1. Reads the margin spreadsheet and filters rows by the configured error types
2. Checks each item against the SQLite tracker database for duplicates
3. **Duplicates** are flagged for review (not skipped, not re-processed)
4. New items get a Jira ticket created and/or an email sent to the advisor
5. Advisor email is looked up by matching account number to the advisor file

## Spreadsheet Columns

**Margin file** (Excel): Account Number, Error Type, Date, Dollar Amount

**Advisor lookup** (CSV or Excel): Account Number, Firm Name, Email

Column names are matched flexibly — common variations like "Acct No", "Amount", "Advisor Email" are auto-detected.

## Team Setup

Each team member needs to:
1. Clone this repo
2. Run `pip install -e .`
3. Create their own `.env` with their API credentials
4. Use the shared `config.yaml` (no secrets in it)
