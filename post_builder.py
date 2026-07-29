import base64
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

# Comprehensive Cyrillic to Latin transliteration mapping
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'yo',
    'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'y', 'К': 'k', 'Л': 'l', 'М': 'm',
    'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
    'Ф': 'f', 'Х': 'kh', 'Ц': 'ts', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'shch',
    'Ъ': '', 'Ы': 'y', 'Ь': '', 'Э': 'e', 'Ю': 'yu', 'Я': 'ya',
    'є': 'ye', 'Є': 'ye', 'і': 'i', 'І': 'i', 'ї': 'yi', 'Ї': 'yi', 'ґ': 'g', 'Ґ': 'g'
}


def slugify(text: str) -> str:
    """
    Transliterates Cyrillic characters and normalizes string to a clean URL slug.
    """
    if not text:
        return f"post-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')}"

    # Remove leading header markers if present
    text = re.sub(r'^\s*#+\s*', '', text)

    # Transliterate Cyrillic characters
    chars = []
    for char in text:
        chars.append(TRANSLIT_MAP.get(char, char))
    transliterated = "".join(chars).lower()

    # Replace invalid chars with hyphen
    cleaned = re.sub(r'[^a-z0-9]+', '-', transliterated)
    # Collapse consecutive hyphens and strip edges
    slug = re.sub(r'-+', '-', cleaned).strip('-')

    if not slug:
        slug = f"post-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')}"

    return slug


def parse_message_text(raw_text: str) -> Tuple[str, str, str]:
    """
    Parses full message text into (title, body, description).
    - Line 1: Title
    - Line 2+: Body
    - Description: Auto-trimmed first 150 chars of body.
    """
    raw_text = raw_text.strip() if raw_text else ""
    if not raw_text:
        title = "Untitled Post"
        body = ""
    else:
        lines = raw_text.splitlines()
        title = lines[0].strip()
        # Remove markdown heading '#' if provided
        title = re.sub(r'^\s*#+\s*', '', title)
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    # Generate a clean description (first 150 chars without newlines)
    desc_clean = re.sub(r'\s+', ' ', body).strip()
    if len(desc_clean) > 150:
        description = desc_clean[:147].rstrip() + "..."
    elif desc_clean:
        description = desc_clean
    else:
        description = title

    return title, body, description


def build_post_files_payload(
    title: str,
    body: str,
    description: str,
    attachments: List[Dict[str, Any]] = None,
    post_date: str = None,
) -> Tuple[List[Dict[str, str]], str, str]:
    """
    Builds the array of files for Forgejo ChangeFilesOptions API based on .env layout settings.
    
    Returns: (files_payload, slug, markdown_content)
    """
    attachments = attachments or []
    slug = slugify(title)
    if not post_date:
        post_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    post_format = os.getenv("BLOG_POST_FORMAT", "single_file").lower()
    content_path = os.getenv("BLOG_CONTENT_PATH", "src/content/blog").strip("/")
    images_path = os.getenv("BLOG_IMAGES_PATH", "public/images").strip("/")
    url_prefix = os.getenv("BLOG_IMAGE_URL_PREFIX", "/images").rstrip("/")

    files_payload = []
    markdown_images = []

    # Process attachments
    for idx, att in enumerate(attachments):
        filename = att.get("filename") or f"image_{idx+1}.jpg"
        file_bytes = att.get("bytes") or b""
        base64_data = base64.b64encode(file_bytes).decode("utf-8")

        if post_format == "folder":
            # Folder-per-post layout (Astro Nano style)
            repo_file_path = f"{content_path}/{slug}/{filename}"
            img_md_url = f"./{filename}"
        else:
            # Single file layout (gluek.info style)
            repo_file_path = f"{images_path}/{slug}/{filename}"
            img_md_url = f"{url_prefix}/{slug}/{filename}"

        files_payload.append({
            "operation": "create",
            "path": repo_file_path,
            "content": base64_data,
        })
        markdown_images.append(f"![{filename}]({img_md_url})")

    # Combine body with image markdown tags if present
    full_body = body
    if markdown_images:
        images_section = "\n\n" + "\n\n".join(markdown_images)
        full_body = (full_body + images_section).strip()

    # Escape quotes in title & description for YAML
    yaml_title = title.replace('"', '\\"')
    yaml_desc = description.replace('"', '\\"')

    # Construct Frontmatter
    frontmatter = (
        f"---\n"
        f'title: "{yaml_title}"\n'
        f'description: "{yaml_desc}"\n'
        f'date: "{post_date}"\n'
        f"---\n\n"
    )

    full_markdown = frontmatter + full_body + "\n"
    md_base64 = base64.b64encode(full_markdown.encode("utf-8")).decode("utf-8")

    # Determine post Markdown target path
    if post_format == "folder":
        post_target_path = f"{content_path}/{slug}/index.md"
    else:
        post_target_path = f"{content_path}/{slug}.md"

    files_payload.insert(0, {
        "operation": "create",
        "path": post_target_path,
        "content": md_base64,
    })

    return files_payload, slug, full_markdown
