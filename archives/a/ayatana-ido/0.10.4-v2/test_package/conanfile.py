#!/usr/bin/env python3
"""Conan test_package — ayatana-ido 0.10.4-v2 consumer test.

Upstream libayatana-ido3-0.4.pc declares Requires: gtk+-3.0 glib-2.0, and
gtk+-3.0 transitively needs pango->harfbuzz (hb.h). PkgConfigDeps generated
.pc files plus pkg_check_modules(IMPORTED_TARGET) propagate the transitive
include/lib paths (same approach as the gtk/3.24.43 recipe), avoiding
CMakeDeps component-graph breakage (hb.h not found).

The test binary is executed headless on the broadway backend (broadwayd from
the gtk package); its stdout is captured and the per-check "menu item OK"
lines are counted for the HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
"""
import json
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps

# test.c performs exactly 2 checks (calendar + entry menu item), each printing
# one "menu item OK" line on success.
CONSUMER_CHECK_COUNT = 2


class AyatanaidoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 (22nd round, same as main recipe): force Linux platform
        # name so cmake 4.4.3 without Platform/HarmonyOS.cmake can
        # configure; plus Experience-1 compiler fallback. Consumer
        # test has no OHOS-specific branches, alias is safe.
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _conf_cxx = None
        if isinstance(_exes, dict):
            _conf_c = _exes.get("c")
            _conf_cxx = (_exes.get("cpp") or _exes.get("cxx")
                         or _exes.get("c"))
        for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++")):
            if _conf_val and (os.path.sep in str(_conf_val)
                              or "/" in str(_conf_val)):
                try:
                    _ok = (os.path.isfile(str(_conf_val))
                           and os.access(str(_conf_val), os.X_OK))
                except Exception:
                    _ok = False
                if not _ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % _conf_val)
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
            elif not _conf_val:
                _which = shutil.which(_bare)
                if _which:
                    # Only pin when the historical absolute path is
                    # missing; otherwise keep the toolchain default.
                    _abs = ("/data/service/hnp/bin/clang"
                            if _bare == "clang"
                            else "/data/service/hnp/bin/clang++")
                    try:
                        _abs_ok = (os.path.isfile(_abs)
                                   and os.access(_abs, os.X_OK))
                    except Exception:
                        _abs_ok = False
                    if not _abs_ok:
                        tc.variables[_key] = _which
        _pkg_exe = self._pkg_config_exe()
        if _pkg_exe:
            tc.variables["PKG_CONFIG_EXECUTABLE"] = _pkg_exe
            self.output.info("test_package using pkg-config: %s" % _pkg_exe)
        else:
            _shim = self._write_pkg_config_shim()
            _py = shutil.which("python3") or "python3"
            tc.variables["PKG_CONFIG_EXECUTABLE"] = "%s;%s" % (_py, _shim)
            self.output.info(
                "test_package: no system pkg-config; using in-recipe shim")
            _pkg_exe = _shim
        try:
            from conan.tools.env import Environment as _Env
            _uniq = self._pkg_config_pc_dirs()
            if _uniq:
                _e = _Env()
                _e.define("PKG_CONFIG_PATH", os.pathsep.join(_uniq))
                _e.vars(self).save_script("hmbs_pkgconfig_path")
        except Exception:
            pass
        tc.generate()
        # The published glib package's glib-2.0.pc lacks -lintl in Libs while
        # libayatana-ido3-0.4.so references g_libintl_ngettext; same precedent
        # as gtk/3.24.43: append -lintl to the generated glib-2.0.pc Libs, or
        # the test executable fails to link with undefined reference
        # (--no-allow-shlib-undefined enforced).
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(pc):
            content = open(pc, encoding="utf-8").read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            new_content = "".join(lines)
            if new_content != content:
                open(pc, "w", encoding="utf-8", newline="\n").write(new_content)

    def _pkg_config_exe(self):
        """Locate a runnable pkg-config (pcre2/10.47 precedent).

        The worker PATH has no pkg-config/pkgconf (preflight proves the
        generic PATH + dep-bindirs probe finds nothing), but the HNP
        toolchain ships a preinstalled pkg-config at a fixed absolute
        path (same constant as archives/p/pcre2/10.47/test_package).
        Candidates are verified runnable via --version; the first that
        prints a version wins. Returns "" when none qualifies.
        """
        import shutil as _shutil
        import subprocess as _sp
        cands = [
            os.environ.get("PKG_CONFIG"),
            _shutil.which("pkg-config"),
            _shutil.which("pkgconf"),
        ]
        for _c in cands:
            if not _c or not os.path.isfile(_c):
                continue
            try:
                _p = _sp.run(
                    [_c, "--version"],
                    stdout=_sp.PIPE, stderr=_sp.PIPE,
                    text=True, timeout=10, check=False,
                )
            except Exception:
                continue
            if _p.returncode == 0 and (_p.stdout or "").strip():
                return _c
        return ""


    def _pkg_config_pc_dirs(self):
        dirs = []
        try:
            gf = self.generators_folder
            if gf and os.path.isdir(gf):
                dirs.append(gf)
        except Exception:
            pass
        try:
            for dep in self.dependencies.values():
                try:
                    pf = dep.package_folder
                except Exception:
                    continue
                if not pf:
                    continue
                for sub in ("lib/pkgconfig", "lib64/pkgconfig",
                            "share/pkgconfig"):
                    d = os.path.join(pf, sub)
                    try:
                        if os.path.isdir(d):
                            dirs.append(d)
                    except Exception:
                        pass
        except Exception:
            pass
        seen = set()
        uniq = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    def _write_pkg_config_shim(self):
        path = os.path.join(self.build_folder, "hmbs-pkgconfig.py")
        try:
            src = self._pkg_config_shim_source()
            baked = self._pkg_config_pc_dirs()
            if baked:
                lit = "[" + ", ".join([chr(34) + b.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34)) + chr(34) for b in baked]) + "]"
                src = src.replace("_BAKED_DIRS = []", "_BAKED_DIRS = " + lit, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(src)
        except Exception:
            pass
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        return path

    def _pkg_config_shim_source(self):
        L = [
            "#!/usr/bin/env python3",
            "import os",
            "import re",
            "import sys",
            "PKG_VERSION = \"0.29.2\"",
            "_BAKED_DIRS = []",
            "def _search_dirs():",
            "    dirs = []",
            "    for key in (\"PKG_CONFIG_PATH\", \"PKG_CONFIG_LIBDIR\"):",
            "        val = os.environ.get(key, \"\")",
            "        if val:",
            "            dirs.extend(val.split(os.pathsep))",
            "    try:",
            "        for d in _BAKED_DIRS:",
            "            if d: dirs.append(d)",
            "    except Exception:",
            "        pass",
            "    for d in (\"/usr/lib/pkgconfig\", \"/usr/share/pkgconfig\",",
            "              \"/usr/local/lib/pkgconfig\",",
            "              \"/usr/local/share/pkgconfig\"):",
            "        dirs.append(d)",
            "    out = []",
            "    for d in dirs:",
            "        if d and d not in out:",
            "            out.append(d)",
            "    return out",
            "def _find_pc(name, dirs):",
            "    for d in dirs:",
            "        p = os.path.join(d, name + \".pc\")",
            "        try:",
            "            if os.path.isfile(p):",
            "                return p",
            "        except Exception:",
            "            pass",
            "    return \"\"",
            "def _expand(text, vars):",
            "    pat = re.compile(r\"\\$\\{([^}]+)\\}|\\$([A-Za-z0-9_]+)\")",
            "    for _ in range(10):",
            "        m = pat.search(text)",
            "        if not m:",
            "            break",
            "        key = m.group(1) or m.group(2)",
            "        text = text[:m.start()] + vars.get(key, \"\") + text[m.end():]",
            "    return text",
            "def _parse_pc(path):",
            "    vars = {}",
            "    fields = {}",
            "    try:",
            "        fh = open(path, encoding=\"utf-8\", errors=\"replace\")",
            "    except Exception:",
            "        return vars, fields",
            "    with fh:",
            "        for raw in fh:",
            "            line = raw.strip()",
            "            if not line or line.startswith(\"#\"):",
            "                continue",
            "            if \"=\" in line and (\":\" not in line or line.index(\"=\") < line.index(\":\")):",
            "                k, v = line.split(\"=\", 1)",
            "                vars[k.strip()] = v.strip()",
            "            elif \":\" in line:",
            "                k, v = line.split(\":\", 1)",
            "                fields[k.strip()] = v.strip()",
            "    return vars, fields",
            "def _ver_parts(v):",
            "    parts = []",
            "    for tok in re.split(r\"[.\\-_+]\", v.strip()):",
            "        m = re.match(r\"(\\d+)(.*)\", tok)",
            "        if m:",
            "            parts.append((0, int(m.group(1)), m.group(2)))",
            "        else:",
            "            parts.append((1, 0, tok))",
            "    return parts",
            "def _ver_cmp(a, b):",
            "    pa, pb = _ver_parts(a), _ver_parts(b)",
            "    n = min(len(pa), len(pb))",
            "    for i in range(n):",
            "        if pa[i] != pb[i]:",
            "            return -1 if pa[i] < pb[i] else 1",
            "    if len(pa) != len(pb):",
            "        return -1 if len(pa) < len(pb) else 1",
            "    return 0",
            "def _check_op(have, op, want):",
            "    c = _ver_cmp(have, want)",
            "    if op == \"=\": return c == 0",
            "    if op == \"==\": return c == 0",
            "    if op == \"!=\": return c != 0",
            "    if op == \">\": return c > 0",
            "    if op == \">=\": return c >= 0",
            "    if op == \"<\": return c < 0",
            "    if op == \"<=\": return c <= 0",
            "    return False",
            "def _load(name, dirs):",
            "    pc = _find_pc(name, dirs)",
            "    if not pc:",
            "        return None",
            "    vars, fields = _parse_pc(pc)",
            "    return {\"vars\": vars, \"fields\": fields}",
            "def _req_names(entry, with_private):",
            "    req = entry[\"fields\"].get(\"Requires\", \"\")",
            "    if with_private:",
            "        priv = entry[\"fields\"].get(\"Requires.private\", \"\")",
            "        if priv: req = (req + \", \" + priv).strip(\", \")",
            "    names = []",
            "    ops = (\"=\", \"==\", \"!=\", \">\", \">=\", \"<\", \"<=\")",
            "    for chunk in req.replace(\",\", \" \").split():",
            "        if chunk in ops: continue",
            "        if names and re.fullmatch(r\"[0-9][A-Za-z0-9.\\-_+]*\", chunk): continue",
            "        names.append(chunk)",
            "    return names",
            "def _field(entry, key, with_private):",
            "    val = entry[\"fields\"].get(key, \"\")",
            "    if with_private and key in (\"Libs\", \"Cflags\"):",
            "        priv = entry[\"fields\"].get(key + \".private\", \"\")",
            "        if priv: val = (val + \" \" + priv).strip()",
            "    return _expand(val, entry[\"vars\"])",
            "def _collect(names, dirs, with_private):",
            "    order = []",
            "    seen = set()",
            "    entries = {}",
            "    ok = [True]",
            "    def visit(n):",
            "        if n in seen: return",
            "        seen.add(n)",
            "        e = _load(n, dirs)",
            "        if e is None:",
            "            ok[0] = False",
            "            return",
            "        entries[n] = e",
            "        for r in _req_names(e, with_private):",
            "            visit(r)",
            "        order.append(n)",
            "    for n in names:",
            "        visit(n)",
            "    if not ok[0]: return None",
            "    cflags = []",
            "    libs = []",
            "    for n in order:",
            "        for tok in _field(entries[n], \"Cflags\", with_private).split():",
            "            if tok not in cflags: cflags.append(tok)",
            "        for tok in _field(entries[n], \"Libs\", with_private).split():",
            "            if tok not in libs: libs.append(tok)",
            "    return (cflags, libs, entries)",
            "def _bare(tok):",
            "    m = re.match(r\"^([A-Za-z0-9_\\+.\\-]+?)((?:>=|<=|==|!=|=|>|<).*)?$\", tok)",
            "    if m: return m.group(1)",
            "    return tok",
            "def _split_mods(args):",
            "    names = []",
            "    cons = []",
            "    ops = (\"=\", \"==\", \"!=\", \">\", \">=\", \"<\", \"<=\")",
            "    i = 0",
            "    while i < len(args):",
            "        a = args[i]",
            "        if a.startswith(\"-\"):",
            "            i += 1",
            "            continue",
            "        m = re.match(r\"^([A-Za-z0-9_\\+.\\-]+?)\\s*(>=|<=|==|!=|=|>|<)\\s*(.+)$\", a)",
            "        if m:",
            "            names.append(m.group(1))",
            "            cons.append((m.group(1), m.group(2), m.group(3)))",
            "            i += 1",
            "            continue",
            "        if i + 2 < len(args) and args[i+1] in ops:",
            "            names.append(_bare(a))",
            "            cons.append((_bare(a), args[i+1], args[i+2]))",
            "            i += 3",
            "        else:",
            "            names.append(_bare(a))",
            "            i += 1",
            "    return names, cons",
            "def main():",
            "    args = sys.argv[1:]",
            "    if not args or \"--help\" in args:",
            "        print(\"Usage: hmbs-pkgconfig.py [options] [modules]\")",
            "        return 0",
            "    mods_only = [a for a in args if not a.startswith(\"-\")]",
            "    if \"--version\" in args and not mods_only:",
            "        print(PKG_VERSION)",
            "        return 0",
            "    for idx, a in enumerate(args):",
            "        if a.startswith(\"--atleast-pkgconfig-version=\"):",
            "            want = a.split(\"=\", 1)[1]",
            "            return 0 if _ver_cmp(PKG_VERSION, want) >= 0 else 1",
            "        if a == \"--atleast-pkgconfig-version\" and idx + 1 < len(args):",
            "            return 0 if _ver_cmp(PKG_VERSION, args[idx+1]) >= 0 else 1",
            "    defines = {}",
            "    rest = []",
            "    i = 0",
            "    while i < len(args):",
            "        if args[i].startswith(\"--define-variable=\"):",
            "            kv = args[i].split(\"=\", 1)[1]",
            "            if \"=\" in kv:",
            "                k, v = kv.split(\"=\", 1)",
            "                defines[k] = v",
            "        elif args[i] == \"--define-variable\" and i + 1 < len(args):",
            "            kv = args[i+1]",
            "            if \"=\" in kv:",
            "                k, v = kv.split(\"=\", 1)",
            "                defines[k] = v",
            "            i += 1",
            "        else:",
            "            rest.append(args[i])",
            "        i += 1",
            "    args = rest",
            "    with_static = \"--static\" in args",
            "    want_exists = \"--exists\" in args",
            "    want_cflags = \"--cflags\" in args",
            "    want_libs = \"--libs\" in args",
            "    want_i = \"--cflags-only-I\" in args",
            "    want_o = \"--cflags-only-other\" in args",
            "    want_L = \"--libs-only-L\" in args",
            "    want_l = \"--libs-only-l\" in args",
            "    want_lo = \"--libs-only-other\" in args",
            "    modversion = \"--modversion\" in args",
            "    variable = \"\"",
            "    for a in args:",
            "        if a.startswith(\"--variable=\"):",
            "            variable = a.split(\"=\", 1)[1]",
            "    pr = \"--print-requires\" in args",
            "    prp = \"--print-requires-private\" in args",
            "    atleast = \"\"",
            "    exact = \"\"",
            "    for idx, a in enumerate(args):",
            "        if a.startswith(\"--atleast-version=\"): atleast = a.split(\"=\", 1)[1]",
            "        elif a == \"--atleast-version\" and idx + 1 < len(args): atleast = args[idx+1]",
            "        if a.startswith(\"--exact-version=\"): exact = a.split(\"=\", 1)[1]",
            "        elif a == \"--exact-version\" and idx + 1 < len(args): exact = args[idx+1]",
            "    names, cons = _split_mods(args)",
            "    dirs = _search_dirs()",
            "    if variable and len(names) == 1:",
            "        e = _load(names[0], dirs)",
            "        if e is None:",
            "            sys.stderr.write(\"Package \" + names[0] + \" was not found\\n\")",
            "            return 1",
            "        merged = dict(e[\"vars\"])",
            "        merged.update(defines)",
            "        print(_expand(merged.get(variable, \"\"), merged))",
            "        return 0",
            "    entries = {}",
            "    for n in names:",
            "        e = _load(n, dirs)",
            "        if e is None:",
            "            sys.stderr.write(\"Package \" + n + \" was not found\\n\")",
            "            return 1",
            "        entries[n] = e",
            "    for (n, op, want) in cons:",
            "        have = entries[n][\"fields\"].get(\"Version\", \"\")",
            "        if not _check_op(have, op, want):",
            "            sys.stderr.write(\"Requested '\" + n + \" \" + op + \" \" + want + \"' but version of \" + n + \" is \" + have + \"\\n\")",
            "            return 1",
            "    if atleast or exact:",
            "        if len(names) != 1: return 1",
            "        have = entries[names[0]][\"fields\"].get(\"Version\", \"\")",
            "        if atleast and _ver_cmp(have, atleast) < 0: return 1",
            "        if exact and _ver_cmp(have, exact) != 0: return 1",
            "        return 0",
            "    if pr or prp:",
            "        out = []",
            "        for n in names:",
            "            req = entries[n][\"fields\"].get(\"Requires\", \"\")",
            "            if prp:",
            "                priv = entries[n][\"fields\"].get(\"Requires.private\", \"\")",
            "                if priv: req = (req + \", \" + priv).strip(\", \")",
            "            if req: out.append(req)",
            "        print(\" \".join(out))",
            "        return 0",
            "    if modversion and not (want_cflags or want_libs):",
            "        print(\" \".join([entries[n][\"fields\"].get(\"Version\", \"\") for n in names]))",
            "        return 0",
            "    if want_exists and not (want_cflags or want_libs or modversion or variable):",
            "        return 0",
            "    res = _collect(names, dirs, with_static)",
            "    if res is None:",
            "        sys.stderr.write(\"Package dependency missing\\n\")",
            "        return 1",
            "    cflags, libs, entries2 = res",
            "    if modversion:",
            "        print(\" \".join([entries[n][\"fields\"].get(\"Version\", \"\") for n in names]))",
            "        return 0",
            "    outs = []",
            "    if want_cflags or want_i or want_o:",
            "        if want_i: outs.append(\" \".join([x for x in cflags if x.startswith(\"-I\")]))",
            "        elif want_o: outs.append(\" \".join([x for x in cflags if not x.startswith(\"-I\")]))",
            "        else: outs.append(\" \".join(cflags))",
            "    if want_libs or want_L or want_l or want_lo:",
            "        if want_L: outs.append(\" \".join([x for x in libs if x.startswith(\"-L\")]))",
            "        elif want_l: outs.append(\" \".join([x for x in libs if x.startswith(\"-l\")]))",
            "        elif want_lo: outs.append(\" \".join([x for x in libs if not (x.startswith(\"-L\") or x.startswith(\"-l\"))]))",
            "        else: outs.append(\" \".join(libs))",
            "    if outs:",
            "        print(\" \".join([o for o in outs if o]).strip())",
            "        return 0",
            "    return 0",
            "if __name__ == \"__main__\":",
            "    sys.exit(main())",
        ]
        return "\n".join(L) + "\n"

    def build(self):
        # E002: keep cmake/clang temp files off read-only /tmp.
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Make every transitive shared library reachable at runtime by
        # injecting all dependency libdirs into LD_LIBRARY_PATH (does not rely
        # on implicit conanrun injection): gtk/pango/cairo pull in
        # libsharpyuv/libatk/libglib/libintl/libfribidi etc., otherwise
        # "Error loading shared library libsharpyuv.so.0" fails relocation.
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            dep_libdirs + ([existing] if existing else [])
        )
        self.output.info("injected LD_LIBRARY_PATH: %d dep libdirs" % len(dep_libdirs))

        # Headless environment (CI/HarmonyOS PC): serve the broadway backend
        # with broadwayd from the gtk package, else gtk_init fails with
        # "cannot open display".
        broadwayd = None
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
        if broadwayd and os.path.isfile(broadwayd):
            proc = subprocess.Popen(
                [broadwayd, ":5"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Readiness wait: poll liveness, up to 10x0.5s (a fixed sleep is
            # too short on slow-start CI runners; an early exit keeps the
            # diagnostics instead of hanging).
            for _ in range(10):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            if proc.poll() is None:
                os.environ["GDK_BACKEND"] = "broadway"
                os.environ["BROADWAY_DISPLAY"] = ":5"
            else:
                self.output.warning(
                    "broadwayd not ready (rc=%s); display may be unavailable"
                    % proc.returncode
                )
                proc = None
        try:
            cmake = CMake(self)
            cmake.test()
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ayatana-ido")
            if not os.path.isfile(bin_path):
                raise ConanException("test binary missing: %s" % bin_path)
            run = subprocess.run(
                [bin_path],
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            output = run.stdout or ""
            self.output.info(output[-2000:])
            ok_count = output.count("menu item OK")
            marker = {
                "executed": True,
                "passed": run.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
                "command": bin_path,
                "discovered": CONSUMER_CHECK_COUNT,
                "passedCount": ok_count,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            if not marker["passed"]:
                raise ConanException(
                    "consumer test failed: rc=%s ok=%s/%s"
                    % (run.returncode, ok_count, CONSUMER_CHECK_COUNT)
                )
            # L0d quality gate: real test execution (gtk/3.24.43 precedent).
            # Validated via subprocess capture above; this run proves the
            # binary executes under the conanrun environment while
            # broadwayd is still serving.
            self.run(bin_path, env="conanrun")
            # Cache-hit re-emit: when Conan reuses the main-package binary,
            # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
            # prints. Re-print the persisted real result (written by build()
            # into package res/hmbs_upstream.json) every run so the evidence
            # gate sees it. No test is redefined here; counts are the real
            # in-build gtest numbers (4 TEST_F).
            try:
                _upstream = None
                _pkg_name = (self.tested_reference_str.split("/")[0]
                             if "/" in self.tested_reference_str else "ayatana-ido")
                try:
                    _dep = self.dependencies[_pkg_name]
                    _pf = getattr(_dep, "package_folder", None)
                    if _pf:
                        _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
                        if os.path.isfile(_cand):
                            with open(_cand, "r", encoding="utf-8") as _fh:
                                _upstream = json.load(_fh)
                except Exception:
                    _upstream = None
                if isinstance(_upstream, dict) and _upstream.get("discovered"):
                    _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(_upstream, ensure_ascii=False))
                    print(_umsg, flush=True)
                    self.output.info(_umsg)
                else:
                    self.output.warning(
                        "persisted hmbs_upstream.json missing; "
                        "upstream evidence only available on fresh build")
            except Exception as _e:
                self.output.warning("upstream re-emit failed: %r" % (_e,))
        finally:
            if proc is not None:
                proc.terminate()
