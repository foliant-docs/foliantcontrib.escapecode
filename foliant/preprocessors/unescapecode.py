'''
Preprocessor for Foliant documentation authoring tool.
Unescapes raw content that is escaped by the
``escapecode`` preprocessor.
'''

import re
from pathlib import Path
from typing import Dict
OptionValue = int or float or bool or str

from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    defaults = {
        'cache_dir': Path('.escapecodecache'),
    }

    tags = 'escaped',

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cache_dir_path = (self.project_path / self.options['cache_dir']).resolve()

        self.logger = self.logger.getChild('unescapecode')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

    def _unescape(self, options: Dict[str, OptionValue]) -> str:
        saved_content_hash = options.get('hash', '')

        saved_content_file_path = self._cache_dir_path / f'{saved_content_hash}.md'

        with open(saved_content_file_path, encoding='utf8') as saved_content_file:
            saved_content = saved_content_file.read()

        return saved_content

    def unescape(self, markdown_content: str) -> str:
        def _sub(escaped_tag) -> str:
            return self._unescape(self.get_options(escaped_tag.group('options')))

        return self.pattern.sub(_sub, markdown_content)

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            processed_content = self.unescape(markdown_content)

            if processed_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_content)

        self.logger.info('Preprocessor applied')
