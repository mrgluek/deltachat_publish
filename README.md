# Delta Chat Publish Bot (`deltachat_publish`)

`deltachat_publish` is a Delta Chat bot designed to publish new posts and attached image assets directly to an Astro blog (`gluek.info` or any Astro theme like Astro Nano) via Forgejo / Gitea REST API.

Following **IndieWeb / POSSE** principles, your Git repository remains the single source of truth.

---

## 🌟 Key Features

- **Single-Commit Multi-File API Publishing**: Uses Forgejo `ChangeFilesOptions` REST API to create both the post Markdown file (`.md`) and attached images in a **single API request / single Git commit**.
- **100% CI/CD Efficient**: Triggers Forgejo Actions build pipeline only **once** per post creation.
- **Flexible Astro Layout Support**:
  - `single_file` layout (`gluek.info`): Post in `src/content/blog/<slug>.md`, images in `public/images/<slug>/`.
  - `folder` layout (`Astro Nano`): Post in `src/content/blog/<slug>/index.md`, images alongside in `src/content/blog/<slug>/`.
- **Automatic Slugification**: Transliterates Russian titles to clean URL slugs (e.g. `Мой новый пост` → `moy-novyy-post`).
- **Standard Delta Chat Bot Architecture**: Fully supports `/help`, `/initadmin`, `/donate`, `/status`, `/list`, `/stats`, `/transports`, SQLite state storage, and thread locking.
- **Multiple Mail Relays**: Relay selection and failover are handled by the Delta Chat core (2.61+): it sends via the newest relay first and falls back to the next one if a relay is unreachable. The former `/setprimary` and `/resilient` commands are deprecated and only reply with this explanation.

---

## 🔒 Security & Encryption Architecture

- **End-to-End Encryption (E2EE)**: All communication between the Delta Chat client and the bot is fully encrypted using OpenPGP / Autocrypt over Chatmail.
- **Key-Based Admin Verification**: The sender's OpenPGP key fingerprint (read from the core's encryption info) is checked against the admin fingerprint set via `/initadmin`, `set_admin.py` or `ADMIN_DC_FINGERPRINT`. When a fingerprint is configured, only the key counts, so the admin keeps access whichever relay their client sends from; the email address is checked only if no fingerprint is configured. Unauthorized publish attempts are immediately rejected (`⛔ Access Denied`).
- **Protected API Credentials**: Forgejo API personal access tokens (`FORGEJO_TOKEN`) are strictly isolated inside server environment variables (`.env`) and never exposed over chat or client logs.

---

## 🚀 How to Publish a Post

Simply send a chat message to your bot:

```text
Title of Your Post

This is the body of the post in Markdown format.
You can write multiple paragraphs.

[Attach photo(s) or file(s)]
```

The bot will:
1. Extract Title from Line 1.
2. Transliterate Title into a clean URL slug.
3. Automatically trim the first 150 characters of the body for the YAML `description`.
4. Upload all attached photos and insert Markdown image tags `![filename](path)` automatically.
5. Create a single commit via Forgejo API and reply with success confirmation & commit link.

---

## ⚙️ Setup & Deployment

### 1. Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in credentials:

```ini
# Forgejo / Gitea REST API Settings
FORGEJO_URL=https://git.gluek.info
FORGEJO_TOKEN=your_forgejo_token_here
FORGEJO_REPO_OWNER=gluek
FORGEJO_REPO_NAME=gluek.info
FORGEJO_BRANCH=main

# Blog Layout Format (single_file or folder)
BLOG_POST_FORMAT=single_file
BLOG_CONTENT_PATH=src/content/blog
BLOG_IMAGES_PATH=public/images
BLOG_IMAGE_URL_PREFIX=/images

# Admin Access Control
ADMIN_DC_EMAIL=gluek@gluek.info
```

### 2. Configure Email and Admin (Optional)
Skip this step and the bot creates its account by itself at first start: the Delta Chat core (2.62+) picks the fastest chatmail relay from its built-in list and later adds further relays in the background. `RELAY` or `ADDR`/`MAIL_PW` in `.env` are still used for that first account when set.

To choose the account yourself, initialize it with your email and password, or with `DCACCOUNT:server.tld` for an account on a specific chatmail relay:
```bash
docker compose run --rm deltachat_publish python bot.py init publishbot@yourdomain.com "your_email_password"
docker compose run --rm deltachat_publish python bot.py init DCACCOUNT:server.tld
```

Configure your admin email address and your cryptographic fingerprint on the server (or do it later inside the bot chat with the `/initadmin` command, see step 4):
```bash
docker compose run --rm deltachat_publish python set_admin.py --email admin@yourdomain.com
docker compose run --rm deltachat_publish python set_admin.py --fingerprint 1234ABCD1234ABCD1234ABCD1234ABCD1234ABCD
```

### 3. Docker Compose Deployment

```bash
docker compose up -d --build
```

The bot's invite QR code and link are printed in the logs (`docker compose logs deltachat_publish`).

### 4. Claim Administrator Ownership

In private chat with the bot, send:
```text
/initadmin
```
This binds your email address and key fingerprint to the bot. Once a fingerprint is bound, you stay the admin even if your client starts sending from another relay address.

### 5. Updates

Run `./update.sh` (e.g. from cron) to deploy the newest release: the highest `vX.Y.Z` tag, from GitHub or, when GitHub is unreachable, from the Forgejo mirror; `-f` rebuilds the container without changes. Commits on `main` that are not released yet are not deployed. In `.env.local`, `UPDATE_REF=v1.2.2` stays on that release (to roll back; remove it to follow new releases again), `UPDATE_REF=main` follows the branch, and `MONITOR_URL` (in `.env` or `.env.local`) pings a healthcheck on start, success and failure. Pushing a `vX.Y.Z` tag publishes the GitHub release with that version's `CHANGELOG.md` section.

Releasing: merge, then `git tag -a vX.Y.Z -m "..." <commit> && git push origin vX.Y.Z`.

---

## 🧪 Running Unit Tests

```bash
python3 -m unittest discover -s tests
```

## License

MIT, see [LICENSE](LICENSE).
