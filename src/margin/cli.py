import logging
import uuid

import click

from margin.config import load_config
from margin.email_client import OutlookClient
from margin.jira_client import JiraClient
from margin.lookup import get_advisor, load_advisors
from margin.reader import read_margin_file
from margin.tracker import Tracker


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


@click.group()
@click.option("--config", "config_path", default="config.yaml", type=click.Path(), help="Path to config.yaml")
@click.option("--dry-run", is_flag=True, help="Preview actions without making API calls")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, config_path, dry_run, verbose):
    """Margin call processing tool — create Jira tickets and notify advisors."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)
    ctx.obj["dry_run"] = dry_run


@cli.command()
@click.pass_context
def tickets(ctx):
    """Create Jira tickets for margin call items."""
    cfg = ctx.obj["config"]
    dry_run = ctx.obj["dry_run"]
    run_id = str(uuid.uuid4())

    items = read_margin_file(cfg.margin_file, cfg.error_types, cfg.margin_file_header_row)
    if not items:
        click.echo("No matching margin items found.")
        return

    advisors = load_advisors(cfg.advisor_file)
    tracker = Tracker(cfg.tracker_db)

    if not dry_run:
        jira = JiraClient(cfg.jira)

    created = 0
    duplicates = 0
    errors = 0

    for item in items:
        existing = tracker.check_duplicate(item)
        if existing:
            tracker.flag_duplicate(item, run_id)
            duplicates += 1
            click.echo(
                f"  DUPLICATE: {item.account_number} / {item.error_type} "
                f"(previously processed {existing.processed_at}). Flagged for review."
            )
            continue

        advisor = get_advisor(advisors, item.account_number)

        if dry_run:
            click.echo(
                f"  [DRY RUN] Would create ticket: "
                f"{item.account_number} - {item.error_type} - ${item.dollar_amount:,.2f}"
            )
            continue

        try:
            ticket_key = jira.create_ticket(item, advisor)
            tracker.record_processing(
                item, run_id, jira_ticket_key=ticket_key,
                advisor_firm=advisor.firm_name if advisor else None,
                advisor_email=advisor.email if advisor else None
            )
            created += 1
            click.echo(f"  Created {ticket_key}: {item.account_number} - {item.error_type}")
        except Exception as e:
            errors += 1
            click.echo(f"  ERROR: {item.account_number} - {item.error_type}: {e}")

    tracker.close()
    click.echo(f"\nSummary: {created} created, {duplicates} duplicates flagged, {errors} errors")

    if not dry_run and created > 0:
        Tracker(cfg.tracker_db).write_history_sheet(cfg.margin_file)
        Tracker(cfg.tracker_db).close()


@cli.command()
@click.pass_context
def emails(ctx):
    """Send advisor notification emails for margin call items."""
    cfg = ctx.obj["config"]
    dry_run = ctx.obj["dry_run"]
    run_id = str(uuid.uuid4())

    items = read_margin_file(cfg.margin_file, cfg.error_types, cfg.margin_file_header_row)
    if not items:
        click.echo("No matching margin items found.")
        return

    advisors = load_advisors(cfg.advisor_file)
    tracker = Tracker(cfg.tracker_db)

    if not dry_run:
        outlook = OutlookClient(cfg.outlook, manual_send=cfg.outlook.manual_send)

    sent = 0
    duplicates = 0
    skipped = 0
    errors = 0

    for item in items:
        existing = tracker.check_duplicate(item)
        if existing:
            tracker.flag_duplicate(item, run_id)
            duplicates += 1
            click.echo(
                f"  DUPLICATE: {item.account_number} / {item.error_type} "
                f"(previously processed {existing.processed_at}). Flagged for review."
            )
            continue

        advisor = get_advisor(advisors, item.account_number)
        if advisor is None:
            skipped += 1
            click.echo(f"  SKIPPED: No advisor found for account {item.account_number}")
            continue

        jira_key = tracker.get_jira_key(item)

        if dry_run:
            click.echo(
                f"  [DRY RUN] Would email {advisor.email} ({advisor.firm_name}): "
                f"{item.account_number} - {item.error_type} - ${item.dollar_amount:,.2f}"
            )
            continue

        try:
            outlook.send_email(
                advisor, item, cfg.email_template, cfg.attachments, jira_key
            )
            tracker.record_processing(
                item, run_id, jira_ticket_key=jira_key, email_sent=True,
                advisor_firm=advisor.firm_name if advisor else None,
                advisor_email=advisor.email if advisor else None
            )
            sent += 1
            click.echo(f"  Emailed {advisor.email}: {item.account_number} - {item.error_type}")
        except Exception as e:
            errors += 1
            click.echo(f"  ERROR: {item.account_number} - {e}")

    tracker.close()
    click.echo(f"\nSummary: {sent} sent, {duplicates} duplicates flagged, {skipped} skipped (no advisor), {errors} errors")

    if not dry_run and sent > 0:
        Tracker(cfg.tracker_db).write_history_sheet(cfg.margin_file)
        Tracker(cfg.tracker_db).close()


@cli.command()
@click.pass_context
def run(ctx):
    """Process margin calls: create Jira tickets, then send emails."""
    click.echo("=== Creating Jira Tickets ===")
    ctx.invoke(tickets)
    click.echo("\n=== Sending Advisor Emails ===")
    ctx.invoke(emails)


@cli.command()
@click.option("--clear", is_flag=True, help="Clear all flagged duplicates after review")
@click.pass_context
def duplicates(ctx):
    """Review or clear flagged duplicate margin items."""
    cfg = ctx.obj["config"]
    tracker = Tracker(cfg.tracker_db)

    if ctx.params["clear"]:
        count = tracker.clear_flagged()
        click.echo(f"Cleared {count} flagged duplicates.")
        tracker.close()
        return

    flagged = tracker.get_flagged_duplicates()
    if not flagged:
        click.echo("No flagged duplicates.")
        tracker.close()
        return

    click.echo(f"Flagged duplicates ({len(flagged)}):\n")
    for rec in flagged:
        click.echo(
            f"  Account: {rec.account_number}  |  Error: {rec.error_type}  |  "
            f"Date: {rec.margin_date}  |  Amount: ${rec.dollar_amount}  |  "
            f"Flagged at: {rec.processed_at}"
        )

    click.echo(f"\nRun 'margin-tool duplicates --clear' to clear after review.")
    tracker.close()
