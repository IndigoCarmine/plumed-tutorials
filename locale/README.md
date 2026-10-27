# Translations of PLUMED-TUTORIALS

The website can be shown in English or Japanese (button in the header).  The English text is the
original, and the Japanese translations are stored in the gettext `.po` files in this folder:

| File | Content |
| ---- | ------- |
| `ja/site.po` | strings in the layout, the navigation bar, the scripts of the pages and `compile.py` |
| `ja/pages/<page>.md.po` | the pages of the website (`Info.md`, `browse.md`, ...) |
| `ja/lessons/<id>/lesson.po` | title and description of the lesson (`lesson.yml`) and titles of the videos (`EMBED.yml`) |
| `ja/lessons/<id>/<file>.md.po` | the markdown files in the zip archive of the lesson |

Lessons can also ship their own translations in the folder `locale/ja/` of their zip archive.
The translations in this repository take precedence over those.

## How the translations are used

`i18n.py` splits the English markdown into translation units: headings, paragraphs, list items,
table cells, HTML elements written on a single line, and the node labels of mermaid flowcharts.
When the site is built, each unit that has a translation is replaced by

```html
<span class="lang-en">original</span><span class="lang-ja">translation</span>
```

and CSS shows only the language selected by the reader.  Code blocks (and therefore PLUMED inputs)
are never modified.  Units without a translation, and units whose English text has changed since
they were translated, are shown in English.  Fuzzy entries are not used.

* Pages of the site: `.ci/prepare` runs `python i18n.py build-site` on the prepared site.
* Lessons: `compile.py` inserts the translations right after downloading the zip archive,
  before the PLUMED inputs are processed.

Parts of a markdown file can be excluded from translation with `<!-- i18n-skip -->` ... `<!-- i18n-end -->`.

## Translating

Install the requirements (`pip install -r requirements.txt`; [gettext](https://www.gnu.org/software/gettext/)
is recommended so that changed strings are marked as fuzzy instead of being dropped).  Then:

```bash
# pages of the site and site.po
python i18n.py update-pages
# one or more lessons (downloads the zip archive given in lesson.yml)
python i18n.py update-lesson lessons/21/003
# translated / fuzzy / untranslated entries of each file
python i18n.py stats
```

Edit the `.po` files with any `.po` editor (e.g. [Poedit](https://poedit.net)) or a text editor and commit them.
When the English text of a lesson changes, run `update-lesson` again: entries whose text changed are
marked as fuzzy so that the translation can be checked and the fuzzy flag removed.

Strings in templates are marked with `{% include t.html s="..." %}` (Liquid), `t("...")` (JavaScript in the pages)
and `i18n.site_spans("...")` (Python), and are collected in `site.po` by `update-pages`.
