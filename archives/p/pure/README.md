# Pure

Pretty, minimal and fast ZSH prompt.

## Description

Pure is a pretty, minimal and fast ZSH prompt that shows:
- Git branch and dirty status
- Unpushed/unpulled commits with arrows
- Command execution time
- Username and host in SSH sessions
- VI-mode indication

## Requirements

- ZSH 5.2+
- Git 2.15.2+

## Installation

Files are installed to `~/usr/local/share/zsh/site-functions/pure/`

To use, add to your `.zshrc`:
```zsh
fpath+=($HOME/usr/local/share/zsh/site-functions/pure)
autoload -U promptinit; promptinit
prompt pure
```

## Source

https://github.com/sindresorhus/pure

## License

MIT License
