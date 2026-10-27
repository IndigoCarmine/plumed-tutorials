# formatted and checked with ruff v0.11
"""
Translation of the website and of the lessons using gettext .po files.

The English markdown is split into translation units (headings, paragraphs, list items,
table cells, HTML lines that contain text and the node labels of mermaid flowcharts).
Each unit for which a translation is found is replaced by

    <span class="lang-en">original</span><span class="lang-ja">translation</span>

and the CSS in assets/css/style.scss shows only the language selected by the reader.
Units without a translation (e.g. because the original text has changed) are left untouched,
so they are shown in English.  Code blocks are never modified.

The translations are stored in:

    locale/ja/site.po                     strings in the layout, navigation and scripts
    locale/ja/pages/<page>.md.po          the pages of the website (Info.md, browse.md, ...)
    locale/ja/lessons/<id>/lesson.po      title and description of the lesson and video titles
    locale/ja/lessons/<id>/<file>.md.po   the markdown files in the zip archive of the lesson

A lesson can also ship its own translations in the folder locale/ja/ of its zip archive.
The translations stored in this repository take precedence over those.
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile

import polib
import yaml

LANG = "ja"
ROOT = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(ROOT, "locale", LANG)
# The pages of the website that are translated
PAGES = (
    "Info.md",
    "plumed.md",
    "masterclass.md",
    "browse.md",
    "contribute.md",
    "cite.md",
    "nest.md",
)
# Strings used on the site that cannot be found by scanning the templates
SITE_EXTRA = ("Welcome to PLUMED-TUTORIALS!",)

SKIP_START = "<!-- i18n-skip -->"
SKIP_END = "<!-- i18n-end -->"

_fence_re = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w-]*)")
_atx_re = re.compile(r"^(\s{0,3}#{1,6}\s+)(.*?)(\s+#+\s*|\s*)$")
_hr_re = re.compile(r"^\s{0,3}(([-*_])\s*){3,}$|^\s{0,3}=+\s*$")
_list_re = re.compile(r"^(\s*)([*+-]|\d+[.)])(\s+)(.*)$")
_quote_re = re.compile(r"^(\s{0,3}>\s?)(.*)$")
_table_sep_re = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_tag_re = re.compile(r"<(/?)([A-Za-z][\w-]*)[^>]*?(/?)>")
_void_tags = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "col"}
_raw_html_tags = {
    "script",
    "style",
    "form",
    "table",
    "iframe",
    "select",
    "pre",
    "svg",
    "textarea",
}
_raw_open_re = re.compile(
    r"<(" + "|".join(sorted(_raw_html_tags)) + r")\b", re.IGNORECASE
)
# HTML block tags that may interrupt a paragraph (type 6 HTML blocks in CommonMark)
_block_tags = {
    "address",
    "article",
    "aside",
    "base",
    "basefont",
    "blockquote",
    "body",
    "caption",
    "center",
    "col",
    "colgroup",
    "dd",
    "details",
    "dialog",
    "dir",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "frame",
    "frameset",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hr",
    "html",
    "iframe",
    "legend",
    "li",
    "link",
    "main",
    "menu",
    "menuitem",
    "nav",
    "noframes",
    "ol",
    "optgroup",
    "option",
    "p",
    "param",
    "search",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "title",
    "tr",
    "track",
    "ul",
}
_block_start_re = re.compile(r"^\s{0,3}</?([A-Za-z][\w-]*)")
_element_re = re.compile(r"^<([A-Za-z][\w-]*)\b[^>]*>(.*)</\1\s*>$", re.DOTALL)
# Mermaid node labels, e.g. A[label], A(label), A{label}, A["label"], A([label]), A[[label]]
_mermaid_node_re = re.compile(
    r"\b([A-Za-z0-9_]+)(\[\[|\[\(|\(\[|\(\(|\[|\(|\{)(\"?)([^\[\]\(\)\{\}\"]+?)\3(\]\]|\)\]|\]\)|\)\)|\]|\)|\})"
)
_mermaid_click_re = re.compile(r'^\s*click\s+\S+\s+"[^"]*"\s+"([^"]*)"')
# Strings marked for translation in templates and scripts
_quoted = r"""(["'])((?:\\.|(?!\1).)*)\1"""
_site_string_res = (
    re.compile(r"\{%\s*include\s+t\.html\s+s=" + _quoted + r"\s*%\}"),
    re.compile(r"\bt\(" + _quoted + r"\)"),
    re.compile(r"\bsite_spans\(" + _quoted),
)


def normalize(text):
    """The msgid of a unit: the text with all whitespace collapsed"""
    return " ".join(text.split())


def _has_words(text):
    text = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|<[^>]*>|https?://\S+", "", text)
    return re.search(r"[^\W\d_]", text) is not None


def spans(original, translation):
    return (
        '<span class="lang-en">'
        + original
        + '</span><span class="lang-ja">'
        + translation
        + "</span>"
    )


def _html_line_is_balanced(line):
    stack = []
    for m in _tag_re.finditer(line):
        closing, name, selfclosing = m.group(1), m.group(2).lower(), m.group(3)
        if name in _raw_html_tags:
            return False
        if selfclosing or name in _void_tags:
            continue
        if closing:
            if not stack or stack[-1] != name:
                return False
            stack.pop()
        else:
            stack.append(name)
    return not stack


def _split_cells(row):
    """Split a table row into the separators and the cells"""
    parts = re.split(r"(?<!\\)(\|)", row)
    return parts


class _Transformer:
    """
    Walk through a markdown document and call translate(msgid, lineno, kind) for each
    translation unit.  translate returns the translation or None.
    """

    def __init__(self, translate):
        self.translate = translate

    def unit(self, text, lineno, kind="text"):
        """Return the replacement for the text of a unit (which may contain newlines)"""
        if not text.strip() or not _has_words(text):
            return text
        tr = self.translate(normalize(text), lineno, kind)
        if not tr:
            return text
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        return lead + spans(text.strip(), tr) + trail

    def html_line(self, line, lineno):
        """
        A line of an HTML block is translated only if it is one complete element, e.g.
        <p align="center"><b>text</b></p>.  The block elements around the text are kept
        and the text inside them is translated.
        """
        stripped = line.strip()
        if not _html_line_is_balanced(stripped):
            return line
        head, inner, tail = "", stripped, ""
        while True:
            m = _element_re.match(inner)
            if (
                not m
                or m.group(1).lower() not in _block_tags
                or not _html_line_is_balanced(m.group(2))
            ):
                break
            close = inner.rindex("</")
            head += inner[: m.start(2)]
            tail = inner[close:] + tail
            inner = m.group(2)
        if head == "" or not _has_words(inner):
            return line
        indent = line[: len(line) - len(line.lstrip())]
        return indent + head + self.unit(inner, lineno, "html") + tail

    def mermaid_line(self, line, lineno):
        m = _mermaid_click_re.match(line)
        if m:
            # Tooltips are translated when the navigation file is processed in compile.py
            if _has_words(m.group(1)):
                self.translate(normalize(m.group(1)), lineno, "tooltip")
            return line

        def repl(m):
            label = m.group(4)
            if not _has_words(label):
                return m.group(0)
            tr = self.translate(normalize(label), lineno, "mermaid")
            if not tr:
                return m.group(0)
            tr = tr.replace('"', "'")
            html = (
                "<span class='lang-en'>"
                + label.strip()
                + "</span><span class='lang-ja'>"
                + tr
                + "</span>"
            )
            return m.group(1) + m.group(2) + '"' + html + '"' + m.group(5)

        return _mermaid_node_re.sub(repl, line)

    def table_row(self, line, lineno):
        parts = _split_cells(line)
        out = []
        for p in parts:
            if p == "|" or not p.strip():
                out.append(p)
            else:
                out.append(self.unit(p, lineno, "cell"))
        return "".join(out)

    def run(self, text):
        lines = text.split("\n")
        out = []
        para = []  # (lineno, line) of the current paragraph or list item
        para_prefix = ""  # list marker or indentation in front of the paragraph
        state = {
            "fence": None,
            "mermaid": False,
            "skip": False,
            "math": False,
            "rawtag": None,
        }
        in_table = False
        in_list = False
        in_html = False
        prev_blank = True

        def flush():
            nonlocal para, para_prefix
            if para:
                lineno = para[0][0]
                body = "\n".join(line for _, line in para)
                out.append(para_prefix + self.unit(body, lineno, "text"))
            para = []
            para_prefix = ""

        i = 0
        # front matter
        if lines and lines[0].strip() == "---":
            for j in range(1, len(lines)):
                if lines[j].strip() in ("---", "..."):
                    out.extend(lines[: j + 1])
                    i = j + 1
                    break

        while i < len(lines):
            line = lines[i]
            lineno = i + 1
            stripped = line.strip()
            i += 1

            # Inside a fenced block
            if state["fence"]:
                if re.match(r"^\s*" + re.escape(state["fence"]) + r"\s*$", line) or (
                    stripped.startswith(state["fence"][0] * len(state["fence"]))
                    and set(stripped) == {state["fence"][0]}
                ):
                    state["fence"], state["mermaid"] = None, False
                    out.append(line)
                elif state["mermaid"]:
                    out.append(self.mermaid_line(line, lineno))
                else:
                    out.append(line)
                continue
            if state["skip"]:
                out.append(line)
                if SKIP_END in line:
                    state["skip"] = False
                continue
            if state["rawtag"]:
                out.append(line)
                if "</" + state["rawtag"] in line.lower():
                    state["rawtag"] = None
                continue
            if state["math"]:
                out.append(line)
                if stripped.endswith("$$"):
                    state["math"] = False
                continue

            if not stripped:
                flush()
                out.append(line)
                in_table = in_html = False
                prev_blank = True
                continue

            m = _fence_re.match(line)
            if m and not (m.group(2)[0] == "`" and "`" in line[m.end(2) :]):
                flush()
                state["fence"] = m.group(2)
                state["mermaid"] = m.group(3) == "mermaid"
                out.append(line)
                prev_blank = False
                continue
            if SKIP_START in line:
                flush()
                state["skip"] = SKIP_END not in line
                out.append(line)
                continue
            if stripped.startswith("$$"):
                flush()
                if not (len(stripped) > 2 and stripped.endswith("$$")):
                    state["math"] = True
                out.append(line)
                continue
            m = _raw_open_re.search(line)
            if m:
                # HTML elements whose content is never translated (scripts, forms, ...)
                flush()
                tag = m.group(1).lower()
                if "</" + tag not in line[m.end() :].lower():
                    state["rawtag"] = tag
                out.append(line)
                continue
            if stripped.startswith(("{%", "{:")):
                flush()
                out.append(line)
                continue
            m = _block_start_re.match(line)
            if in_html or (
                stripped.startswith("<")
                and (not para or (m and m.group(1).lower() in _block_tags))
            ):
                flush()
                in_html = True
                out.append(self.html_line(line, lineno))
                continue
            if _hr_re.match(line):
                # setext underline or horizontal rule
                flush()
                out.append(line)
                continue
            if in_table:
                if "|" in line:
                    out.append(self.table_row(line, lineno))
                    continue
                in_table = False
            if (
                "|" in line
                and i < len(lines)
                and _table_sep_re.match(lines[i])
                and "|" in lines[i]
            ):
                flush()
                out.append(self.table_row(line, lineno))
                out.append(lines[i])
                i += 1
                in_table = True
                continue
            m = _atx_re.match(line)
            if m:
                flush()
                out.append(
                    m.group(1) + self.unit(m.group(2), lineno, "heading") + m.group(3)
                )
                continue
            m = _quote_re.match(line)
            if m:
                flush()
                # collect the whole block quote and translate its content recursively
                block, prefixes = [m.group(2)], [m.group(1)]
                while i < len(lines) and _quote_re.match(lines[i]):
                    mm = _quote_re.match(lines[i])
                    block.append(mm.group(2))
                    prefixes.append(mm.group(1))
                    i += 1
                inner = _Transformer(
                    lambda msgid, ln, kind, offset=lineno - 1: self.translate(
                        msgid, ln + offset, kind
                    )
                ).run("\n".join(block))
                inner_lines = inner.split("\n")
                if len(inner_lines) == len(block):
                    out.extend(p + t for p, t in zip(prefixes, inner_lines))
                else:
                    out.extend(prefixes[0] + t for t in inner_lines)
                continue
            m = _list_re.match(line)
            if m:
                flush()
                in_list = True
                para_prefix = m.group(1) + m.group(2) + m.group(3)
                para = [(lineno, m.group(4))]
                prev_blank = False
                continue
            indent = len(line) - len(line.lstrip())
            if prev_blank and indent >= 4 and not in_list:
                # indented code block
                out.append(line)
                continue
            if not para:
                if indent == 0:
                    in_list = False
                para_prefix = line[:indent]
                para = [(lineno, line[indent:])]
            else:
                para.append((lineno, line))
            prev_blank = False
        flush()
        return "\n".join(out)


def transform(text, translate):
    """Apply translate(msgid, lineno, kind) -> str|None to every translation unit of text"""
    return _Transformer(translate).run(text)


def extract(text):
    """Return a list of (msgid, lineno, kind) for the translation units of text"""
    found = []

    def record(msgid, lineno, kind):
        found.append((msgid, lineno, kind))

    transform(text, record)
    return found


class Catalog:
    """A dictionary of translations read from one or more .po files"""

    def __init__(self, po_paths=()):
        self.tr = {}
        for path in po_paths:
            self.add(path)

    def add(self, path, override=True):
        if not os.path.exists(path):
            return
        for entry in polib.pofile(path):
            if entry.obsolete or entry.fuzzy or not entry.msgstr:
                continue
            if override or entry.msgid not in self.tr:
                self.tr[entry.msgid] = entry.msgstr

    def __len__(self):
        return len(self.tr)

    def get(self, text):
        return self.tr.get(normalize(text))

    def apply(self, text):
        return transform(text, lambda msgid, lineno, kind: self.tr.get(msgid))

    def spans(self, text):
        """Inline HTML showing the text in the language selected by the reader"""
        tr = self.get(text)
        return spans(text, tr) if tr else text

    def both(self, text):
        """Plain text with both languages, for places where HTML cannot be used (e.g. tooltips)"""
        tr = self.get(text)
        return text + " / " + tr.replace('"', "'") if tr else text


# ---------------------------------------------------------------------------
# Reading and writing .po files
# ---------------------------------------------------------------------------


def _new_po():
    po = polib.POFile(wrapwidth=0)
    po.metadata = {
        "Project-Id-Version": "PLUMED-TUTORIALS",
        "Language": LANG,
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    return po


def update_po(path, entries):
    """
    Update the po file at path so that it contains exactly the msgids in entries,
    a list of (msgid, occurrence, comment).  Existing translations are kept, translations
    of msgids that are no longer used are marked obsolete (or fuzzy matched by msgmerge
    when it is available).
    """
    pot = _new_po()
    seen = {}
    for msgid, occurrence, comment in entries:
        if msgid in seen:
            seen[msgid].occurrences.append(occurrence)
            continue
        e = polib.POEntry(
            msgid=msgid, msgstr="", occurrences=[occurrence], comment=comment
        )
        seen[msgid] = e
        pot.append(e)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and shutil.which("msgmerge"):
        with tempfile.NamedTemporaryFile("w", suffix=".pot", delete=False) as f:
            potfile = f.name
        pot.save(potfile)
        subprocess.run(
            [
                "msgmerge",
                "--quiet",
                "--update",
                "--backup=none",
                "--no-wrap",
                path,
                potfile,
            ],
            check=True,
        )
        os.remove(potfile)
        return
    old = polib.pofile(path) if os.path.exists(path) else None
    if old is not None:
        oldtr = {e.msgid: e for e in old if not e.obsolete}
        for e in pot:
            if e.msgid in oldtr:
                e.msgstr = oldtr[e.msgid].msgstr
                e.flags = list(oldtr[e.msgid].flags)
                e.tcomment = oldtr[e.msgid].tcomment
        for msgid, e in oldtr.items():
            if msgid not in seen and e.msgstr:
                e.obsolete = True
                pot.append(e)
    pot.save(path)


def markdown_entries(text, filename):
    kinds = {"tooltip": "mermaid click tooltip", "mermaid": "mermaid node label"}
    return [
        (msgid, (filename, str(lineno)), kinds.get(kind, ""))
        for msgid, lineno, kind in extract(text)
    ]


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------


def site_strings():
    entries = []
    nav = os.path.join(ROOT, "_data", "navigation.yml")
    with open(nav) as f:
        for item in yaml.safe_load(f)["pages"]:
            entries.append((item["title"], ("_data/navigation.yml", ""), "navigation"))
    files = [
        os.path.join(ROOT, "_layouts", "default.html"),
        os.path.join(ROOT, "compile.py"),
    ]
    files += [os.path.join(ROOT, p) for p in PAGES]
    files += glob.glob(os.path.join(ROOT, "_includes", "*.html"))
    for fname in files:
        with open(fname) as f:
            for lineno, line in enumerate(f, 1):
                for r in _site_string_res:
                    for m in r.finditer(line):
                        msgid = m.group(2).replace('\\"', '"').replace("\\'", "'")
                        if "{{" in msgid:
                            continue
                        entries.append(
                            (msgid, (os.path.relpath(fname, ROOT), str(lineno)), "")
                        )
    for s in SITE_EXTRA:
        entries.append((s, ("i18n.py", ""), ""))
    return entries


def site_catalog():
    return Catalog([os.path.join(LOCALE_DIR, "site.po")])


def site_spans(text, **kwargs):
    """Text from Python code shown in the selected language.  {key} placeholders are filled from kwargs"""
    out = site_catalog().spans(text)
    for k, v in kwargs.items():
        out = out.replace("{" + k + "}", v)
    return out


def update_pages():
    for page in PAGES:
        with open(os.path.join(ROOT, page)) as f:
            text = f.read()
        update_po(
            os.path.join(LOCALE_DIR, "pages", page + ".po"),
            markdown_entries(text, page),
        )
    update_po(os.path.join(LOCALE_DIR, "site.po"), site_strings())


def build_site(sitedir):
    """Translate the pages of the site that has been prepared in sitedir"""
    catalog = Catalog(sorted(glob.glob(os.path.join(LOCALE_DIR, "pages", "*.po"))))
    catalog.add(os.path.join(LOCALE_DIR, "site.po"))
    for page in PAGES + ("README.md",):
        path = os.path.join(sitedir, page)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            text = f.read()
        with open(path, "w") as f:
            f.write(catalog.apply(text))
    os.makedirs(os.path.join(sitedir, "_data"), exist_ok=True)
    with open(os.path.join(sitedir, "_data", "i18n.yml"), "w") as f:
        yaml.safe_dump(site_catalog().tr, f, allow_unicode=True, width=100000)
    stats()


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


def lesson_locale_dir(lesson_id):
    return os.path.join(LOCALE_DIR, "lessons", lesson_id)


def lesson_markdown_files(datadir):
    files = []
    for path in glob.glob(os.path.join(datadir, "**", "*.md"), recursive=True):
        rel = os.path.relpath(path, datadir)
        if rel.split(os.sep)[0] in ("locale",) or any(
            p.startswith(".") for p in rel.split(os.sep)
        ):
            continue
        files.append(rel)
    return sorted(files)


def lesson_catalog(lesson_id, datadir):
    """All the translations available for a lesson"""
    catalog = Catalog()
    # translations shipped in the zip archive of the lesson
    for path in sorted(
        glob.glob(os.path.join(datadir, "locale", LANG, "**", "*.po"), recursive=True)
    ):
        catalog.add(path)
    # translations stored in this repository take precedence
    for path in sorted(
        glob.glob(
            os.path.join(lesson_locale_dir(lesson_id), "**", "*.po"), recursive=True
        )
    ):
        catalog.add(path)
    catalog.add(os.path.join(LOCALE_DIR, "site.po"), override=False)
    return catalog


def translate_lesson(lesson_id, datadir):
    """Insert the translations in the markdown files of a lesson.  Returns the catalog that was used"""
    catalog = lesson_catalog(lesson_id, datadir)
    if not len(catalog):
        return catalog
    for rel in lesson_markdown_files(datadir):
        path = os.path.join(datadir, rel)
        with open(path) as f:
            text = f.read()
        new = catalog.apply(text)
        if new != text:
            with open(path, "w") as f:
                f.write(new)
    return catalog


def update_lesson(lesson_path):
    """Download a lesson and create/update the .po files with the strings to translate"""
    from compile import cd, fetch_lesson_data

    lesson_path = os.path.abspath(lesson_path)
    if lesson_path.endswith(".yml"):
        lesson_path = os.path.dirname(lesson_path)
    with open(os.path.join(lesson_path, "lesson.yml")) as f:
        config = yaml.load(f, Loader=yaml.BaseLoader)
    parts = lesson_path.rstrip("/").split("/")
    lesson_id = parts[-2] + "." + parts[-1]
    outdir = lesson_locale_dir(lesson_id)

    entries = []
    for key in ("title", "description"):
        if key in config:
            entries.append((config[key], ("lesson.yml", key), ""))
    with tempfile.TemporaryDirectory() as tmp, cd(tmp):
        fetch_lesson_data(config, lesson_path)
        for embed in ("data/embed.yml", "data/EMBED.yml"):
            if os.path.exists(embed):
                with open(embed) as f:
                    embeds = yaml.load(f, Loader=yaml.BaseLoader) or {}
                for key, data in embeds.items():
                    if "title" in data:
                        entries.append(
                            (
                                data["title"],
                                (os.path.basename(embed), key),
                                "video title",
                            )
                        )
        update_po(os.path.join(outdir, "lesson.po"), entries)
        for rel in lesson_markdown_files("data"):
            with open(os.path.join("data", rel)) as f:
                text = f.read()
            po_entries = markdown_entries(text, rel)
            po_path = os.path.join(outdir, rel + ".po")
            if po_entries or os.path.exists(po_path):
                update_po(po_path, po_entries)
    print("Updated", os.path.relpath(outdir, ROOT))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def stats():
    print("Translation status (" + LANG + "): translated / fuzzy / untranslated")
    for path in sorted(
        glob.glob(os.path.join(LOCALE_DIR, "**", "*.po"), recursive=True)
    ):
        po = polib.pofile(path)
        print(
            f"  {os.path.relpath(path, LOCALE_DIR):60s} {len(po.translated_entries()):5d} {len(po.fuzzy_entries()):5d} {len(po.untranslated_entries()):5d}"
        )


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog="i18n",
        description="Manage the translations of the PLUMED-TUTORIALS website and lessons.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "update-pages", help="update the .po files of the pages of the site and site.po"
    )
    p = sub.add_parser(
        "update-lesson", help="download lessons and update their .po files"
    )
    p.add_argument("lessons", nargs="+", help="lesson directories, e.g. lessons/21/003")
    p = sub.add_parser(
        "build-site", help="insert the translations in the pages of a prepared site"
    )
    p.add_argument("sitedir")
    sub.add_parser("stats", help="print the translation status")
    args = parser.parse_args()
    if args.command == "update-pages":
        update_pages()
    elif args.command == "update-lesson":
        for lesson in args.lessons:
            update_lesson(lesson)
    elif args.command == "build-site":
        build_site(args.sitedir)
    elif args.command == "stats":
        stats()
