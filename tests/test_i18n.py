import tempfile
import unittest
from pathlib import Path

import polib

from i18n import Catalog


class CatalogWhitespaceTests(unittest.TestCase):
    def write_catalog(self, path, original, translation):
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8"}
        po.append(polib.POEntry(msgid=original, msgstr=translation))
        po.save(str(path))

    def test_metadata_with_repeated_spaces_renders_its_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.po"
            self.write_catalog(path, "A short  description.", "短い説明。")
            catalog = Catalog([str(path)])

            rendered = catalog.spans("A short  description.")

            self.assertIn('<span class="lang-ja">短い説明。</span>', rendered)
            self.assertIn("A short  description.", rendered)

    def test_shared_catalog_does_not_replace_lesson_whitespace_variant(self):
        with tempfile.TemporaryDirectory() as directory:
            lesson = Path(directory) / "lesson.po"
            shared = Path(directory) / "site.po"
            self.write_catalog(lesson, "A short  description.", "レッスンの説明。")
            self.write_catalog(shared, "A short description.", "共通の説明。")
            catalog = Catalog([str(lesson)])

            catalog.add(str(shared), override=False)

            self.assertEqual(catalog.get("A short\ndescription."), "レッスンの説明。")


if __name__ == "__main__":
    unittest.main()
