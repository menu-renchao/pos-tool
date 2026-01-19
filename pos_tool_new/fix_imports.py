#!/usr/bin/env python3
"""
Fix import statements - convert UI to ui in all files
"""
import os
import re

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix pos_tool_new.UI to pos_tool_new.UI
    content = re.sub(r'from pos_tool_new\.UI\.', 'from pos_tool_new.UI.', content)
    content = re.sub(r'from pos_tool_new\.main_window\.', 'from pos_tool_new.UI.main_window.', content)
    content = re.sub(r'from pos_tool_new\.widgets\.', 'from pos_tool_new.UI.widgets.', content)
    content = re.sub(r'from pos_tool_new\.styles\.', 'from pos_tool_new.UI.styles.', content)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed imports in: {file_path}")

def main():
    """Fix imports in all Python files"""
    root_dir = os.path.dirname(os.path.abspath(__file__))

    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for file in files:
            if file.endswith('.py') and file != 'fix_imports.py':
                file_path = os.path.join(root, file)
                fix_imports_in_file(file_path)

if __name__ == '__main__':
    main()
    print("Import fixing completed!")