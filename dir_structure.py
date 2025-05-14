import os


def print_directory_structure(
    start_path, indent=0, ignore_dirs=None, ignore_files=None
):
    """
    Print the directory structure starting from start_path.

    Args:
        start_path (str): The path to start traversing from
        indent (int): Current indentation level (used in recursion)
        ignore_dirs (list): Directories to ignore
        ignore_files (list): Files to ignore
    """
    if ignore_dirs is None:
        ignore_dirs = ["__pycache__", "venv", ".venv", ".git", "node_modules"]

    if ignore_files is None:
        ignore_files = ["__init__.py", ".gitignore", ".DS_Store"]

    # Print the current directory name
    if indent == 0:
        print(f"📁 {os.path.basename(os.path.abspath(start_path))}")

    # Get items in the directory
    try:
        items = os.listdir(start_path)
        items.sort()

        # Process directories first, then files
        dirs = [
            item
            for item in items
            if os.path.isdir(os.path.join(start_path, item)) and item not in ignore_dirs
        ]
        files = [
            item
            for item in items
            if os.path.isfile(os.path.join(start_path, item))
            and item not in ignore_files
        ]

        # Print directories
        for i, dirname in enumerate(dirs):
            is_last_dir = i == len(dirs) - 1 and len(files) == 0
            prefix = "└── " if is_last_dir else "├── "
            print(" " * indent + prefix + f"📁 {dirname}")

            # Recursively print subdirectories with increased indentation
            next_indent = indent + 4
            next_path = os.path.join(start_path, dirname)
            print_directory_structure(next_path, next_indent, ignore_dirs, ignore_files)

        # Print files
        for i, filename in enumerate(files):
            is_last_file = i == len(files) - 1
            prefix = "└── " if is_last_file else "├── "
            print(" " * indent + prefix + f"📄 {filename}")

    except PermissionError:
        print(" " * indent + "  ⚠️  Permission denied")
    except Exception as e:
        print(" " * indent + f"  ⚠️  Error: {str(e)}")


if __name__ == "__main__":
    # Use the current directory by default, or specify another path
    path = "."  # Current directory
    print("\nDirectory Structure (ignoring __pycache__, __init__.py, and venv):\n")
    print_directory_structure(path)
