# zsh-git-prompt

Informative git prompt for zsh - displays information about the current git repository.

## Overview

This is a zsh plugin that shows git status information in your prompt:
- Branch name
- Difference with remote branch  
- Number of files staged/changed/untracked
- Merge conflicts

## Installation

1. Clone/copy this repository
2. Add to ~/.zshrc:
   ```sh
   source path/to/zshrc.sh
   PROMPT='%B%m%~%b$(git_super_status) %# '
   ```

## Implementation

- **Python (default)**: gitstatus.py - works out of the box
- **Haskell (optional)**: gitstatus executable - 4-6x faster but requires GHC+Stack

## Requirements

- zsh
- git
- python3 (for default implementation)

## License

MIT License
