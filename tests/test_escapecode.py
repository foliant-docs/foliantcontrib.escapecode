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

class TestEscapecode(TestCase):
    def setUp(self):
        self.ptf = PreprocessorTestFramework('escapecode')
        self.ptf.context['project_path'] = Path('.')

    def test_pre_blocks(self):
        content = data_file_content(os.path.join('data', 'input', 'pre_blocks.md'))
        content_with_hash = data_file_content(os.path.join('data', 'expected', 'pre_blocks.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_fence_blocks(self):
        content = data_file_content(os.path.join('data', 'input', 'fence_blocks.md'))
        content_with_hash = data_file_content(os.path.join('data', 'expected', 'fence_blocks.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )

    def test_inline_code(self):
        content = data_file_content(os.path.join('data', 'input', 'inline_code.md'))
        content_with_hash = data_file_content(os.path.join('data', 'expected', 'inline_code.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': content
            },
            expected_mapping = {
                'index.md': content_with_hash
            }
        )
