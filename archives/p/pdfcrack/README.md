# pdfcrack

PDF files password cracker. Recover passwords from PDF documents using both
owner- and user-passwords with the Standard Security Handler.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.21 | built | 纯 Makefile 项目，需补丁添加 configure + install target |

## Build Configuration

- **Build system**: makefile
- **Compiler**: clang/clang++
- **Dependencies**: none
- **Patches required**: 2 (Makefile install target + dummy configure script)

## Usage

```bash
pdfcrack -f document.pdf [OPTIONS]
```

Options include: `-b` benchmark, `-c` charset, `-w` wordlist, `-n` minpw,
`-m` maxpw, `-o` owner password, `-u` user password, `-p` verify password,
`-q` quiet, `-s` permutate, `-v` version.

## License

GPL-2.0-or-later

## Homepage

https://sourceforge.net/projects/pdfcrack/