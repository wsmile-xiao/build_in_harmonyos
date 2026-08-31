"""Minimal unexpand(1) for atools bats fixtures (OHOS adaptation).

Only implements what upstream tests/*.bats retab() needs: fold LEADING blanks
into tabs according to tab stops (--first-only semantics, which covers both
GNU `--first-only` and busybox `-f`). Intra-line whitespace is preserved.

Usage: unexpand.py [-f | --first-only] [-tN | -t N | --tabs=N | -N] [FILE...]
"""
import sys


def parse_args(argv):
    tab = 8
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-f", "--first-only"):
            pass
        elif a == "-t" and i + 1 < len(argv):
            i += 1
            tab = int(argv[i])
        elif a.startswith("-t") and a[2:].isdigit():
            tab = int(a[2:])
        elif a.startswith("--tabs=") and a[7:].isdigit():
            tab = int(a.split("=", 1)[1])
        elif a == "--":
            files.extend(argv[i + 1:])
            break
        elif len(a) > 1 and a[0] == "-" and a[1:].isdigit():
            tab = int(a[1:])  # GNU legacy form: unexpand -4
        else:
            files.append(a)
        i += 1
    return tab, files


def unexpand_line(line, tab):
    """Fold leading blank run into tabs (first-only)."""
    n = len(line)
    i = 0
    while i < n and line[i] in (" ", "\t"):
        i += 1
    head = line[:i]
    rest = line[i:]

    out = []
    col = 0
    pending = 0
    for ch in head:
        if ch == "\t":
            if pending:
                out.append(" " * pending)
                col += pending
                pending = 0
            out.append("\t")
            col = (col // tab + 1) * tab
        else:
            pending += 1
            if (col + pending) % tab == 0:
                if pending > 1:
                    out.append("\t")
                    col += pending
                    pending = 0
                elif i < n and line[i] in (" ", "\t"):
                    # single space landing exactly on a stop with more
                    # blanks following: keep as spaces, next stop folds
                    pass
                else:
                    out.append(" " * pending)
                    col += pending
                    pending = 0
    if pending:
        out.append(" " * pending)
    return "".join(out) + rest


def main():
    tab, files = parse_args(sys.argv[1:])
    if files:
        with open(files[0], "r") as f:
            data = f.read()
    else:
        data = sys.stdin.read()
    lines = data.split("\n")
    trailing_nl = bool(lines) and lines[-1] == ""
    if trailing_nl:
        lines.pop()
    result = "\n".join(unexpand_line(ln, tab) for ln in lines)
    if trailing_nl or lines:
        result += "\n"
    sys.stdout.write(result)


main()
