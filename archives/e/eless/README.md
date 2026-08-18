# eless

**eless** — A Better Less

A bash script that runs Emacs in `view-mode` with sane defaults, designed to
replace `less`, `diff`, `man`, and `ls` as a pager.

## Features

- Syntax highlighting
- Org-mode file rendering
- Better navigable man page viewer
- Better Info viewer
- Colored diffs, `git diff`, `git log`, `ls`, etc. (auto ANSI detection)
- Filter log files by regexp
- Auto-revert log files (like `tail -f`)
- Quickly change frame and font sizes

## Usage

```bash
eless file.txt          # View a file
echo "hello" | eless     # View piped input
man eless                # View man page (if installed)
```

## Runtime Dependencies

- Emacs (eless wraps Emacs in view-mode)
- Bash

## License

MIT

## Homepage

https://github.com/kaushalmodi/eless
