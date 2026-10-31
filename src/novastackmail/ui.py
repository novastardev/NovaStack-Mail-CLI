from rich.align import Align
from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_header(console):
    content = Text()
    content.append("✦ NOVASTACK MAIL\n", style="bold bright_cyan")
    content.append("Your mailbox. Your command line.", style="dim")
    console.print(Panel(Align.center(content), border_style="bright_blue", box=ROUNDED, padding=(1, 3)))


def render_login_success(console, mailbox, expires_at):
    details = Text()
    details.append("  STATUS   ", style="dim"); details.append("● AUTHENTICATED\n", style="bold green")
    details.append("  MAILBOX  ", style="dim"); details.append(f"{mailbox}\n", style="bold white")
    details.append("  EXPIRES  ", style="dim"); details.append(str(expires_at), style="cyan")
    console.print(Panel(details, title="[bold green]LOGIN SUCCESSFUL[/bold green]", border_style="green", box=ROUNDED, padding=(1, 2)))
    console.print("[dim]Access token saved with private file permissions.[/dim]")


def render_logout_success(console, mailbox):
    details = Text()
    details.append("  STATUS   ", style="dim"); details.append("● REVOKED\n", style="bold green")
    details.append("  MAILBOX  ", style="dim"); details.append(f"{mailbox}\n", style="bold white")
    details.append("  SECURITY ", style="dim"); details.append("Access token invalidated", style="cyan")
    console.print(Panel(details, title="[bold green]LOGOUT SUCCESSFUL[/bold green]", border_style="green", box=ROUNDED, padding=(1, 2)))
    console.print("[dim]Your local access token has been removed securely.[/dim]")


def render_logout_cancelled(console):
    console.print(Panel("[yellow]Logout cancelled.[/yellow]\nYour session is still active.", title="[bold yellow]SESSION KEPT[/bold yellow]", border_style="yellow", box=ROUNDED, padding=(1, 2)))


def render_status(console, mailbox, expires_at, api_base):
    details = Text()
    for label, value, style in [
        ("SESSION", "● ACTIVE", "bold green"),
        ("MAILBOX", mailbox.get("address", "Unknown"), "bold white"),
        ("MAILBOX ID", mailbox.get("id") or "Not available", "cyan"),
        ("CREATED", mailbox.get("createdAt") or "Not available", "white"),
        ("TYPE", "Permanent mailbox", "white"),
        ("TOKEN EXPIRES", expires_at or "Not provided", "yellow"),
        ("API", api_base, "cyan"),
    ]:
        details.append("  " + label + "  ", style="dim")
        details.append(str(value) + "\n", style=style)
    console.print(Panel(details, title="[bold bright_cyan]MAILBOX STATUS[/bold bright_cyan]", border_style="bright_blue", box=ROUNDED, padding=(1, 2)))
    console.print("[dim]Live session verified. Access token is hidden.[/dim]")


def render_status_error(console, message, signed_in=False):
    if signed_in:
        title, detail, border = "[bold red]STATUS CHECK FAILED[/bold red]", "[yellow]Your saved token was not deleted. Try again or sign in again if it has expired.[/yellow]", "red"
    else:
        title, detail, border = "[bold yellow]NOT SIGNED IN[/bold yellow]", "[dim]Run novastackmail --login to connect a mailbox.[/dim]", "yellow"
    console.print(Panel(f"[white]{message}[/white]\n{detail}", title=title, border_style=border, box=ROUNDED, padding=(1, 2)))


def render_inbox(console, mailbox, messages, pagination=None):
    table = Table(title=f"INBOX · {mailbox}", box=ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("MESSAGE ID", style="bright_cyan", no_wrap=True, overflow="fold")
    table.add_column("STATUS", width=9)
    table.add_column("FROM", style="cyan", max_width=26)
    table.add_column("SUBJECT", style="bold white", max_width=36)
    table.add_column("RECEIVED", style="dim", max_width=21)
    for index, message in enumerate(messages, start=1):
        read_value = message.get("isRead", message.get("is_read", message.get("read")))
        status = "Read" if read_value is True else "Unread" if read_value is False else "Unknown"
        status_style = "green" if status == "Read" else "yellow" if status == "Unread" else "dim"
        table.add_row(Text(str(index)), Text(str(message.get("id") or "Missing ID"), style="bright_cyan"),
                      Text(status, style=status_style),
                      Text(str(message.get("from") or "Unknown")),
                      Text(str(message.get("subject") or "(no subject)")),
                      Text(str(message.get("date") or "Unknown")))
    if messages:
        console.print(table)
        if pagination:
            console.print(f"[dim]Page {pagination.get('page', 1)} of {pagination.get('totalPages', 1)} · {pagination.get('total', len(messages))} message(s) · {pagination.get('perPage', len(messages))} per page[/dim]")
    else:
        console.print(Panel("[dim]No messages yet. New emails will appear here.[/dim]", title="[bold bright_cyan]INBOX[/bold bright_cyan]", border_style="bright_blue", box=ROUNDED))


def render_message(console, message):
    details = Text()
    for label, value in [
        ("FROM", message.get("from")), ("TO", message.get("to")),
        ("SUBJECT", message.get("subject")), ("DATE", message.get("date")),
        ("STATUS", "Read" if message.get("isRead") is True else "Unread" if message.get("isRead") is False else "Unknown"),
    ]:
        details.append(label + "  ", style="dim")
        details.append(str(value or "Unknown") + "\n", style="white")
    body = message.get("text") or "(This message has no plain-text body.)"
    console.print(Panel(details, title="[bold bright_cyan]MESSAGE[/bold bright_cyan]", border_style="bright_blue", box=ROUNDED))
    console.print(Panel(Text(str(body)), title="[bold]BODY[/bold]", border_style="blue", box=ROUNDED))
    attachments = message.get("attachments") or []
    if attachments:
        table = Table(title="ATTACHMENTS", box=ROUNDED)
        table.add_column("ID"); table.add_column("FILENAME"); table.add_column("SIZE")
        for item in attachments:
            table.add_row(str(item.get("id", "")), str(item.get("filename", "attachment")), str(item.get("size") or "Unknown"))
        console.print(table)


def render_attachments(console, message):
    attachments = message.get("attachments") or []
    if not attachments:
        console.print("[dim]This message has no attachments.[/dim]")
        return
    table = Table(title=f"ATTACHMENTS · {message.get('subject') or message.get('id')}", box=ROUNDED)
    table.add_column("ID"); table.add_column("FILENAME"); table.add_column("TYPE"); table.add_column("SIZE")
    for item in attachments:
        table.add_row(Text(str(item.get("id", ""))), Text(str(item.get("filename", "attachment"))),
                      Text(str(item.get("contentType", "unknown"))), Text(str(item.get("size") or "Unknown")))
    console.print(table)
