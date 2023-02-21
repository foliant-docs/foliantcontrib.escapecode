'''
Preprocessor for Foliant documentation authoring tool.
Escapes code blocks, inline code, and other content parts
that should not be processed by any preprocessors.
'''

import re
import marko
from pathlib import Path
from hashlib import md5

from foliant.preprocessors.base import BasePreprocessor
from marko.md_renderer import MarkdownRenderer
from marko import *
import marko.block as block
import marko.inline as inline


class foliantMarkdown(Markdown):
    def render(self, foliant_obj) -> str:
        """Call ``self.renderer.render(text)``.
        Override this to handle parsed result.
        """
        self.renderer.foliant_obj = foliant_obj
        parsed = foliant_obj.content
        self.renderer.root_node = parsed
        with self.renderer as r:
            return r.render(parsed)


marko.Markdown = foliantMarkdown


class MarkdownRenderer(MarkdownRenderer):

    def render_setext_heading(self, element: block.SetextHeading) -> str:
        return self.render_children(element)

    def render_code_block(self, element: block.CodeBlock) -> str:
        indent = " " * 4
        lines = self.render_children(element).splitlines()
        foliant_obj = self.foliant_obj
        raw_type = 'pre_blocks'
        exclude = False
        for k, v in foliant_obj.options.get('pattern_override').items():
            if k == raw_type: exclude = re.compile(v)
        for action in foliant_obj.options.get('actions', []):
            if type(action) is not str:
                for escape_action in action['escape']:
                    if escape_action == 'pre_blocks':
                        for i, line in enumerate(lines):
                            if exclude: exclude = re.search(exclude, line)
                            if exclude or re.search(r'<escaped*></escaped>', line):
                                lines[i] = indent + line
                            else:
                                del_indent = 0
                                if line.startswith(" "):
                                    indent_size = len(re.search(r"^ +", line).group(0))
                                    if indent_size < 4: del_indent = indent_size
                                    else: del_indent = 4
                                lines[i] = indent + foliant_obj.escape_for_raw_type(line[del_indent:], raw_type)
        lines = [self._prefix + lines[0]] + [
            self._second_prefix + line for line in lines[1:]
        ]
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"

    def render_fenced_code(self, element: block.FencedCode) -> str:
        extra = f" {element.extra}" if element.extra else ""
        lines = [self._prefix + f"```{element.lang}{extra}"]
        lines.extend(
            self._second_prefix + line
            for line in self.render_children(element).splitlines()
        )
        lines.append(self._second_prefix + "```")
        self._prefix = self._second_prefix

        foliant_obj = self.foliant_obj
        raw_type = 'fence_blocks'
        exclude = False
        for k, v in foliant_obj.options.get('pattern_override').items():
            if k == raw_type: exclude = re.compile(v)
        for action in foliant_obj.options.get('actions', []):
            if type(action) is not str:
                for escape_action in action['escape']:
                    if escape_action == 'fence_blocks':
                        for i, line in enumerate(lines):
                            if exclude: exclude = re.search(exclude, line)
                            if exclude or re.search(r'<escaped*></escaped>', line):
                                lines[i] = line
                            else:
                                lines[i] = foliant_obj.escape_for_raw_type(line, raw_type)
        return "\n".join(lines) + "\n"

    def render_code_span(self, element: inline.CodeSpan) -> str:
        text = element.children
        foliant_obj = self.foliant_obj
        raw_type = 'inline_code'
        exclude = False
        for k, v in foliant_obj.options.get('pattern_override').items():
            if k == raw_type: exclude = re.compile(v)
        for action in foliant_obj.options.get('actions', []):
            if type(action) is not str:
                for escape_action in action['escape']:
                    if escape_action == raw_type:
                        if exclude: exclude = re.search(exclude, text)
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
                    {
                        'tags': [
                            'plantuml',
                            'seqdiag'
                        ]
                    }
                ]
            }
        ],
        'pattern_override': {
            'inline_code': '(`(?!(JIRA|My-API:))[^`\n]*`)',
            'pre_block': '\={3}\s\"|\!{3}\s[A-z]+|\?{3}\+\s[A-z]+|\?{3}\s[A-z]+'
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()

        self.logger = self.logger.getChild('escapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')
        try:
            exclude_pattern = self.options['pattern_override']
            self.exclude_pattern = re.compile(
                exclude_pattern
            )
            self.logger.debug(f"inline_code replaced by {exclude_pattern}")
        except:
            pass
        self.logger.debug(f'Options: {self.options}')

    def _normalize(self, markdown_content: str) -> str:
        '''Normalize the source Markdown content to simplify
        further operations: replace ``CRLF`` with ``LF``,
        remove excessive whitespace characters,
        provide trailing newline, etc.
        :param markdown_content: Source Markdown content
        :returns: Normalized Markdown content
        '''

        markdown_content = re.sub(r'^\ufeff', '', markdown_content)
        markdown_content = re.sub(r'\ufeff', '\u2060', markdown_content)
        markdown_content = re.sub(r'\r\n', '\n', markdown_content)
        markdown_content = re.sub(r'\r', '\n', markdown_content)
        # markdown_content = re.sub(r'(?<=\S)$', '\n', markdown_content)
        markdown_content = re.sub(r'\t', '    ', markdown_content)
        markdown_content = re.sub(r'[ \n]+$', '\n', markdown_content)
        markdown_content = re.sub(r' +\n', '\n', markdown_content)

        return markdown_content

    def _save_raw_content(self, content_to_save: str) -> str:
        '''Calculate MD5 hash of raw content. Save the content into the file
        with the hash in its name.

        :param content_to_save: Raw content

        :returns: MD5 hash of raw content
        '''

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

    def _escape_overlapping(self, markdown_content: str, raw_type) -> str:
        '''Replace the parts of raw content with detection patterns that may overlap
        (fence blocks, pre blocks) with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''
        if markdown_content:
            self.logger.debug(f'Found raw content part, type: {raw_type}')

            if raw_type == 'fence_blocks':
                after = ''
                content_to_save = markdown_content

            elif raw_type == 'pre_blocks':
                after = '\n'
                content_to_save = markdown_content

            content_to_save_hash = self._save_raw_content(content_to_save)

            match_string = markdown_content
            tag_to_insert = f'<escaped hash="{content_to_save_hash}"></escaped>'
            match_string_replacement = f'{tag_to_insert}{after}'
            markdown_content = markdown_content.replace(match_string, match_string_replacement, 1)

        return markdown_content

    def _escape_not_overlapping(self, markdown_content: str, raw_type) -> str:
        '''Replace the parts of raw content with detection patterns that may not overlap
        (inline code, HTML-style comments) with the ``<escaped>...</escaped>`` pseudo-XML tags.
        :param content_to_save: Markdown content
        :returns: Markdown content with replaced raw parts of certain types
        '''
        self.logger.debug(f'Found raw content part, type: {raw_type}')

        content_to_save = markdown_content
        print(repr(content_to_save))
        content_to_save_hash = self._save_raw_content(content_to_save)

        markdown_content = f'<escaped hash="{content_to_save_hash}"></escaped>'

        return markdown_content

    def _escape_tag(self, markdown_content: str, tag: str) -> str:
        '''Replace the parts of content enclosed between
        the same opening and closing pseudo-XML tags
        (e.g. ``<plantuml>...</plantuml>``)
        with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''
        def _sub(match):
            self.logger.debug(f'Found tag to escape: {tag}')

            content_to_save = match
            content_to_save_hash = self._save_raw_content(content_to_save)

            return f'<escaped hash="{content_to_save_hash}"></escaped>'

        raw_type = 'inline_code'
        tag_pattern = re.compile(
            rf'(?<!\<)\<(?P<tag>{re.escape(tag, raw_type)})' +
            r'(?:\s[^\<\>]*)?\>.*?\<\/(?P=tag)\>',
            flags=re.DOTALL
        )

        return tag_pattern.sub(_sub, markdown_content)

    def escape(self, markdown_content: str ) -> str:
        '''Perform normalization. Replace the parts of Markdown content
        that should not be processed by following preprocessors
        with the ``<escaped>...</escaped>`` pseudo-XML tags.
        The ``unescapecode`` preprocessor should do reverse operation.

        :param markdown_content: Markdown content

        :returns: Markdown content with replaced raw parts
        '''

        md = marko.Markdown(renderer=MarkdownRenderer)
        self.content = md.parse(markdown_content)

        markdown_content = md.render(self)
        return markdown_content

    def escape_for_raw_type(self, markdown_content: str, raw_type) -> str:

        for action in self.options.get('actions', []):
            if action == 'normalize':
                self.logger.debug('Normalizing the source content')

                markdown_content = self._normalize(markdown_content)

            elif action.get('escape', []):
                self.logger.debug('Escaping raw parts in the source content')
                print(raw_type)
                # for raw_type in action['escape']:
                if raw_type == 'fence_blocks' or raw_type == 'pre_blocks':
                    self.logger.debug(f'Escaping {raw_type} (detection patterns may overlap)')

                    markdown_content = self._escape_overlapping(markdown_content, raw_type)

                elif raw_type == 'inline_code' or raw_type == 'comments':
                    self.logger.debug(f'Escaping {raw_type} (detection patterns may not overlap)')

                    markdown_content = self._escape_not_overlapping(markdown_content, raw_type)

                elif type(raw_type) is dict:
                    for tag in raw_type['tags']:
                        self.logger.debug(
                            f'Escaping content parts enclosed in the tag: <{tag}> ' +
                            '(detection patterns may not overlap)'
                    )

                    markdown_content = self._escape_tag(markdown_content, tag)

                else:
                    self.logger.debug(f'Unknown raw content type: {raw_type}')

            else:
                self.logger.debug(f'Unknown action: {action}')

        return markdown_content

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing the file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            markdown_content = self.escape(markdown_content)

            processed_content = markdown_content

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
