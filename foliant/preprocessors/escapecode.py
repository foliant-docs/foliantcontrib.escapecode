'''
Preprocessor for Foliant documentation authoring tool.
Escapes code blocks, inline code, and other content parts
that should not be processed by any preprocessors.
'''

import re
from pathlib import Path
from hashlib import md5

from foliant.preprocessors.base import BasePreprocessor


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

    _raw_patterns = {}

    _raw_patterns['fence_blocks'] = re.compile(
        r'(?P<before>^|\n)' +
        r'(?P<content>' +
            r'(?P<backticks>```|~~~)(?:\S+)?(?:\n)' +
            r'(?:(?:[^\n]*\n)*?)' +
            r'(?P=backticks)' +
        r')' +
        r'(?P<after>\n)'
    )

    _raw_patterns['pre_blocks'] = re.compile(
        r'(?P<before>^|\n\n)' +
        r'(?P<content>' +
            r'(?:(?:    [^\n]*\n)+?)' +
        r')' +
        r'(?P<after>\n)'
    )

    _raw_patterns['inline_code'] = re.compile(
        r'(`[^`\n]*`)'
    )

    _raw_patterns['comments'] = re.compile(
        r'(\<\!\-\-.*?\-\-\>)',
        flags=re.DOTALL
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()

        self.logger = self.logger.getChild('escapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')
        self.logger.debug(f'Options: {self.options}')

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

    def _escape_overlapping(self, markdown_content: str, raw_type: str) -> str:
        '''Replace the parts of raw content with detection patterns that may overlap
        (fence blocks, pre blocks) with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''

        while True:
            match = re.search(self._raw_patterns[raw_type], markdown_content)

            if match:
                self.logger.debug(f'Found raw content part, type: {raw_type}')

                if raw_type == 'fence_blocks':
                    before = f'{match.group("before")}'
                    after = f'{match.group("after")}'
                    content_to_save = f'{match.group("content")}'

                elif raw_type == 'pre_blocks':
                    before = f'{match.group("before")}'
                    after = f'\n{match.group("after")}'
                    content_to_save = f'{match.group("content")}'[:-1]

                content_to_save_hash = self._save_raw_content(content_to_save)

                match_string = match.group(0)

                tag_to_insert = f'<escaped hash="{content_to_save_hash}"></escaped>'
                match_string_replacement = f'{before}{tag_to_insert}{after}'
                markdown_content = markdown_content.replace(match_string, match_string_replacement, 1)

            else:
                break

        return markdown_content

    def _escape_not_overlapping(self, markdown_content: str, raw_type: str) -> str:
        '''Replace the parts of raw content with detection patterns that may not overlap
        (inline code, HTML-style comments) with the ``<escaped>...</escaped>`` pseudo-XML tags.

        :param content_to_save: Markdown content

        :returns: Markdown content with replaced raw parts of certain types
        '''

        def _sub(match):
            self.logger.debug(f'Found raw content part, type: {raw_type}')

            content_to_save = match.group(0)
            content_to_save_hash = self._save_raw_content(content_to_save)

            return f'<escaped hash="{content_to_save_hash}"></escaped>'

        return self._raw_patterns[raw_type].sub(_sub, markdown_content)

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

            content_to_save = match.group(0)
            content_to_save_hash = self._save_raw_content(content_to_save)

            return f'<escaped hash="{content_to_save_hash}"></escaped>'

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
            if action == 'normalize':
                self.logger.debug('Normalizing the source content')

                markdown_content = self._normalize(markdown_content)

            elif action.get('escape', []):
                self.logger.debug('Escaping raw parts in the source content')

                for raw_type in action['escape']:
                    if raw_type == 'fence_blocks' or raw_type == 'pre_blocks':
                        self.logger.debug(f'Escaping {raw_type} (detection patterns may overlap)')

                        markdown_content = self._escape_overlapping(markdown_content, raw_type)

                    elif raw_type == 'inline_code' or raw_type == 'comments':
                        self.logger.debug(f'Escaping {raw_type} (detection patterns may not overlap)')

                        markdown_content = self._escape_not_overlapping(markdown_content, raw_type)

                    elif raw_type.get('tags', []):
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

            processed_content = self.escape(markdown_content)

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
