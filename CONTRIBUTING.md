# Contributing to Synq

First off, thank you for considering contributing to Synq! It's people like you that make open source such a great community.

## How Can I Contribute?

### Reporting Bugs
If you find a bug, please open an issue and provide as much detail as possible, including:
* Your operating system and Python version.
* The SQLAlchemy and database driver versions.
* A minimal, reproducible example of the bug.
* The full traceback of the error.

### Suggesting Enhancements
If you have an idea for a new feature or an improvement to an existing one, please open an issue to start a discussion. This allows us to align on the proposal before you put in significant work.

### Pull Requests
1.  Fork the repository and create your branch from `main`.
2.  Set up a virtual environment and install the development dependencies:
    ```bash
    pip install -e ".[dev]"
    ```
3.  Make your changes. Ensure you add tests for any new features or bug fixes.
4.  Run the test suite to make sure everything passes:
    ```bash
    pytest
    ```
5.  Format your code with Ruff.
6.  Submit a pull request with a clear description of the changes.

We look forward to your contributions!
