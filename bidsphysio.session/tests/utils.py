import hashlib
from pathlib import Path

TESTS_DATA_PATH = Path(__file__).parent / 'data'


def file_md5sum(filename):
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()
