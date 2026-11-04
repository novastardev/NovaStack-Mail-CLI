import argparse
import getpass
import json
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .client import DEFAULT_API_BASE, NovaStackMailClient, NovaStackMailError
from .config import active_profile, clear_config, config_path, load_config, save_config, validate_profile_name
from .ui import (
    render_attachments, render_header, render_inbox, render_login_success,
    render_logout_cancelled, render_logout_success, render_message,
    render_status, render_status_error,
)


console = Console()


def _client_for(config, api_base, timeout):
    profile = active_profile(config)
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or profile.get("access_token")
    return NovaStackMailClient(
        api_base=profile.get("api_base") or (config or {}).get("api_base") or api_base,
        access_token=token,
        timeout=timeout,
    )


def _emit_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _logout(api_base, timeout, quiet=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or active_profile(config).get("access_token")
    if not token:
        if not quiet:
            console.print("[yellow]No saved mailbox session was found on this device.[/yellow]")
        return 0
    mailbox_data = active_profile(config).get("mailbox") or {}
    mailbox = mailbox_data.get("address", "your mailbox")
    if not quiet:
        console.print(Panel(
            f"Mailbox: [cyan]{mailbox}[/cyan]\\n\\n[yellow]This revokes this device's access token.[/yellow]\\n"
            "[dim]Your mailbox and messages will not be deleted.[/dim]",
            title="[bold bright_cyan]CONFIRM LOGOUT[/bold bright_cyan]", border_style="bright_blue",
        ))
    if not Confirm.ask("[yellow]Are you sure you want to log out?[/yellow]", default=False):
        if not quiet:
            render_logout_cancelled(console)
        return 0
    try:
        _client_for(config, api_base, timeout).logout(token)
        if config and config.get("access_token") == token:
            clear_config()
        if not quiet:
            render_logout_success(console, mailbox)
        return 0
    except NovaStackMailError as exc:
        if not quiet:
            console.print(Panel(f"[red]Logout failed[/red]\n{exc}\n[yellow]Saved credentials were kept.[/yellow]", border_style="red"))
        return 1


def _status(api_base, timeout, as_json=False, quiet=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
    if not token:
        if not quiet:
            render_status_error(console, "No saved mailbox session was found on this device.")
        return 0
    try:
        client = _client_for(config, api_base, timeout)
        mailbox = client.get_mailbox(token)
        if config and config.get("access_token") == token:
            config["mailbox"] = mailbox
            save_config(config)
        result = {"mailbox": mailbox, "expiresAt": (config or {}).get("expires_at"), "apiBase": client.api_base, "session": "active"}
        if as_json:
            _emit_json(result)
        elif not quiet:
            render_status(console, mailbox, result["expiresAt"], client.api_base)
        return 0
    except NovaStackMailError as exc:
        if not quiet:
            render_status_error(console, str(exc), signed_in=True)
        return 1


def _inbox(api_base, timeout, page, per_page, as_json=False, quiet=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
    if not token:
        if not quiet:
            render_status_error(console, "No saved mailbox session was found on this device.")
        return 0
    mailbox_data = (config or {}).get("mailbox") or {}
    mailbox = mailbox_data.get("address", "your mailbox")
    try:
        client = _client_for(config, api_base, timeout)
        result = client.get_inbox_page(page, per_page)
        messages = sorted(result["messages"], key=lambda item: _date_key(item.get("date")), reverse=True)
        pagination = result.get("pagination") or {"page": page, "perPage": per_page, "total": len(messages), "totalPages": 1}
        payload = {"mailbox": mailbox, "messages": messages, "pagination": pagination}
        if as_json:
            _emit_json(payload)
        elif not quiet:
            render_inbox(console, mailbox, messages, pagination)
        return 0
    except NovaStackMailError as exc:
        if not quiet:
            render_status_error(console, str(exc), signed_in=True)
        return 1


def _date_key(value):
    from datetime import datetime
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _read(api_base, timeout, message_id, output=None, download=False, as_json=False, quiet=False, attachments_only=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
    if not token:
        if not quiet:
            render_status_error(console, "No saved mailbox session was found on this device.")
        return 0
    try:
        message = _client_for(config, api_base, timeout).read_message(message_id)
        if attachments_only:
            if as_json:
                _emit_json({"attachments": message.get("attachments") or []})
            elif not quiet:
                render_attachments(console, message)
            return 0
        if output or download:
            import re
            safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(message_id))[:80] or "message"
            target = Path(output or ("message-" + safe_id + ".txt")).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(message.get("text") or "", encoding="utf-8")
            if not quiet:
                console.print(f"[green]Message saved to {target}[/green]")
            return 0
        if as_json:
            _emit_json(message)
        elif not quiet:
            render_message(console, message)
        return 0
    except (NovaStackMailError, OSError) as exc:
        if not quiet:
            console.print(f"[red]{exc}[/red]")
        return 1


def _search(api_base, timeout, query, as_json=False, quiet=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
    if not token:
        if not quiet:
            render_status_error(console, "No saved mailbox session was found on this device.")
        return 0
    try:
        client = _client_for(config, api_base, timeout)
        first = client.get_inbox_page(1, 50)
        messages = list(first["messages"])
        pages = int((first.get("pagination") or {}).get("totalPages", 1))
        for page in range(2, min(pages, 2) + 1):
            messages.extend(client.get_inbox_page(page, 50)["messages"])
        needle = query.casefold()
        matches = [item for item in messages if needle in " ".join(
            str(item.get(key) or "") for key in ("from", "subject", "date")
        ).casefold()]
        matches.sort(key=lambda item: _date_key(item.get("date")), reverse=True)
        if as_json:
            _emit_json({"query": query, "count": len(matches), "messages": matches})
        elif not quiet:
            mailbox = ((config or {}).get("mailbox") or {}).get("address", "your mailbox")
            render_inbox(console, mailbox, matches, {"page": 1, "perPage": len(matches), "total": len(matches), "totalPages": 1})
        return 0
    except NovaStackMailError as exc:
        if not quiet:
            console.print(f"[red]{exc}[/red]")
        return 1


def _delete(api_base, timeout, message_id, as_json=False, quiet=False, yes=False):
    config = load_config()
    token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
    if not token:
        if not quiet:
            render_status_error(console, "No saved mailbox session was found on this device.")
        return 0
    if not yes and not Confirm.ask(
        f"[bold red]Permanently delete message {message_id}?[/bold red]", default=False
    ):
        if not quiet:
            console.print("[yellow]Message deletion cancelled.[/yellow]")
        return 0
    try:
        result = _client_for(config, api_base, timeout).delete_message(message_id)
        if as_json:
            _emit_json(result)
        elif not quiet:
            console.print(f"[green]Message {message_id} deleted.[/green]")
        return 0
    except NovaStackMailError as exc:
        if not quiet:
            console.print(f"[red]Delete failed: {exc}[/red]")
        return 1


def main():
    parser = argparse.ArgumentParser(prog="novastackmail", description="Official NovaStack Mail command-line client")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help=argparse.SUPPRESS)
    parser.add_argument("--config", nargs="?", const="show", help="Show the config file path, or set a custom config file path")
    parser.add_argument("--timeout", type=float, default=15, help="HTTP timeout in seconds (default: 15)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress decorative terminal output")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation for explicitly requested destructive actions")
    parser.add_argument("--output", help="Save a read message body to a file")
    parser.add_argument("--page", type=int, default=1, help="Inbox page number (default: 1)")
    parser.add_argument("--per-page", type=int, default=10, help="Messages per page (1-50; default: 10)")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.4")

    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--login", action="store_true", help="Sign in to your mailbox")
    actions.add_argument("--logout", action="store_true", help="Revoke this device's session")
    actions.add_argument("--status", action="store_true", help="Show mailbox and session status")
    actions.add_argument("--inbox", "--list-inbox", action="store_true", help="List a page of inbox messages")
    actions.add_argument("--refresh", action="store_true", help="Refresh the first inbox page")
    actions.add_argument("--read", metavar="MESSAGE_ID", help="Read a message")
    actions.add_argument("--search", metavar="QUERY", help="Search sender, subject, and date")
    actions.add_argument("--attachments", metavar="MESSAGE_ID", help="List attachments for a message")
    actions.add_argument("--download", metavar="MESSAGE_ID", help="Save a message's plain-text body to a file")
    actions.add_argument("--download-attachment", nargs=2, metavar=("MESSAGE_ID", "ATTACHMENT_ID"), help="Download one message attachment")
    actions.add_argument("--delete", metavar="MESSAGE_ID", help="Delete a message after confirmation")
    actions.add_argument("--mark-read", metavar="MESSAGE_ID", help="Mark a message as read")
    actions.add_argument("--mark-unread", metavar="MESSAGE_ID", help="Mark a message as unread")

    subparsers = parser.add_subparsers(dest="command")
    account_parser = subparsers.add_parser("account", help="Manage saved mailbox profiles")
    account_actions = account_parser.add_subparsers(dest="account_action", required=True)
    add_parser = account_actions.add_parser("add", help="Add a mailbox profile")
    add_parser.add_argument("name", help="Profile name (letters, numbers, hyphens, underscores)")
    account_actions.add_parser("list", help="List saved mailbox profiles")
    use_parser = account_actions.add_parser("use", help="Switch the active mailbox profile")
    use_parser.add_argument("name")
    remove_parser = account_actions.add_parser("remove", help="Remove a saved mailbox profile")
    remove_parser.add_argument("name")
    args = parser.parse_args()

    if args.config:
        if args.config.lower() in ("show", "true"):
            print(config_path())
            return 0
        os.environ["NOVASTACKMAIL_CONFIG"] = str(Path(args.config).expanduser())
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.page < 1 or not 1 <= args.per_page <= 50:
        parser.error("--page must be positive and --per-page must be between 1 and 50")

    if args.command == "account":
        config = load_config() or {"profiles": {}, "active_profile": None}
        profiles = config.setdefault("profiles", {})
        if args.account_action == "list":
            items = [{"name": name, "address": (item.get("mailbox") or {}).get("address", "Unknown"),
                      "active": name == config.get("active_profile")} for name, item in profiles.items()]
            if args.json:
                _emit_json({"profiles": items, "activeProfile": config.get("active_profile")})
            elif not args.quiet:
                if not items:
                    console.print("[yellow]No saved profiles. Use: novastackmail account add NAME[/yellow]")
                for item in items:
                    marker = "[green]*[/green]" if item["active"] else " "
                    console.print(f"{marker} [bold]{item['name']}[/bold]  {item['address']}")
            return 0
        if args.account_action == "use":
            if args.name not in profiles:
                console.print(f"[red]Profile '{args.name}' does not exist.[/red]")
                return 1
            config["active_profile"] = args.name
            save_config(config)
            if not args.quiet: console.print(f"[green]Active mailbox profile: {args.name}[/green]")
            return 0
        if args.account_action == "remove":
            if args.name not in profiles:
                console.print(f"[red]Profile '{args.name}' does not exist.[/red]")
                return 1
            profile = profiles[args.name]
            mailbox = (profile.get("mailbox") or {}).get("address", args.name)
            if not args.yes and not Confirm.ask(f"[yellow]Remove profile {args.name} ({mailbox}) and revoke its device token?[/yellow]", default=False):
                console.print("[yellow]Profile removal cancelled.[/yellow]")
                return 0
            try:
                NovaStackMailClient(api_base=profile.get("api_base") or args.api_base, timeout=args.timeout).logout(profile["access_token"])
            except NovaStackMailError as exc:
                console.print(f"[red]Could not revoke profile token; profile was kept: {exc}[/red]")
                return 1
            profiles.pop(args.name, None)
            if config.get("active_profile") == args.name:
                config["active_profile"] = next(iter(profiles), None)
            save_config(config)
            if not args.quiet: console.print(f"[green]Profile '{args.name}' removed.[/green]")
            return 0
        if args.account_action == "add":
            if not validate_profile_name(args.name):
                console.print("[red]Profile name must be 1–32 letters, numbers, hyphens, or underscores, and start with a letter or number.[/red]")
                return 2
            if args.name in profiles:
                console.print(f"[red]Profile '{args.name}' already exists. Use account use or remove first.[/red]")
                return 2
            address = Prompt.ask("[cyan]Mailbox address[/cyan]").strip()
            password = getpass.getpass("Mailbox password: ")
            if not address or not password:
                console.print("[red]Mailbox address and password are required.[/red]")
                return 2
            try:
                client = NovaStackMailClient(api_base=args.api_base, timeout=args.timeout)
                result = client.login(address, password)
                profiles[args.name] = {
                    "api_base": args.api_base.rstrip("/"),
                    "access_token": result["accessToken"],
                    "expires_at": result.get("expiresAt"),
                    "mailbox": result.get("mailbox") or {},
                }
                if not config.get("active_profile"):
                    config["active_profile"] = args.name
                save_config(config)
                if not args.quiet: render_login_success(console, (result.get("mailbox") or {}).get("address", address), result.get("expiresAt", "not provided"))
                return 0
            except NovaStackMailError as exc:
                console.print(f"[red]Could not add profile: {exc}[/red]")
                return 1

    if args.mark_read or args.mark_unread:
        message_id = args.mark_read or args.mark_unread
        is_read = bool(args.mark_read)
        config = load_config()
        token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or active_profile(config).get("access_token")
        if not token:
            if not args.quiet: render_status_error(console, "No saved mailbox session was found on this device.")
            return 1
        try:
            result = _client_for(config, args.api_base, args.timeout).set_message_read(message_id, is_read)
            if args.json: _emit_json(result)
            elif not args.quiet:
                state = "read" if is_read else "unread"
                console.print(f"[green]Message {message_id} marked as {state} in NovaStack.[/green]")
            return 0
        except NovaStackMailError as exc:
            if not args.quiet: console.print(f"[red]Could not update message status: {exc}[/red]")
            return 1

    if args.status:
        if not args.quiet and not args.json: render_header(console)
        return _status(args.api_base, args.timeout, args.json, args.quiet)
    if args.inbox or args.refresh:
        if not args.quiet and not args.json: render_header(console)
        return _inbox(args.api_base, args.timeout, 1 if args.refresh else args.page, args.per_page, args.json, args.quiet)
    if args.read:
        if not args.quiet and not args.json: render_header(console)
        return _read(args.api_base, args.timeout, args.read, args.output, as_json=args.json, quiet=args.quiet)
    if args.attachments:
        if not args.quiet and not args.json: render_header(console)
        return _read(args.api_base, args.timeout, args.attachments, as_json=args.json, quiet=args.quiet, attachments_only=True)
    if args.download_attachment:
        config = load_config()
        token = os.environ.get("NOVASTACKMAIL_ACCESS_TOKEN") or (config or {}).get("access_token")
        if not token:
            if not args.quiet: render_status_error(console, "No saved mailbox session was found on this device.")
            return 0
        message_id, attachment_id = args.download_attachment
        try:
            data, disposition = _client_for(config, args.api_base, args.timeout).download_attachment(message_id, attachment_id)
            filename = "attachment-" + str(attachment_id)
            import re
            match = re.search(r'filename="([^"]+)"', disposition)
            if match:
                filename = match.group(1)
            filename = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(filename.replace("\\", "/")).name)
            if filename in ("", ".", ".."):
                filename = "attachment-" + str(attachment_id)
            target = Path(args.output or filename).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if not args.quiet:
                console.print(f"[green]Attachment saved to {target}[/green]")
            return 0
        except (NovaStackMailError, OSError) as exc:
            if not args.quiet:
                console.print(f"[red]{exc}[/red]")
            return 1
    if args.download:
        if not args.quiet and not args.json: render_header(console)
        return _read(args.api_base, args.timeout, args.download, args.output, download=True, quiet=args.quiet)
    if args.search:
        if not args.quiet and not args.json: render_header(console)
        return _search(args.api_base, args.timeout, args.search, args.json, args.quiet)
    if args.delete:
        if not args.quiet and not args.json: render_header(console)
        return _delete(args.api_base, args.timeout, args.delete, args.json, args.quiet, args.yes)
    if args.logout:
        if not args.quiet: render_header(console)
        return _logout(args.api_base, args.timeout, args.quiet)

    if not args.login:
        if args.config is None:
            parser.print_help()
        return 0

    if not args.quiet: render_header(console)
    console.print("\n[bold]Sign in to your mailbox[/bold]")
    console.print("[dim]Use your NovaStack Mail address and mailbox password.[/dim]\n")
    try:
        address = Prompt.ask("[cyan]Mailbox address[/cyan]").strip()
        if not address:
            console.print("[red]Mailbox address is required.[/red]")
            return 2
        password = getpass.getpass("Mailbox password: ")
        if not password:
            console.print("[red]Mailbox password is required.[/red]")
            return 2
        with console.status("[cyan]Authenticating with NovaStack Mail…[/cyan]", spinner="dots"):
            client = NovaStackMailClient(api_base=args.api_base, timeout=args.timeout)
            result = client.login(address, password)
        config = load_config() or {"profiles": {}, "active_profile": None}
        profiles = config.setdefault("profiles", {})
        profile_name = config.get("active_profile") or "default"
        profiles[profile_name] = {
            "api_base": args.api_base.rstrip("/"),
            "access_token": result["accessToken"],
            "expires_at": result.get("expiresAt"),
            "mailbox": result.get("mailbox") or {},
        }
        config["active_profile"] = profile_name
        save_config(config)
        mailbox = result.get("mailbox") or {}
        if not args.quiet:
            render_login_success(console, mailbox.get("address", address), result.get("expiresAt", "not provided"))
        return 0
    except NovaStackMailError as exc:
        console.print(Panel(f"[bold red]Login failed[/bold red]\n{exc}", border_style="red", title="[red]AUTHENTICATION ERROR[/red]"))
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Login cancelled.[/yellow]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
