# Changelog

All notable changes to the `deltachat_publish` project will be documented in this file.

## [1.4.0] - 2026-10-28

### Changed
- **Delta Chat Core 2.66.0**: `deltachat-rpc-server` is pinned to 2.66.0 (was 2.65.0). Core 2.66 removes the `configured_addr` config: `get_config("configured_addr")` now fails with "unknown key", and `addr` has been empty since core 2.61. The bot's own address now comes from its self contact (`dc_fingerprint.get_self_addr()`), which the core fills from the primary relay; this also works on older cores.

## [1.3.1] - 2026-10-28

### Changed
- **Fingerprint Lookup Ready for Core 2.66**: The contact's key block was picked by its address in the header, which core 2.66 no longer prints. It is now the one block that is not the bot's own key, recognised by the fingerprint in the bot's invite link (`dc_fingerprint.py`, shared between the bots).
- **Core Pinned to 2.65.0**: `deltachat-rpc-server` was `>=2.62.0`, so any image rebuild pulled core 2.66.0, which removes the `configured_addr` option the bot still reads. Core upgrades are now made on purpose, after reading the core changelog.

## [1.3.0] - 2026-10-24

### Added
- **Automatic Account Creation**: `bot.py serve` without a configured account now creates one by itself, so a new bot needs no `init` step. Without `RELAY` or `ADDR`/`MAIL_PW` in the environment the Delta Chat core (2.62+, `init_transports`) probes its built-in chatmail relay list, configures the fastest relay and later adds further relays in the background; `RELAY` and `ADDR`/`MAIL_PW` are still used when set (`RELAY` no longer defaults to `chatmail.uk`). A failure is logged and `serve` exits, so the container restart retries. Account setup now runs only for `serve`: before, any command (also `bot.py init <addr> <password>`) first configured a `chatmail.uk` account. `bot.py init <addr> <password>` and `bot.py init DCACCOUNT:server.tld` keep working and take precedence. Unit tests in `tests/test_auto_account.py` (mocked RPC).

### Changed
- **The server runs releases, not the tip of `main`.** `update.sh` deploys the newest `vX.Y.Z` tag, so a merge into `main` reaches the server only once it is released; several PRs can go out together. `UPDATE_REF` in `.env.local` pins a release (`UPDATE_REF=v1.2.2` - a rollback; empty again = newest) or follows a branch as before (`UPDATE_REF=main`). A release tag moved on GitHub or Forgejo makes the update fail instead of deploying the changed code. Errors that stopped the script with a message (both remotes unreachable, an unknown `UPDATE_REF`) now also ping the healthcheck's `/fail`, not only failed commands. The script now runs as one function, so the `git reset` that rewrites `update.sh` cannot confuse the running copy.
- **Releases are published by a tag** (new `.github/workflows/release.yml`): pushing `vX.Y.Z` checks that `bot.py` has that version, creates the GitHub release with the version's section of this file as its notes (an existing release is left alone), then sends the ntfy notification and the `bot-updated` dispatch to `hass-addons-deltachat` (now with `"version"` in the payload). Both used to go out on every push to `main` (`publish-changelog.yml`, removed), so Home Assistant users got unreleased code.
- **README**: the "Configure Email and Admin" step is optional; added the update and release notes.
- Releasing: merge, then `git tag -a vX.Y.Z -m "..." <commit> && git push origin vX.Y.Z`.
- **Upgrading:** tag `v1.3.0` right after merging this. Until then the new `update.sh` would deploy `v1.2.2`, which still has the old script that follows `main` - and the server would switch back and forth on every run.

## [1.2.2] - 2026-10-21

### Fixed
- **Admin Lost Access After Adding a Relay**: The bot read the sender's fingerprint from a `fingerprint` field that the JSON-RPC `Contact` object does not have, so the fingerprint was always empty and the admin was recognised by email address only. Since core 2.61 the client sends from its newest relay, so after the admin added a relay their address changed and publishing was denied. The fingerprint is now read from `get_contact_encryption_info()`, and when an admin fingerprint is configured only the key is checked, whatever address the message comes from. The address is checked only when no fingerprint is configured.

## [1.2.1] - 2026-10-16
- **MIT License**: the project is now licensed under MIT (`LICENSE`).

## [1.2.0] - 2026-10-14
- **`/transports` Shows the Relay Actually Used for Sending**: Since core 2.61 the core sends through the relay that last worked and switches only when it cannot connect, so the main address (`configured_addr`) says nothing about where mail goes out. `/transports` now lists relays in the order the core tries them, with the current sending relay first, shows the core's send queue (waiting messages and retries) and outgoing status, and per relay the incoming status, when the last message arrived, mailbox storage usage (⚠️ from 80%) and when it was added. The sending order and queue are read from the core's account database (read-only); the report is built by the shared `transports_view.py`.
- **Removed Misleading Per-Relay Sent/Received Counters**: They credited every message to `configured_addr` (or, in some places, the wrong address), so the numbers and "last sent" dates were wrong once the core sent through another relay. Counting them also cost extra RPC calls per message. The `transport_stats` table is left in place but no longer updated.
- **`/stats` No Longer Lists Transport Counters**: it points to `/transports` instead. The received counter was keyed by the sender's address, not a relay.

## [1.1.0] - 2026-09-28

