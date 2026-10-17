#!/usr/bin/env python3
import sys, re, os
ret = 0
apkbuild = ""

def violation(msg, line, tag):
    global ret
    if os.getenv("SKIP_AL"+tag):
        return
    ret += 1
    sys.stdout.write(f"SC:[AL{tag}]:{apkbuild}:{line}:{msg}\n")

def readFile(path):
    linenum = 0
    try:
        f = open(path, 'r', encoding='utf-8', errors='ignore')
    except:
        return None
    y = None
    while True:
        line = f.readline()
        if not line:
            break
        # strip trailing \n and \r
        line = line.rstrip("\r\n")
        if re.match(r"^# secfixes", line):
            y = {}
            linenum += 1
            if re.match(r"^# secfixes$", line):
                violation("missing colon on '"+line[2:]+"'", linenum, "37")
                line = line + ":"
            # inner loop: collect # lines
            while line is not None and re.match(r"^#", line):
                # l = line without "# "
                if line.startswith("# "):
                    l = line[2:]
                elif line == "#":
                    l = ""
                else:
                    l = line[1:]  # fallback
                # keep original l with leading spaces
                # Check pkgver-pkgrel indentation
                # if (not l:match("^%s%s") or l:match("^%s%s%s"))
                if (not re.match(r"^\s\s", l) or re.match(r"^\s\s\s", l)):
                    le = re.sub(r"^\s+", "", l)
                    if re.match(r"^\d\S*\-r", le):
                        violation("pkgver-pkgrel indentation is 3 whitespaces", linenum, "48")
                        l = re.sub(r"^", "  ", le, count=1)
                        # also check missing colon after fixing indent
                        if re.match(r"^\d\S*[^:]$", le):
                            violation("missing colon on '"+le+"'", linenum, "38")
                            l = l + ":"
                if (re.match(r"^\s\s", l) and re.match(r"^\s\s\d", l)):
                    if (re.match(r"^\s\s\d\S*\-r", l) and re.match(r"^\s\s\d\S*[^:]$", l)):
                        violation("missing colon on '"+re.sub(r"^\s+", "", l)+"'", linenum, "38")
                        l = l + ":"
                # Check security identifier indentation
                if (not re.match(r"^\s\s\s\s", l) or re.match(r"^\s\s\s\s\s", l)):
                    le = re.sub(r"^\s+", "", l)
                    if re.match(r"^- ", le):
                        violation("Security identifier identation is 5 whitespaces", linenum, "47")
                        l = re.sub(r"^", "    ", le, count=1)
                if (re.match(r"^\s\s\s\s", l) and not re.match(r"^\s\s\s\s- ", l)):
                    # missing hyphen, but only if line looks like identifier
                    stripped = re.sub(r"^\s+", "", l)
                    if stripped and not stripped.startswith("-"):
                        # check if stripped looks like identifier (contains - or alphanumeric)
                        if re.match(r"^[A-Z0-9\-]+", stripped):
                            violation("missing hyphen on '"+stripped+"'", linenum, "41")
                            l = re.sub(r"^\s+", "    - ", l)
                y[linenum] = l
                # read next
                pos = f.tell()
                nxt = f.readline()
                if not nxt:
                    line = None
                    break
                line = nxt.rstrip("\r\n")
                # strip \r already
                linenum += 1
                continue
            f.close()
            return y
        linenum += 1
    f.close()
    return None

def checkRel(s, line):
    if "0" in s:
        return
    if not re.match(r".*-r\d+:$", s):
        violation("invalid pkgrel", line, "40")
    if (not re.match(r"^\d[\d\.\-_a-zA-Z]*:$", s) and not re.match(r"^\d[\d\.\-_a-zA-Z]*-r*:$", s)):
        violation("invalid pkgver", line, "39")

def checkGNUTLS(s,line):
    s=re.sub(r"^GNUTLS-SA","",s)
    if len(s)==0:
        violation("GNUTLS-SA ID is empty",line,"51")
        return
    if not re.match(r"^-[\d\-]*$",s):
        violation("GNUTLS-SA ID is not composed of only digits and hyphens",line,"51")
    if not re.match(r"^-\d\d\d\d",s):
        violation("GNUTLS-SA ID has a bad year, it needs to be in YYYY format",line,"51")
    # month check: Lua if not str:match("^%-.-%-%d%d%-") then bad month else check 1-12
    if not re.match(r"^-.*?-\d\d-",s):
        violation("GNUTLS-SA ID has a bad month, it needs to be in MM format",line,"51")
    else:
        m=re.search(r"^-.*?-(\d\d)",s)
        if m:
            try:
                month=int(m.group(1))
                if month<1 or month>12:
                    violation("GNUTLS-SA ID has invalid month, it must be between 01 and 12",line,"51")
            except:
                pass
    # day check: Lua if not str:match("^%-.-%-.-%-%d%d$") then bad day else check 1-31
    if not re.match(r"^-.*?-.*?-\d\d$",s):
        violation("GNUTLS-SA ID has a bad day, it needs to be in DD format",line,"51")
    else:
        m=re.search(r"^-.*?\-.*?\-(\d\d)",s)
        if m:
            try:
                day=int(m.group(1))
                if day<1 or day>31:
                    violation("GNUTLS-SA ID has a bad day, it needs to be between 01 and 31",line,"51")
            except:
                pass
    if s.count("-") != 3:
        violation("GNUTLS-SA ID must have exactly 4 hyphens",line,"51")
