#!/usr/bin/env python3
"""Minimal `gnatprep` stand-in for building Florist with ohpcd's gcc-ada.

Why this exists
---------------
`gcc-ada/9.5.0` ships gnatbind/gnatchop/gnatclean/gnatlink/gnatls/gnatmake but
NOT `gnatprep`, while Florist's build needs it for the two `*.gpb` templates:

    libsrc/posix-implementation.gpb
    libsrc/threads/posix-timers-extensions.gpb

covered by Makefile.in:

    $(GENDIR)/%.adb: libsrc/%.gpb gnatprep.config
        $(GNATPREP) $< $@ gnatprep.config $(GNATPREPFLAGS)

Supported syntax
----------------
Those templates use only conditional directives:

    #  if <SYMBOL> then
    #  else
    #  end if;

Symbols are read from the `gnatprep.config` deffile that `configure` writes,
in the form `NAME := True|False`.  Preprocessor lines are dropped from the
output (equivalent to gnatprep's `-c`).
"""
import re
import sys

_DIRECTIVE = re.compile(r"^\s*#\s*(if|elsif|else|end\s+if)\b\s*(.*)$",
                        re.IGNORECASE)
_TRUTHY = ("true", "yes", "1")


def load_defs(path):
    """Parse `NAME := Value` assignments from a gnatprep deffile."""
    symbols = {}
    with open(path, "r", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("--") or ":=" not in line:
                continue
            name, _, value = line.partition(":=")
            value = value.strip()
            if value.endswith(";"):
                value = value[:-1].strip()
            symbols[name.strip()] = value
    return symbols


def truthy(value):
    return str(value).strip().lower() in _TRUTHY


def preprocess(lines, symbols):
    """Evaluate #if/#else/#end-if, emitting only active source lines."""
    out = []
    # Each frame: (parent_active, branch_already_taken)
    stack = []
    active = True
    for line in lines:
        match = _DIRECTIVE.match(line)
        if not match:
            if active:
                out.append(line)
            continue
        kind = re.sub(r"\s+", " ", match.group(1).strip().lower())
        rest = match.group(2).strip()
        if kind == "if":
            name = rest.split()[0] if rest else ""
            cond = truthy(symbols.get(name, "False"))
            stack.append((active, cond))
            active = active and cond
        elif kind == "elsif":
            if not stack:
                raise SystemExit("gnatprep-shim: #elsif without #if")
            parent, taken = stack[-1]
            name = rest.split()[0] if rest else ""
            cond = truthy(symbols.get(name, "False"))
            stack[-1] = (parent, taken or cond)
            active = parent and cond and not taken
        elif kind == "else":
            if not stack:
                raise SystemExit("gnatprep-shim: #else without #if")
            parent, taken = stack[-1]
            active = parent and not taken
        else:  # end if
            if not stack:
                raise SystemExit("gnatprep-shim: #end if without #if")
            parent, _ = stack.pop()
            active = parent
    if stack:
        raise SystemExit("gnatprep-shim: unterminated #if")
    return out


def main(argv):
    positional = [arg for arg in argv if not arg.startswith("-")]
    if len(positional) < 3:
        sys.stderr.write(
            "usage: gnatprep infile outfile deffile [-c] [-r] [-b]\n")
        return 2
    infile, outfile, deffile = positional[0], positional[1], positional[2]
    symbols = load_defs(deffile)
    with open(infile, "r", errors="replace") as handle:
        lines = handle.readlines()
    with open(outfile, "w") as handle:
        handle.write("".join(preprocess(lines, symbols)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
