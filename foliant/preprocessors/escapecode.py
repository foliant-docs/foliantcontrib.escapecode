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
    def render_code_block(self, element: block.CodeBlock) -> str:
        foliant_obj = self.foliant_obj
        indent = " " * 4
        lines = self.render_children(element).splitlines()
        for i, line in enumerate(lines):
            lines[i] = foliant_obj.escape(line.replace("\n", ''))

        lines = [self._prefix + indent + lines[0]] + [
            self._second_prefix + indent + line for line in lines[1:]
        ]
        self._prefix = self._second_prefix
        return "\n".join(lines) + "\n"


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
        ]
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()

        self.logger = self.logger.getChild('escapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')
        self.logger.debug(f'Options: {self.options}')

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

    def _escape_overlapping(self, markdown_content: str,) -> str:
        '''Replace the parts of raw content with detection patterns that may overlap
        (fence blocks, pre blocks) with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''

        if markdown_content:
            self.logger.debug(f'Found raw content part, type: ')    

            content_to_save_hash = self._save_raw_content(markdown_content)

            tag_to_insert = f'<escaped hash="{content_to_save_hash}" ></escaped>'

            match_string_replacement = f'{tag_to_insert}'
            markdown_content = match_string_replacement

        return markdown_content

    def _escape_tag(self, markdown_content: str, tag: str) -> str:
        '''Replace the parts of content enclosed between
        the same opening and closing pseudo-XML tags
        (e.g. ``<plantuml>...</plantuml>``)
        with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''

        def _sub(markdown_content):
            self.logger.debug(f'Found tag to escape: {tag}')

            content_to_save = markdown_content
            content_to_save_hash = self._save_raw_content(content_to_save)

            return f'<escaped hash="{content_to_save_hash}" ></escaped>'

        tag_pattern = re.compile(
            rf'(?<!\<)\<(?P<tag>{re.escape(tag)})' +
            r'(?:\s[^\<\>]*)?\>.*?\<\/(?P=tag)\>',
            flags=re.DOTALL
        )

        return tag_pattern.sub(_sub, markdown_content)

    def escape(self, markdown_content: str) -> str:
        '''Perform normalization. Replace the parts of Markdown content
        that should not be processed by following preprocessors
        with the ``<escaped>...</escaped>`` pseudo-XML tags.
        The ``unescapecode`` preprocessor should do reverse operation.

        :param markdown_content: Markdown content

        :returns: Markdown content with replaced raw parts
        '''

        for action in self.options.get('actions', []):
            if action.get('escape', []):
                print('escape')
                self.logger.debug('Escaping raw parts in the source content')
                print(markdown_content)
                markdown_content = self._escape_overlapping(markdown_content)

            else:
                self.logger.debug(f'Unknown action: {action}')

        return markdown_content

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing the file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            md = marko.Markdown(renderer=MarkdownRenderer)
            self.content = md.parse(markdown_content)

            markdown_content = md.render(self)

            processed_content = markdown_content

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
