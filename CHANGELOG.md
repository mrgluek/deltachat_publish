# Changelog

All notable changes to the `deltachat_publish` project will be documented in this file.

## [1.0.1] - 2026-07-30

### Added
- **Terminal ASCII QR Code Display:** Output securejoin QR code and invite URI in container logs on startup for easy contact scanning.
- **Auto Account Setup (`on_init`):** Automated bot account initialization and transport configuration (`RELAY` or `ADDR`/`MAIL_PW`).

### Fixed
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
