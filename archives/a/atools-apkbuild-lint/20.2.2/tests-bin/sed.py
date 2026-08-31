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

def compile_bre(pat):
    pat = bre_to_ere(pat)
    try:
        return re.compile(pat)
    except re.error as e:
        sys.stderr.write(f"sed: invalid regex '{pat}': {e}\n")
        sys.exit(2)

def parse_s_command(s):
    if not s or s[0] != 's':
        return None
    delim = s[1]
    i = 2
    pat = ""
    while i < len(s):
        if s[i] == "\\" and i+1 < len(s):
            if s[i+1] == delim:
                pat += s[i+1]
                i += 2
            else:
                pat += s[i:i+2]
                i += 2
        elif s[i] == delim:
            i += 1
            break
        else:
            pat += s[i]
            i += 1
    else:
        return None
    repl = ""
    while i < len(s):
        if s[i] == "\\" and i+1 < len(s):
            if s[i+1] == delim:
                repl += s[i+1]
                i += 2
            else:
                repl += s[i:i+2]
                i += 2
        elif s[i] == delim:
            i += 1
            break
        else:
            repl += s[i]
            i += 1
    flags = s[i:] if i < len(s) else ""
    return pat, repl, flags

def apply_sub(line, pat, repl, flags):
    cre = compile_bre(pat)
    py_repl = ""
    i = 0
    while i < len(repl):
        if repl[i] == "\\" and i+1 < len(repl):
            nxt = repl[i+1]
            if nxt == "&":
                py_repl += "&"
                i += 2
            elif nxt.isdigit():
                py_repl += "\\" + nxt
                i += 2
            elif nxt == "\\":
                py_repl += "\\\\"
                i += 2
            else:
                py_repl += repl[i:i+2]
                i += 2
        elif repl[i] == "&":
            py_repl += "\\g<0>"
            i += 1
        else:
            if repl[i] == "\\":
                py_repl += "\\\\"
            else:
                py_repl += repl[i]
            i += 1
    count = 0 if "g" in flags else 1
    try:
        if count == 0:
            return cre.sub(py_repl, line)
        else:
            return cre.sub(py_repl, line, count=1)
    except Exception as e:
        sys.stderr.write(f"sed: sub failed: {e}\n")
        return line

def parse_range(script):
    s = script.strip()
    if not s:
        return None
    if not s.endswith("p"):
        return None
    s = s[:-1].rstrip()
    if ",/" in s:
        if s[0] not in ("/", "~", "|", "#"):
            return None
        delim1 = s[0]
        i = 1
        pat1 = ""
        while i < len(s):
            if s[i] == "\\" and i+1 < len(s):
                pat1 += s[i:i+2]
                i += 2
            elif s[i] == delim1:
                i += 1
                break
            else:
                pat1 += s[i]
                i += 1
        if i >= len(s) or s[i] != ",":
            return None
        i += 1
        if i >= len(s) or s[i] not in ("/", "~", "|", "#"):
            return None
        delim2 = s[i]
        i += 1
        pat2 = ""
        while i < len(s):
            if s[i] == "\\" and i+1 < len(s):
                pat2 += s[i:i+2]
                i += 2
            elif s[i] == delim2:
                i += 1
                break
            else:
                pat2 += s[i]
                i += 1
        return (pat1, pat2, True)
    else:
        if s[0] not in ("/", "~", "|", "#"):
            return None
        delim = s[0]
        i = 1
        pat = ""
        while i < len(s):
            if s[i] == "\\" and i+1 < len(s):
                pat += s[i:i+2]
                i += 2
            elif s[i] == delim:
                i += 1
                break
            else:
                pat += s[i]
                i += 1
        return (pat, None, False)

def main():
    argv = sys.argv[1:]
    n_flag = False
    r_flag = False
    scripts = []
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            files.extend(argv[i+1:])
            break
        if a == "-n":
            n_flag = True
            i += 1
        elif a == "-r" or a == "-E":
            r_flag = True
            i += 1
        elif a.startswith("-e"):
            if a == "-e":
                i += 1
                if i < len(argv):
                    scripts.append(argv[i])
                    i += 1
                else:
                    sys.stderr.write("sed: -e requires argument\n"); sys.exit(2)
            else:
                scripts.append(a[2:])
                i += 1
        elif a.startswith("-") and len(a) > 1:
            for ch in a[1:]:
                if ch == "n":
                    n_flag = True
                elif ch in ("r","E"):
                    r_flag = True
            i += 1
        else:
            if not scripts and not files:
                if os.path.isfile(a) and not any(c in a for c in ["s","/","p","d"]):
                    if any(x in a for x in ["s","/","p"]):
                        scripts.append(a)
                    else:
                        files.append(a)
                else:
                    if scripts:
                        files.append(a)
                    else:
                        if a.startswith("s") or a.startswith("/"):
                            scripts.append(a)
                        else:
                            files.append(a)
                i += 1
            else:
                files.append(a)
                i += 1
    if not scripts:
        sys.stderr.write("sed: no script\n"); sys.exit(2)
    if not files:
        files = ["-"]
    for fpath in files:
        if fpath == "-":
            lines = sys.stdin.read().splitlines()
        else:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
            except FileNotFoundError:
                sys.stderr.write(f"sed: can't read {fpath}: No such file or directory\n"); continue
        in_range = False
        range_start_pat = None
        range_end_pat = None
        range_cre_start = None
        range_cre_end = None
        s_scripts = []
        range_script = None
        for sc in scripts:
            if ",/" in sc and sc.strip().endswith("p"):
                range_script = sc
            elif sc.strip().endswith("p") and sc.strip().startswith("/"):
                range_script = sc
            else:
                s_scripts.append(sc)
        if range_script:
            parsed = parse_range(range_script)
            if parsed:
                pat1, pat2, is_range = parsed
                range_start_pat = pat1
                range_end_pat = pat2
                def comp(p):
                    if p is None:
                        return None
                    if not r_flag:
                        p2 = bre_to_ere(p)
                    else:
                        p2 = p
                    try:
                        return re.compile(p2)
                    except:
                        return re.compile(p)
                range_cre_start = comp(range_start_pat)
                range_cre_end = comp(range_end_pat) if is_range else None
        for line in lines:
            out = line
            for sc in s_scripts:
                parsed = parse_s_command(sc)
                if parsed:
                    pat, repl, flags = parsed
                    out = apply_sub(out, pat, repl, flags)
            if n_flag:
                if range_script:
                    if not in_range:
                        if range_cre_start and range_cre_start.search(line):
                            in_range = True
                            sys.stdout.write(out + "\n")
                            if range_cre_end is None:
                                in_range = False
                            # GNU range end is searched on the NEXT line, not same line.
                            # Checking start line for end would close a multi-line block
                            # such as options=" ... " immediately (both contain \") and
                            # cause fallback detection of invalid options to miss lines.
                            # Therefore do not test range_cre_end here.
                    else:
                        sys.stdout.write(out + "\n")
                        if range_cre_end and range_cre_end.search(line):
                            in_range = False
                else:
                    pass
            else:
                if range_script and n_flag:
                    continue
                sys.stdout.write(out + "\n")
if __name__ == "__main__":
    main()
