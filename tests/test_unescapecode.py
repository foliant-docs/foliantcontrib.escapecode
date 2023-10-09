import os

from pathlib import Path
from foliant_test.preprocessor import PreprocessorTestFramework
from unittest import TestCase

def rel_name(path:str):
    return os.path.join(os.path.dirname(__file__), path)

def data_file_content(path: str) -> str:
    '''read data file by path relative to this module and return its contents'''
    with open(rel_name(path), encoding='utf8') as f:
        return f.read()

class TestUnescapecode(TestCase):
    def setUp(self):
        self.ptf = PreprocessorTestFramework('unescapecode')
        self.ptf.context['project_path'] = Path('.')

    def test_pre_blocks(self):
        content = data_file_content(os.path.join('data', 'expected', 'pre_blocks.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'pre_blocks.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_fence_blocks(self):
        content = data_file_content(os.path.join('data', 'expected', 'fence_blocks.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'fence_blocks.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_inline_code(self):
        content = data_file_content(os.path.join('data', 'expected', 'inline_code.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'inline_code.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )


    def test_comments(self):
        content = data_file_content(os.path.join('data', 'expected', 'comments.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'comments.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_tags(self):
        self.ptf.options =  {
            'cache_dir': Path('.escapecodecache'),
            'actions': [
                'normalize',
                {
                    'escape': [
                        {
                            'tags': [
                                'plantuml',
                                'seqdiag'
                            ]
                        }
                    ]
                }
            ],
        }
        content = data_file_content(os.path.join('data', 'expected', 'tags.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'tags.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_pattern_override(self):
        content = data_file_content(os.path.join('data', 'expected', 'pattern_override.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'pattern_override.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_frontmatter_yaml(self):
        content = data_file_content(os.path.join('data', 'expected', 'frontmatter_yaml.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'frontmatter_yaml.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_frontmatter_toml(self):
        content = data_file_content(os.path.join('data', 'expected', 'frontmatter_toml.md'))
        content_with_hash = data_file_content(os.path.join('data', 'input', 'frontmatter_toml.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )
