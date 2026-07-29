# Changelog

All notable changes to the `deltachat_publish` project will be documented in this file.

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
