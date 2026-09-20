'''Script to verify that all Python filenames adhere to snake_case naming convention.'''

import os
import re
import sys

# Allowed exceptions or special filenames if any
ALLOWED_FILENAMES = {
    '__init__.py',
}

# Regex pattern for snake_case python file names
SNAKE_CASE_PATTERN = re.compile(r'^[a-z0-9_]+\.py$')


def check_filenames(target_dir='.'):
    '''Recursively scan directories for .py files and validate naming convention.'''
    invalid_files = []
    excluded_dirs = {'.tox', '.git', '__pycache__', 'build', 'dist', 'venv', '.venv'}

    for root, dirs, files in os.walk(target_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in files:
            if file.endswith('.py'):
                if file in ALLOWED_FILENAMES:
                    continue
                if not SNAKE_CASE_PATTERN.match(file):
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    invalid_files.append(rel_path)

    if invalid_files:
        print('Error: The following Python files do not follow snake_case naming convention:')
        for path in invalid_files:
            print(f'  - {path}')
        return False

    print('All Python file names adhere to snake_case naming convention.')
    return True


if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    success = check_filenames(project_root)
    if not success:
        sys.exit(1)