### Removed
- **Resilient Sending Mode**: Removed the resilient-send `send_msg` patch. It switched `configured_addr` and called `resend_messages`, but since Delta Chat core 2.61 the SMTP relay is no longer chosen by `configured_addr`: the core tries the newest relay first and falls back to the next one if a relay is unreachable. The patch could no longer switch relays and only produced duplicate resends.

### Changed
- **`/setprimary` and `/resilient` Deprecated**: Both commands are disabled and only reply with an explanation of how the core picks relays now. They are removed from `/help`.
- **`/transports` Sending Order**: Relays are listed newest first, in the order the core tries them for sending, instead of marking `configured_addr` as "Used for sending".
- **Core Requirement**: `requirements.txt` now requires `deltachat-rpc-server>=2.62.0`.

## [1.0.5] - 2026-09-24

### Fixed
- **`update.sh` Deployed the Wrong Branch**: Branch detection took the first remote branch in alphabetical order, so a leftover PR branch such as `origin/claude/...` sorted before `origin/master` and was deployed instead (and new `master` commits were reported as "Already up to date"). It now follows the checked-out branch, falling back to `main`/`master`.

## [1.0.4] - 2026-09-16

### Security
- **SSRF Protection in Forgejo Client**: Added URL validation (`is_safe_url`) in `ForgejoClient.commit_files` and `ForgejoClient.check_connection` with DNS resolution to block loopback, private, link-local, multicast, and cloud metadata IP ranges (`169.254.169.254`, `127.0.0.0/8`, etc.), plus `.local`, `.internal`, and `.lan` domains.
- **Bounded Response Reads**: Enforced read byte limits on Forgejo API responses (10 MB for commits, 64 KB for errors and connectivity checks) to prevent memory exhaustion.
- **Dependency Pinning**: Pinned dependencies to secure version bounds in `requirements.txt` (`deltabot-cli>=8.1.2,<9.0.0`, `aiohttp>=3.10.11,<4.0.0`, `qrcode>=7.4.2,<8.0.0`).

## [1.0.3] - 2026-09-09

### Added
- **Private Chat Enforcement**: Enforce private 1:1 chat for `/addtransport` and `/initadmin` to prevent credential exposure in group chats.
- **Resilient Transport Sending**: Integrated `_setup_resilient_mode` with concurrency lock and automatic fallback transport resending.
- **Automated Retention & Pruning**: Periodic background cleanup task in `on_start` for database records and transport statistics.
- **Transport Command Unit Tests**: Added `tests/test_transport_commands.py` covering private chat constraints, resilient mode toggle, and error sanitization.

### Fixed
- **Transport Command Error Sanitization**: Sanitized error output in `/transports`, `/addtransport`, `/rmtransport`, `/setprimary`, and `/resilient`.

### Changed
- **SQLite Performance Optimization**: Enabled WAL mode (`journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`) and in-memory buffered transport statistics.

## [1.0.2] - 2026-09-07

### Added
- **Options.json Fallback for Display Name & Status Text**:
  - `on_init` now checks `/data/options.json` fallback when `DISPLAY_NAME` or `STATUS_TEXT` are not set in environment variables.

## [1.0.1] - 2026-07-30

### Added
- **Profile Metadata Customization (`.env`):** Added support for `DISPLAY_NAME`, `STATUS_TEXT`, and `AVATAR_PATH` environment variables to easily set bot profile details.
- **Terminal ASCII QR Code Display:** Output securejoin QR code and invite URI in container logs on startup for easy contact scanning.
- **Auto Account Setup (`on_init`):** Automated bot account initialization and transport configuration (`RELAY` or `ADDR`/`MAIL_PW`).

### Fixed
- **Synchronous Event Handler:** Converted `on_new_message` to a synchronous callback to eliminate `RuntimeWarning: coroutine 'on_new_message' was never awaited`.
- **Dependency Pinning:** Pinned `deltachat2[full]<1.0.0` and `deltabot-cli>=8.1.2` in `requirements.txt`.
- **Command CLI Entry Point:** Fixed `BotCli` entry point to `dc_cli.start()` and event decorator to `@dc_cli.on(...)`.
- **Script Executable Permission:** Made `update.sh` executable (`chmod +x update.sh`).
- **Docker Compose Cleanup:** Removed obsolete `version:` attribute and unused port 8080 mapping.

## [1.0.0] - 2026-07-29

### Added
- Initial release of `deltachat_publish` Delta Chat bot.
- Single-commit multi-file publishing via Forgejo REST API `ChangeFilesOptions`.
- Automatic Russian title transliteration to URL slugs (`post_builder.py`).
- Flexible Astro blog layout support: `single_file` (`gluek.info`) and `folder` (`Astro Nano`).
- Automatic Frontmatter generation (`title`, `description`, `date`).
- Support for attached photos with automatic Markdown image link insertion.
- Admin ownership claim (`/initadmin`), authorization verification, and set_admin.py CLI tool.
- Standard commands: `/help`, `/donate`, `/status`, `/list`, `/stats`, `/transports`.
- SQLite database storage with thread locking (`database.py`).
- Docker containerization (`Dockerfile`, `docker-compose.yml`, `Caddyfile`).
- Healthchecks pings and backup remote fallback in `update.sh`.
- Comprehensive unit test suite (`tests/test_publish.py`) and GitHub Actions CI workflow.
