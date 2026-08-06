# colordiff

Perl script wrapper for `diff` that produces the same output but with syntax highlighting (colours).

## Usage

```bash
colordiff file1 file2
diff -u file1 file2 | colordiff
```

## Dependencies

- Perl
- diffutils (diff)

## Configuration

System-wide config: `/etc/colordiffrc`
User config: `~/.colordiffrc`

Default colours suit dark backgrounds. For light backgrounds, use `colordiffrc-lightbg`.
