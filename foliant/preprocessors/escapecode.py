'''
Preprocessor for Foliant documentation authoring tool.
Escapes code blocks, inline code, and other content parts
that should not be processed by any preprocessors.
'''

import re
from pathlib import Path
from hashlib import md5
from collections import OrderedDict

from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    defaults = {
        'cache_dir': Path('.escapecodecache'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()

        self.logger = self.logger.getChild('escapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

    def _normalize(self, markdown_content: str) -> str:
        '''Normalize the source Markdown content to simplify
        further operations: replace ``CRLF`` with ``LF``,
        remove excessive whitespace characters,
        provide trailing newline, etc.

        :param markdown_content: Source Markdown content

        :returns: Normalized Markdown content
        '''

        markdown_content = re.sub(r'\r\n', '\n', markdown_content)
        markdown_content = re.sub(r'\r', '\n', markdown_content)
        markdown_content = re.sub(r'(?<=\S)$', '\n', markdown_content)
        markdown_content = re.sub(r'\t', '    ', markdown_content)
        markdown_content = re.sub(r'[ \n]+$', '\n', markdown_content)
        markdown_content = re.sub(r' +\n', '\n', markdown_content)

        return markdown_content

    def escape(self, markdown_content: str) -> str:
        '''Replace the parts of Markdown content that should not be processed
        by any preprocessors (fence code blocks, pre code blocks,
        inline code, etc.) with pseudo-XML tags. Save these content parts
        into files. The ``unescapecode`` preprocessor should do the reverse operation.

        :param markdown_content: Markdown content

        :returns: Markdown content with replaced raw parts
        '''

        self.logger.debug('Normalizing the source content')

        markdown_content = self._normalize(markdown_content)

        patterns = OrderedDict()

        patterns['block_fence'] = re.compile(
            r'(?P<before>^|\n)' +
            r'(?P<content>' +
                r'(?P<backticks>```|~~~)(?:\S+)?(?:\n)' +
                r'(?:(?:[^\n]*\n)*?)' +
                r'(?P=backticks)' +
            r')' +
            r'(?P<after>\n)'
        )

        patterns['block_pre'] = re.compile(
            r'(?P<before>^|\n\n)' +
            r'(?P<content>' +
                r'(?:(?:    [^\n]*\n)+?)' +
            r')' +
            r'(?P<after>\n)'
        )

        patterns['inline_code'] = re.compile(
            r'(?P<content>`[^`\n]*`)'
        )

        for pattern_type in patterns:
            while True:
                match = re.search(patterns[pattern_type], markdown_content)

                if match:
                    self.logger.debug(f'Found raw content part, type: {pattern_type}')

                    if pattern_type == 'block_fence':
                        before = f'{match.group("before")}'
                        after = f'{match.group("after")}'
                        saved_content = f'{match.group("content")}'

                    elif pattern_type == 'block_pre':
                        before = f'{match.group("before")}'
                        after = f'\n{match.group("after")}'
                        saved_content = f'{match.group("content")}'[:-1]

                    elif pattern_type == 'inline_code':
                        before = ''
                        after = ''
                        saved_content = f'{match.group("content")}'

                    saved_content_hash = f'{md5(saved_content.encode()).hexdigest()}'

                    self.logger.debug(f'Hash: {saved_content_hash}')

                    saved_content_file_path = self._cache_dir_path / f'{saved_content_hash}.md'

                    if not saved_content_file_path.exists():
                        self.logger.debug(
                            f'Content is not found in cache, saving into the file: {saved_content_file_path}'
                        )

                        self._cache_dir_path.mkdir(parents=True, exist_ok=True)

                        with open(saved_content_file_path, 'w', encoding='utf8') as saved_content_file:
                            saved_content_file.write(saved_content)

                    match_str = f'{match.group(0)}'

                    tag = f'<escaped hash="{saved_content_hash}"></escaped>'

                    match_str_replacement = f'{before}{tag}{after}'

                    markdown_content = markdown_content.replace(match_str, match_str_replacement, 1)

                else:
                    break

        return markdown_content

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing the file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            processed_content = self.escape(markdown_content)

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
