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

---

## 🔒 Security & Encryption Architecture

- **End-to-End Encryption (E2EE)**: All communication between the Delta Chat client and the bot is fully encrypted using OpenPGP / Autocrypt over Chatmail.
- **Cryptographic Fingerprint & Email Verification**: The bot strictly verifies the sender's email AND cryptographic OpenPGP fingerprint against `database.is_authorized_sender(...)` initialized via `/initadmin` or `set_admin.py`. Unauthorized publish attempts are immediately rejected (`⛔ Access Denied`).
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

### 2. Docker Compose Deployment

```bash
docker compose up -d --build
```

### 3. Claim Administrator Ownership

In private chat with the bot, send:
```text
/initadmin
```
This binds your email address and cryptographic fingerprint to the bot.

---

## 🧪 Running Unit Tests

```bash
python3 -m unittest discover -s tests
```
