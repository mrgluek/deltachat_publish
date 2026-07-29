import base64
import os
import sys
import unittest
from unittest.mock import patch

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from post_builder import slugify, parse_message_text, build_post_files_payload
import database


class TestPublishBot(unittest.TestCase):
    def setUp(self):
        os.environ["DB_PATH"] = ":memory:"
        database.init_db()

    def test_slugify_russian_text(self):
        title = "Мой новый пост в блоге 2026!"
        slug = slugify(title)
        self.assertEqual(slug, "moy-novyy-post-v-bloge-2026")

    def test_slugify_with_markdown_header(self):
        title = "###  Заголовок с решетками!!! "
        slug = slugify(title)
        self.assertEqual(slug, "zagolovok-s-reshetkami")

    def test_slugify_fallback(self):
        slug = slugify("!!! ???")
        self.assertTrue(slug.startswith("post-"))

    def test_parse_message_text(self):
        raw = "My Great Title\nThis is line 1 of the body.\nThis is line 2 of the body."
        title, body, desc = parse_message_text(raw)
        self.assertEqual(title, "My Great Title")
        self.assertIn("line 1", body)
        self.assertEqual(desc, "This is line 1 of the body. This is line 2 of the body.")

    def test_build_post_files_payload_single_file(self):
        with patch.dict(os.environ, {"BLOG_POST_FORMAT": "single_file"}):
            attachments = [{"filename": "photo.jpg", "bytes": b"fake_image_bytes"}]
            files, slug, md = build_post_files_payload(
                title="Test Post Title",
                body="Body paragraph.",
                description="Short desc.",
                attachments=attachments,
                post_date="2026-07-29"
            )
            self.assertEqual(slug, "test-post-title")
            self.assertEqual(len(files), 2)  # 1 .md + 1 image

            # Check .md file target path
            self.assertEqual(files[0]["path"], "src/content/blog/test-post-title.md")
            # Check image target path
            self.assertEqual(files[1]["path"], "public/images/test-post-title/photo.jpg")

            # Verify image markdown link inside .md content
            decoded_md = base64.b64decode(files[0]["content"]).decode("utf-8")
            self.assertIn('![photo.jpg](/images/test-post-title/photo.jpg)', decoded_md)
            self.assertIn('date: "2026-07-29"', decoded_md)

    def test_build_post_files_payload_folder_format(self):
        with patch.dict(os.environ, {"BLOG_POST_FORMAT": "folder"}):
            attachments = [{"filename": "banner.png", "bytes": b"fake_banner"}]
            files, slug, md = build_post_files_payload(
                title="Astro Nano Test",
                body="Hello Astro Nano",
                description="Nano desc",
                attachments=attachments,
                post_date="2026-07-29"
            )
            self.assertEqual(slug, "astro-nano-test")
            self.assertEqual(len(files), 2)

            # Check folder layout paths
            self.assertEqual(files[0]["path"], "src/content/blog/astro-nano-test/index.md")
            self.assertEqual(files[1]["path"], "src/content/blog/astro-nano-test/banner.png")

            decoded_md = base64.b64decode(files[0]["content"]).decode("utf-8")
            self.assertIn('![banner.png](./banner.png)', decoded_md)

    def test_is_authorized_sender(self):
        database.set_config("admin_dc_email", "admin@gluek.info")
        database.set_admin_fingerprint("A1B2C3D4E5F67890A1B2C3D4E5F67890")

        self.assertTrue(database.is_authorized_sender("admin@gluek.info"))
        self.assertTrue(database.is_authorized_sender("ADMIN@GLUEK.INFO"))
        self.assertFalse(database.is_authorized_sender("hacker@other.com"))


if __name__ == "__main__":
    unittest.main()
