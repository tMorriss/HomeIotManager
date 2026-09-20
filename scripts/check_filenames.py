import os
import re
import sys


def check_filenames():
    pattern = re.compile(r'^[a-z0-9_]+\.py$')
    invalid_files = []

    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ('.git', '.tox', '.venv', '__pycache__')]
        for file in files:
            if file.endswith('.py') and not pattern.match(file):
                invalid_files.append(os.path.join(root, file))

    if invalid_files:
        print('Invalid filenames found:')
        for file in invalid_files:
            print(f'  {file}')
        sys.exit(1)
    else:
        print('All filenames are valid.')


if __name__ == '__main__':
    check_filenames()
