"""
Preprocessor for Foliant documentation authoring tool.
Escapes code blocks, inline code, and other content parts
that should not be processed by any preprocessors.
"""

import re
from pathlib import Path
from hashlib import md5

from foliant.preprocessors.base import BasePreprocessor

import marko
import marko.block as block

from marko import Markdown, inline, patterns
from marko.helpers import Source
from marko.md_renderer import MarkdownRenderer


class Preprocessor(BasePreprocessor):
    defaults = {
        'cache_dir': Path('.escapecodecache'),
        'actions': [
            'normalize',
            {
                'escape': [
                    'fence_blocks',
                    'pre_blocks',
                    'inline_code',
                ]
            }
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.content = None
        self.pre_blocks_pattern = None
        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()
        self.frontmatter_pattern = re.compile(r'^((-|\+){3})\n([\s\S]+?)\n((-|\+){3})([\s\S]*)')

        self.logger = self.logger.getChild('escapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')
        self.logger.debug(f'Options: {self.options}')

    @staticmethod
    def _normalize(markdown_content: str) -> str:
        """Normalize the source Markdown content to simplify
        further operations: replace ``CRLF`` with ``LF``,
        remove excessive whitespace characters,
        provide trailing newline, etc.

        :param markdown_content: Source Markdown content

        :returns: Normalized Markdown content
        """

        markdown_content = re.sub(r'^\ufeff', '', markdown_content)
        markdown_content = re.sub(r'\ufeff', '\u2060', markdown_content)
        markdown_content = re.sub(r'\r\n', '\n', markdown_content)
        markdown_content = re.sub(r'\r', '\n', markdown_content)
        # this regex generated excessive newlines with the Marko parser and was commented out.
        # markdown_content = re.sub(r'(?<=\S)$', '\n', markdown_content)
        markdown_content = re.sub(r'\t', '    ', markdown_content)
        markdown_content = re.sub(r'[ \n]+$', '\n', markdown_content)
        markdown_content = re.sub(r' +\n', '\n', markdown_content)

        return markdown_content

    def _save_raw_content(self, content_to_save: str) -> str:
        """Calculate MD5 hash of raw content.
        Save the content into the file
        with the hash in its name.

        :param content_to_save: Raw content

        :returns: MD5 hash of raw content
        """
        content_to_save_hash = f'{md5(content_to_save.encode()).hexdigest()}'

        self.logger.debug(f'Hash of raw content part to save: {content_to_save_hash}')

        content_to_save_file_path = (self._cache_dir_path / f'{content_to_save_hash}.md').resolve()

        self.logger.debug(f'File to save: {content_to_save_file_path}')

        if content_to_save_file_path.exists():
            self.logger.debug('File already exists, skipping')

        else:
            self.logger.debug('Writing the file')

            self._cache_dir_path.mkdir(parents=True, exist_ok=True)

            with open(content_to_save_file_path, 'w', encoding='utf8') as content_to_save_file:
                content_to_save_file.write(content_to_save)

        return content_to_save_hash

    def _escape_overlapping(self, markdown_content: str, raw_type: str) -> str:
        """Replace the parts of raw content with detection patterns that may overlap
        (fence blocks, pre blocks) with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param markdown_content: Markdown content
        :param raw_type

        :returns: Markdown content with replaced raw parts of certain types
        """
        content_to_save, after = "", ""
        if markdown_content:
            self.logger.debug(f'Found raw content part, type: {raw_type}')

            if raw_type == 'fence_blocks':
                after = ''
                content_to_save = markdown_content

            elif raw_type == 'pre_blocks':
                after = ''
                content_to_save = markdown_content

            content_to_save_hash = self._save_raw_content(content_to_save)

            match_string = markdown_content
            tag_to_insert = f'<escaped hash="{content_to_save_hash}"></escaped>'
            match_string_replacement = f'{tag_to_insert}{after}'
            markdown_content = markdown_content.replace(match_string, match_string_replacement, 1)

        return markdown_content

    def _escape_not_overlapping(self, markdown_content: str, raw_type: str) -> str:
        """Replace the parts of raw content with detection patterns that may not overlap
        (inline code, HTML-style comments) with the ``<escaped>...</escaped>`` pseudo-XML tags.
        :param markdown_content: Markdown content
        :param raw_type
        :returns: Markdown content with replaced raw parts of certain types
        """
        self.logger.debug(f'Found raw content part, type: {raw_type}')

        content_to_save = markdown_content
        content_to_save_hash = self._save_raw_content(content_to_save)

        markdown_content = f'<escaped hash="{content_to_save_hash}"></escaped>'

        return markdown_content

    def _escape_tag(self, markdown_content: str, tag: str) -> str:
        """Replace the parts of content enclosed between
        the same opening and closing pseudo-XML tags
        (e.g. ``<plantuml>...</plantuml>``)
        with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param markdown_content: Markdown content
        :param tag

        :returns: Markdown content with replaced raw parts of certain types
        """
        def _sub(match):
            self.logger.debug(f'Found tag to escape: {tag}')

            content_to_save = match.group(0)
            content_to_save_hash = self._save_raw_content(content_to_save)

            return f'<escaped hash="{content_to_save_hash}"></escaped>'

        tag_pattern = re.compile(
            rf'(?<!<)<(?P<tag>{re.escape(tag)})' +
            r'(?:\s[^<>]*)?>.*?</(?P=tag)>',
            flags=re.DOTALL
        )

        return tag_pattern.sub(_sub, markdown_content)

    def escape(self, markdown_content: str) -> str:
        """Preparing to use parsing and rendering with Marko.

        :param markdown_content: Markdown content

        :returns: Markdown content with replaced raw parts
        """

        # exclude admonitions syntax:
        self.pre_blocks_pattern = r'(\={3}|\!{3}|\?{3}|\?{3}\+)\s((\w+)(?: +\"(.*)\")|\"(.*)\")'

        md = marko.Markdown(renderer=EscapeCodeMarkdownRenderer)

        self.content = md.parse(markdown_content)

        markdown_content = md.render(self)

        if self.options.get('actions'):
            for action in self.options.get('actions', []):
                if type(action) is dict:
                    for raw_type in action.get('escape', []):
                        if type(raw_type) is dict:
                            for tag in raw_type['tags']:
                                self.logger.debug(
                                    f'Escaping content parts enclosed in the tag: <{tag}> ' +
                                    '(detection patterns may not overlap)'
                                )
                                markdown_content = self._escape_tag(markdown_content, tag)

        return markdown_content

    def escape_for_raw_type(self, markdown_content: str, raw_type: str) -> str:
        """Perform normalization.
        Replace the parts of Markdown content
        that should not be processed by following preprocessors
        with the ``<escaped>...</escaped>`` pseudo-XML tags.
        The ``unescapecode`` preprocessor should do reverse operation.

        :param markdown_content: Markdown content
        :param raw_type

        :returns: Markdown content with replaced raw parts
        """

        for action in self.options.get('actions', []):
            if action == 'normalize':
                self.logger.debug('Normalizing the source content')

                markdown_content = self._normalize(markdown_content)

            elif action.get('escape', []):
                self.logger.debug('Escaping raw parts in the source content')

                if raw_type == 'fence_blocks' or raw_type == 'pre_blocks':
                    self.logger.debug(f'Escaping {raw_type} (detection patterns may overlap)')

                    markdown_content = self._escape_overlapping(markdown_content, raw_type)
                    if raw_type == 'pre_blocks':
                        markdown_content = markdown_content.replace("\n", '')

                elif raw_type == 'inline_code' or raw_type == 'comments':
                    self.logger.debug(f'Escaping {raw_type} (detection patterns may not overlap)')

                    markdown_content = self._escape_not_overlapping(markdown_content, raw_type)

            else:
                self.logger.debug(f'Unknown action: {action}')

        return markdown_content

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing the file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            if markdown_content.startswith('---') or markdown_content.startswith('+++'):
                def _sub_frontmatter(m):
                    return m.group(3)
                def _sub_content(m):
                    return m.group(6)
                def _sub_format(m):
                    return m.group(1)
                frontmatter = self.frontmatter_pattern.sub(_sub_frontmatter, markdown_content)
                content = self.frontmatter_pattern.sub(_sub_content, markdown_content)
                format = self.frontmatter_pattern.sub(_sub_format, markdown_content)
                for action in self.options.get('actions', []):
                    if type(action) == dict:
                        for escape_action in action['escape']:
                            if escape_action == 'frontmatter':
                                frontmatter = self.escape_for_raw_type(frontmatter, 'fence_blocks')
                markdown_content = f"{format}\n" + frontmatter + f"\n{format}\n" + self.escape(content)
            else:
                markdown_content = self.escape(markdown_content)

            processed_content = markdown_content

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')


class FoliantMarkdown(Markdown):
    def render(self, foliant_obj) -> str:
        """Call ``self.renderer.render(text)``.
        Override this to handle the parsed result.
        """
        self.renderer.foliant_obj = foliant_obj
        parsed = foliant_obj.content
        self.renderer.root_node = parsed
        with self.renderer as r:
            return r.render(parsed)


marko.Markdown = FoliantMarkdown


class HTMLBlock(block.HTMLBlock):

    def __init__(self, lines: str) -> None:
        self.children = lines
        self.id = self.id

    @classmethod
    def match(cls, source: Source) -> int or bool:
        if source.expect_re(r"(?i) {,3}<(script|pre|style|textarea)[>\s]"):
            assert source.match
            cls._end_cond = re.compile(rf"(?i)</{source.match.group(1)}>")
            cls.id = 1
            return 1
        if source.expect_re(r" {,3}<!--"):
            cls._end_cond = re.compile(r"-->")
            cls.id = 2
            return 2
        if source.expect_re(r" {,3}<\?"):
            cls._end_cond = re.compile(r"\?>")
            cls.id = 3
            return 3
        if source.expect_re(r" {,3}<!"):
            cls._end_cond = re.compile(r">")
            cls.id = 4
            return 4
        if source.expect_re(r" {,3}<!\[CDATA\["):
            cls._end_cond = re.compile(r"]]>")
            cls.id = 5
            return 5
        block_tag = r"(?:{})".format("|".join(patterns.tags))
        if source.expect_re(r"(?im) {,3}</?%s(?: +|/?>|$)" % block_tag):
            cls._end_cond = None
            cls.id = 6
            return 6
        if source.expect_re(
            r"(?m) {,3}(<%(tag)s(?:%(attr)s)*[^\n\S]*/?>|</%(tag)s[^\n\S]*>)[^\n\S]*$"
            % {"tag": patterns.tag_name, "attr": patterns.attribute_no_lf}
        ):
            cls._end_cond = None
            cls.id = 7
            return 7

        return False

block.HTMLBlock = HTMLBlock

class EscapeCodeMarkdownRenderer(MarkdownRenderer):
    def __init__(self):
        super().__init__()
        self._prefix = None

    @staticmethod
    def _check_options(raw_type: str, actions) -> bool:
        if actions:
            for action in actions:
                if type(action) == dict:
                    for escape_action in action['escape']:
                        if escape_action == raw_type:
                            return True
        return False

    def render_setext_heading(self, element: block.SetextHeading) -> str:
        result = self._prefix + self.render_children(element)
        self._prefix = self._second_prefix
        return result

    def render_code_block(self, element: block.CodeBlock) -> str:
        foliant_obj = self.foliant_obj
        indent = " " * 4; raw_type = 'pre_blocks'
        exclude = False
        run_escapecode = self._check_options(raw_type, foliant_obj.options.get('actions', []))
        lines = self.render_children(element).splitlines()
        pattern = foliant_obj.options.get('pattern_override', {}).get(raw_type, '')
        if run_escapecode:
            for i, line in enumerate(lines):
                indent = " " * 4
                if line.startswith(" "):
                    indent = " " * (4 + len(re.search(r'^ +', line).group(0)))
                if pattern: exclude = re.compile(pattern).search(line)
                if exclude or re.search(r'\s<escaped*></escaped>', line) or re.search(foliant_obj.pre_blocks_pattern, line):
                    lines[i] = indent + line.strip()
                elif line.strip() == "":
                    lines[i] = line.strip()
                else:
                    lines[i] = indent + foliant_obj.escape_for_raw_type(line.strip(), raw_type)
            indent = ''
        lines = [self._prefix + indent + lines[0]] + [
            self._second_prefix + indent + line for line in lines[1:]
        ]
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"

    def render_fenced_code(self, element: block.FencedCode) -> str:
        foliant_obj = self.foliant_obj
        raw_type = 'fence_blocks'
        run_escapecode = self._check_options(raw_type, foliant_obj.options.get('actions', []))
        extra = f" {element.extra}" if element.extra else ""
        first_line = f"```{element.lang}{extra}"
        if run_escapecode:
            first_line = foliant_obj.escape_for_raw_type(first_line, raw_type)
        lines = [first_line]
        for line in self.render_children(element).splitlines():
            if line.strip() != "":
                lines.append(self._second_prefix + line)
            else:
                lines.append(line)
        last_line = self._second_prefix + "```"
        lines.append(last_line)
        code_block = "\n".join(lines)
        if run_escapecode:
            if not re.search(r'<escaped*></escaped>', line):
                code_block = foliant_obj.escape_for_raw_type(code_block, raw_type)
        self._prefix = self._second_prefix
        return self._prefix + code_block + "\n"

    def render_code_span(self, element: inline.CodeSpan) -> str:
        text = element.children
        foliant_obj = self.foliant_obj
        raw_type = 'inline_code'
        exclude = False
        run_escapecode = self._check_options(raw_type, foliant_obj.options.get('actions', []))
        pattern = foliant_obj.options.get('pattern_override', {}).get(raw_type, '')
        if run_escapecode:
            if pattern: exclude = re.compile(pattern).search(text)
            if exclude or re.search(r'<escaped*></escaped>', text):
                text = text
            else:
                text = foliant_obj.escape_for_raw_type(text, raw_type)
        if text and text[0] == "`" or text[-1] == "`":
            return f"`` {text} ``"
        return f"`{text}`"

    def render_thematic_break(self, element: block.ThematicBreak) -> str:
        result = self._prefix + "---\n"
        self._prefix = self._second_prefix
        return result

    def render_list(self, element: block.List) -> str:
        result = []
        if element.ordered:
            for num, child in enumerate(element.children, element.start):
                with self.container(f"{num}. ", " " * (len(str(num)) + 2)):
                    result.append(self.render(child))
        else:
            for child in element.children:
                with self.container(f"{element.bullet} ", "  "):
                    result.append(self.render(child))
        self._prefix = self._second_prefix
        for num, item in enumerate(result):
            no_new_line = False
            lines = item.split("\n")
            for i, line in enumerate(lines):
                if len(lines) <= 2:
                    no_new_line = True
                if line.strip() == "":
                    lines[i] = ""
            if no_new_line:
                result[num] = "\n".join(lines)
            else:
                result[num] = "\n".join(lines) +"\n"

        return "".join(result)

    def render_html_block(self, element: block.HTMLBlock) -> str:
        children = element.children
        raw_type = 'comments'
        foliant_obj = self.foliant_obj
        run_escapecode = self._check_options(raw_type, foliant_obj.options.get('actions', []))
        exclude = False
        pattern = foliant_obj.options.get('pattern_override', {}).get(raw_type, '')
        if element.id == 2 and run_escapecode:
            if pattern: exclude = re.compile(pattern).search(children)
            if exclude or re.search(r'<escaped*></escaped>', children):
                children = children
            else:
                children = foliant_obj.escape_for_raw_type(children, raw_type)
        result = self._prefix + children + "\n"
        self._prefix = self._second_prefix
        return result
