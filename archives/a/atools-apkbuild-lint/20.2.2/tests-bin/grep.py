#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore")
import sys, re, os

def bre_to_ere(p):
    res = ""
    i = 0
    while i < len(p):
        if p[i] == "\\" and i+1 < len(p):
            nxt = p[i+1]
            if nxt in "+?|(){}":
                res += nxt
                i += 2
            elif nxt == "\\":
                res += "\\\\"
                i += 2
            else:
                res += "\\" + nxt
                i += 2
        elif p[i] in "+?|(){}":
            res += "\\" + p[i]
            i += 1
        else:
            res += p[i]
            i += 1
    return res

def parse_args(argv):
    opts = {"E": False, "F": False, "G": False, "i": False, "v": False, "q": False, "H": None, "n": False, "o": False, "x": False, "c": False, "l": False, "L": False, "h": False, "e": []}
    files = []
    patterns = []
    i = 0
    after_dd = False
    while i < len(argv):
        a = argv[i]
        if a == "--":
            after_dd = True
            if not opts["e"] and not patterns and i+1 < len(argv):
                patterns.append(argv[i+1])
                files.extend(argv[i+2:])
            else:
                files.extend(argv[i+1:])
            break
        if a.startswith("-") and len(a) > 1 and not a.startswith("--"):
            j = 1
            while j < len(a):
                ch = a[j]
                if ch == "e":
                    pat = a[j+1:] if j+1 < len(a) else ""
                    if pat:
                        opts["e"].append(pat)
                        j = len(a)
                    else:
                        i += 1
                        if i < len(argv):
                            opts["e"].append(argv[i])
                        else:
                            sys.stderr.write("grep: option requires an argument -- 'e'\n"); sys.exit(2)
                    break
                elif ch == "f":
                    patfile = a[j+1:] if j+1 < len(a) else ""
                    if not patfile:
                        i += 1
                        if i < len(argv):
                            patfile = argv[i]
                    if patfile and os.path.isfile(patfile):
                        with open(patfile, "r", encoding="utf-8", errors="ignore") as pf:
                            for line in pf:
                                opts["e"].append(line.rstrip("\n"))
                    j = len(a)
                    break
                elif ch in opts:
                    opts[ch] = True
                    if ch == "H":
                        opts["H"] = True
                    elif ch == "h":
                        opts["H"] = False
                    j += 1
                else:
                    j += 1
            i += 1
            continue
        elif a.startswith("--"):
            if a == "--help":
                print("usage: grep [OPTION]... PATTERN [FILE]...")
                sys.exit(0)
            elif a.startswith("--color"):
                i += 1; continue
            elif a in ("--extended-regexp",): opts["E"] = True
            elif a in ("--fixed-strings",): opts["F"] = True
            elif a in ("--basic-regexp",): opts["G"] = True
            elif a in ("--ignore-case",): opts["i"] = True
            elif a in ("--invert-match",): opts["v"] = True
            elif a in ("--quiet", "--silent"): opts["q"] = True
            elif a in ("--with-filename",): opts["H"] = True
            elif a in ("--no-filename",): opts["H"] = False
            elif a in ("--line-number",): opts["n"] = True
            elif a in ("--only-matching",): opts["o"] = True
            elif a in ("--line-regexp",): opts["x"] = True
            i += 1; continue
        else:
            if not opts["e"] and not patterns:
                patterns.append(a)
            else:
                files.append(a)
            i += 1
    if opts["e"]:
        patterns = opts["e"] + patterns
    if not patterns:
        pass
    return opts, patterns, files

def compile_pattern(pat, opts):
    flags = 0
    if opts["i"]:
        flags |= re.IGNORECASE
    if opts["F"]:
        pat = re.escape(pat)
        return re.compile(pat, flags)
    # GNU quirk: \s inside [] is not whitespace class (treated as 's')
    # Python's \s inside [] would match whitespace and cause false positives
    # for custom_variable's ^[\sA-Za-z0-9_]*= . Emulate GNU by not expanding \s inside brackets.
    # Replace \s that appears inside [...] with literal 's' for matching.
    def _fix_bracket_s(m):
        inner = m.group(1)
        inner = inner.replace("\\s", "s").replace("\\S", "S")
        return "[" + inner + "]"
    pat = re.sub(r'\[([^\]]*)\]', lambda m: _fix_bracket_s(m), pat)
    if not opts["E"] and not opts["F"] and not opts["G"]:
        pat = bre_to_ere(pat)
    elif opts["G"]:
        pat = bre_to_ere(pat)
    pat = pat.replace("?+", "*").replace("*+", "*").replace("++", "+").replace("?*", "*").replace("+*", "*")
    try:
        return re.compile(pat, flags)
    except re.error as e:
        try:
            pat2 = re.sub(r"(\?|\*|\+)\1+", r"\1", pat)
            return re.compile(pat2, flags)
        except:
            sys.stderr.write(f"grep: invalid regex '{pat}': {e}\n"); sys.exit(2)

def main():
    argv = sys.argv[1:]
    opts, patterns, files = parse_args(argv)
    if not patterns:
        sys.stderr.write("grep: no pattern\n"); sys.exit(2)
    compiled = [compile_pattern(p, opts) for p in patterns]
    if not files:
        files = ["-"]
    multi = len(files) > 1
    if opts["H"] is None:
        opts["H"] = multi
    exit_code = 1
    out_lines = []
    for fpath in files:
        if fpath == "-":
            try:
                data = sys.stdin.read()
                lines = data.splitlines()
                src_name = "(standard input)"
            except:
                continue
        else:
            if os.path.isdir(fpath):
                sys.stderr.write(f"grep: {fpath}: Is a directory\n"); continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
                src_name = fpath
            except FileNotFoundError:
                sys.stderr.write(f"grep: {fpath}: No such file or directory\n"); continue
            except Exception as e:
                sys.stderr.write(f"grep: {fpath}: {e}\n"); continue
        for idx, line in enumerate(lines, 1):
            matched = False
            match_objs = []
            for cre in compiled:
                if opts["x"]:
                    m = cre.fullmatch(line)
                    if m:
                        matched = True
                        match_objs.append(m)
                        break
                else:
                    if opts["o"]:
                        for m in cre.finditer(line):
                            match_objs.append(m)
                        if match_objs:
                            matched = True
                            break
                    else:
                        m = cre.search(line)
                        if m:
                            matched = True
                            match_objs.append(m)
                            break
            if opts["v"]:
                matched = not matched
                match_objs = []
            if not matched:
                continue
            exit_code = 0
            if opts["q"]:
                sys.exit(0)
            if opts["c"] or opts["l"] or opts["L"]:
                continue
            if opts["o"] and not opts["v"]:
                for m in match_objs:
                    text = m.group(0)
                    prefix = ""
                    if opts["H"]:
                        prefix += f"{src_name}:"
                    if opts["n"]:
                        prefix += f"{idx}:"
                    out_lines.append(f"{prefix}{text}")
            else:
                prefix = ""
                if opts["H"]:
                    prefix += f"{src_name}:"
                if opts["n"]:
                    prefix += f"{idx}:"
                out_lines.append(f"{prefix}{line}")
    if opts["q"]:
        sys.exit(exit_code)
    if out_lines:
        sys.stdout.write("\n".join(out_lines) + ("\n" if out_lines else ""))
        sys.exit(0)
    else:
        sys.exit(exit_code)
if __name__ == "__main__":
    main()
