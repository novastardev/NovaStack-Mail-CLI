# NovaStack Mail CLI

Official Python command-line client for permanent NovaStack Mail mailboxes.

## Install

```bash
python -m pip install --upgrade novastackmailcli
```

The distribution is named `novastackmailcli`; the installed terminal command remains `novastackmail`.

For the latest unreleased development version, install directly from GitHub:

```bash
python -m pip install --upgrade --no-cache-dir "git+https://github.com/novastardev/NovaStack-Mail-CLI.git"
```

## Authentication and session

```bash
novastackmail --login
novastackmail --status
novastackmail --logout

# Additional mailbox profiles
novastackmail account add work
novastackmail account list
novastackmail account use default
novastackmail account remove work
```

Login asks for the mailbox address and mailbox password. The password is never saved. The returned access token is stored in `~/.config/novastackmail/config.json` with owner-only permissions on POSIX systems. The original single-session config is migrated automatically to a `default` profile on first load. Logout revokes and removes only the active profile; other saved profiles remain available.

For automation, set `NOVASTACKMAIL_ACCESS_TOKEN`. It overrides the locally saved token and is never printed by status/config output.

## Inbox and messages

```bash
novastackmail --inbox
novastackmail --inbox --page 2
novastackmail --inbox --page 2 --per-page 20
novastackmail --refresh
novastackmail --search "deployment"
novastackmail --read MESSAGE_ID
novastackmail --attachments MESSAGE_ID
novastackmail --download MESSAGE_ID
novastackmail --download-attachment MESSAGE_ID ATTACHMENT_ID
novastackmail --delete MESSAGE_ID
novastackmail --delete MESSAGE_ID --yes
novastackmail --delete MESSAGE_ID --json --yes
novastackmail --mark-read MESSAGE_ID
novastackmail --mark-unread MESSAGE_ID
```

Inbox defaults to 10 messages per page and sorts newest first. Use `--page` to navigate and `--per-page` to choose 1–50 messages. Each row displays the original provider MESSAGE ID, which is used directly by `--read`, `--delete`, and attachment commands, plus Read/Unread status. The API enforces the mailbox's configured message limit, up to 100 messages for this CLI endpoint.

Search checks sender, subject, and date across the available inbox window (up to 100 messages). Reading a message displays its plain-text body and attachment list. `--download MESSAGE_ID` saves the message's plain-text body; `--download-attachment MESSAGE_ID ATTACHMENT_ID` downloads an individual attachment when the upstream provider supplies a supported download URL. Deletion always asks for confirmation. Read/unread commands persist status in NovaStack and the CLI inbox keeps that status across refreshes. This status is currently NovaStack-side; the upstream provider has no documented status mutation endpoint, so it does not change the provider webmail status.

### Mailbox limits and plan upgrades

The CLI uses the mailbox's server-side message limit; it does not maintain a separate local quota. Manage your mailbox and eligible plan upgrades from the NovaStack dashboard. The current CLI inbox API caps the returned window at 100 messages even if a mailbox is configured with a higher limit, so larger-tier CLI access requires the API cap to be raised as part of the plan integration. The CLI cannot upgrade a plan or change billing limits itself.

## Automation and output

```bash
novastackmail --inbox --json
novastackmail --read MESSAGE_ID --json
novastackmail --status --json
novastackmail --inbox --quiet
novastackmail --read MESSAGE_ID --output ./message.txt
novastackmail --download-attachment MESSAGE_ID ATTACHMENT_ID --output ./file.bin
novastackmail --timeout 30 --status
novastackmail --config
novastackmail --version
novastackmail --help
```

- `--json`: machine-readable JSON output for status, inbox, search, read, attachments, delete, mark-read, mark-unread, and account list (place global flags before `account`).
- `account add NAME`: sign in and save another mailbox profile. `account list` lists profiles, `account use NAME` switches, and `account remove NAME` revokes and removes one profile.
- `--quiet`: suppress decorative output; destructive actions still require confirmation.
- `--yes`: explicitly bypass the delete confirmation for scripts.
- `--output PATH`: choose the saved message/attachment file path.
- `--timeout SECONDS`: set the HTTP request timeout (default 15).
- `--config`: show the config file path. `--config PATH` selects a custom path.
- `--version`, `--help`: display CLI version and usage.

Exit codes: `0` success, `1` API/operation failure, `2` invalid interactive login input, and `130` interrupted login.

## Development

From this directory:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Set `NOVASTACKMAIL_CONFIG` to override the configuration file location.
