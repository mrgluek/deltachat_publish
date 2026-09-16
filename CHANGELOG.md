# Changelog

All notable changes to the `deltachat_publish` project will be documented in this file.

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