def checkXSA(s, line):
    s = re.sub(r"^XSA", "", s)
    if len(s) == 0:
        violation("XSA ID is empty", line, "53")
    if not re.match(r"^\-\d*$", s):
        violation("XSA ID only have integers after the initial XSA-", line, "53")
    n = s.count("-")
    if n != 1:
        violation("XSA IDs must have exactly 1 hyphen", line, "53")

def checkCVE(s, line):
    s = re.sub(r"^CVE", "", s)
    if len(s) == 0:
        violation("CVE ID is empty", line, "50")
    if not re.match(r"^\-[\d\-]*$", s):
        violation("CVE ID only have integers and hyphens after the initial CVE", line, "50")
    if not re.match(r"^\-\d\d\d\d\-", s):
        violation("CVE ID does not have year in 4 digit YYYY format", line, "50")
    if not re.match(r"^-.*?-\d\d\d\d+$", s):
        violation("CVE ID does not have at least 4 digits at the end", line, "50")
    n = s.count("-")
    if n != 2:
        violation("CVE IDs must have exactly 2 hyphens", line, "50")

def checkGHSL(s, line):
    s = re.sub(r"^GHSL", "", s)
    if len(s) == 0:
        violation("GHSL ID is empty", line, "63")
    if not re.match(r"^\-[\d\-]*$", s):
        violation("GHSL ID only have integers and hyphens after the initial GHSL", line, "63")
    if not re.match(r"^\-\d\d\d\d\-", s):
        violation("GHSL ID does not have year in 4 digit YYYY format", line, "63")
    n = s.count("-")
    if n != 2:
        violation("GHSL IDs must have exactly 2 hyphens", line, "63")

# main
if __name__ == "__main__":
    for arg in sys.argv[1:]:
        apkbuild = arg
        table = readFile(apkbuild)
        if table:
            identifiers = {}
            for k, v in table.items():
                if re.match(r"^\s\s\S", v):
                    checkRel(re.sub(r"^\s+", "", v), k)
                elif re.match(r"^\s\s\s\s\S", v):
                    # strip leading "    - "
                    vv = re.sub(r"^\s+\- ", "", v)
                    vv = re.sub(r"\(.*?\)", "", vv)  # strip parentheses
                    for splitv in re.findall(r"[^ ]+", vv):
                        if not splitv:
                            continue
                        if re.match(r"^CVE", splitv):
                            checkCVE(splitv, k)
                            identifiers[k] = v
                        elif re.match(r"^GNUTLS-SA", splitv):
                            checkGNUTLS(splitv, k)
                            identifiers[k] = v
                        elif re.match(r"^XSA", splitv):
                            checkXSA(splitv, k)
                            identifiers[k] = v
                        elif re.match(r"^GHSL", splitv):
                            checkGHSL(splitv, k)
                            identifiers[k] = v
                        else:
                            violation(f"unknown security identifier '{splitv}'", k, "52")
            # duplicate check
            seen = []
            for line, value in list(identifiers.items()):
                vv = re.sub(r"^\s+\- ", "", value)
                vv = re.sub(r"\(.*?\)", "", vv)
                for splitv in re.findall(r"[^ ]+", vv):
                    if not splitv:
                        continue
                    if splitv in seen:
                        continue
                    if re.match(r"^GNUTLS-SA", splitv):
                        seen.append(splitv)
                        continue
                    saw = False
                    for l2, v2 in identifiers.items():
                        if l2 == line:
                            continue
                        vv2 = re.sub(r"^\s+\- ", "", v2)
                        vv2 = re.sub(r"\(.*?\)", "", vv2)
                        for sv in re.findall(r"[^ ]+", vv2):
                            if sv == splitv:
                                violation(f"duplicate value '{sv}'", l2, "59")
                                saw = True
                    if saw:
                        violation(f"duplicate value '{splitv}'", line, "59")
                    seen.append(splitv)
    sys.exit(ret)
