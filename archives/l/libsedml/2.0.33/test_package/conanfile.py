import json
import os
from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def _ensure_writable_tmp(self):
        # Mirror of the main recipe: /tmp is read-only on OHOS, the direct
        # clang++ invocation spills temporaries via TMPDIR. Reuse the
        # HMBS-injected dir when writable, else fall back under the build
        # folder. Temp root only; test logic unchanged.
        cands = []
        for _k in ("TMPDIR", "TMP", "TEMP"):
            try:
                _v = os.environ.get(_k, "")
            except Exception:
                _v = ""
            if _v:
                cands.append(_v)
        try:
            _home = os.environ.get("HOME", "")
        except Exception:
            _home = ""
        if _home:
            cands.append(os.path.join(_home, "tmp"))
        try:
            if self.build_folder:
                cands.append(os.path.join(str(self.build_folder),
                                          "hmbs-tmp"))
        except Exception:
            pass
        for _c in cands:
            try:
                os.makedirs(_c, exist_ok=True)
                _probe = os.path.join(_c, ".hmbs_write_probe")
                with open(_probe, "w", encoding="utf-8") as _f:
                    _f.write("ok")
                try:
                    os.remove(_probe)
                except Exception:
                    pass
                for _k in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
                    try:
                        os.environ[_k] = _c
                    except Exception:
                        pass
                self.output.info("test_package writable tmp: %s" % _c)
                return _c
            except Exception:
                continue
        self.output.warning("test_package: no writable tmp among %s" % cands)
        return ""

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self._ensure_writable_tmp()
        import shutil
        dep = self.dependencies["libsedml"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        self.output.info("test_package cpp_info.libs=%s libdirs=%s "
                         "system_libs=%s" % (dep.libs, dep.libdirs,
                                             dep.system_libs))
        # Resolve every static archive to an absolute path and verify it
        # exists before linking. The 2026-09-16 preflight linked with no
        # visible sedml archive and failed with `undefined symbol:
        # SedDocument::...` for every Sed class; absolute paths plus an
        # explicit pre-link inventory make that failure mode loud instead
        # of a wall of undefined symbols.
        abs_libs = []
        search_dirs = list(dep.libdirs)
        for d in search_dirs:
            try:
                entries = sorted(os.listdir(d))
            except Exception:
                entries = []
            self.output.info("test_package libdir %s: %s" % (d, entries))
        for lib in dep.libs:
            hit = None
            for d in search_dirs:
                for ext in (".a", ".so"):
                    cand = os.path.join(d, "lib%s%s" % (lib, ext))
                    if os.path.isfile(cand):
                        hit = cand
                        break
                if hit:
                    break
            if hit is None:
                raise Exception(
                    "test_package: archive for -l%s not found in %s "
                    "(consumer link cannot succeed)" % (lib, search_dirs))
            self.output.info("test_package link archive: %s (%d bytes)"
                             % (hit, os.path.getsize(hit)))
            abs_libs.append('"%s"' % hit)
        if not any("sedml" in a for a in abs_libs):
            raise Exception(
                "test_package: no sedml archive in link list %s" % dep.libs)
        # --start-group/--end-group makes the static chain
        # (sedml -> numl -> sbml -> expat) order-insensitive and tolerates
        # any circular references between the vendored archives.
        grouped = "-Wl,--start-group %s -Wl,--end-group" % " ".join(abs_libs)
        syslibs = " ".join(["-l" + l for l in dep.system_libs])
        # Resolve CXX: profile conf first (validated), then CXX env,
        # then PATH lookup (HMBS injects tool dirs into PATH).
        cxx = ""
        try:
            cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                default="", check_type=str)
        except Exception:
            cxx = ""
        if not (cxx and os.path.isfile(cxx) and os.access(cxx, os.X_OK)):
            env_cxx = os.environ.get("CXX", "")
            if env_cxx and os.path.isfile(env_cxx) and os.access(env_cxx, os.X_OK):
                cxx = env_cxx
            elif env_cxx and shutil.which(env_cxx):
                cxx = shutil.which(env_cxx)
            else:
                cxx = shutil.which("clang++") or shutil.which("c++") or "clang++"
        self.run('%s -std=c++11 test_sedml.cpp -o test_sedml %s %s %s'
                 % (cxx, inc, grouped, syslibs))

    def test(self):
        self._ensure_writable_tmp()
        if can_run(self):
            self.run("./test_sedml", env="conanrun")
            # Cache-hit rounds skip the main build() so no fresh upstream
            # marker is emitted there. Re-emit the measured build-time
            # result persisted in the package (res/hmbs_upstream.json) via
            # both channels. Missing/invalid file only warns, never fakes.
            try:
                pkg = str(self.dependencies["libsedml"].package_folder)
                up_path = os.path.join(pkg, "res", "hmbs_upstream.json")
                obj = None
                if os.path.isfile(up_path):
                    with open(up_path, "r", encoding="utf-8") as rf:
                        obj = json.loads(rf.read())
                if (isinstance(obj, dict)
                        and obj.get("status") == "passed"
                        and int(obj.get("discovered", 0)) > 0
                        and int(obj.get("executed", 0)) > 0):
                    line = ("HMBS_UPSTREAM_TEST_RESULT="
                            + json.dumps(obj, separators=(",", ":")))
                    self.output.info(line)
                    try:
                        print(line, flush=True)
                    except Exception:
                        pass
                else:
                    self.output.warning(
                        "test_package: persisted upstream evidence missing "
                        "or invalid at %s; cannot re-emit" % up_path)
            except (OSError, ValueError) as e:
                self.output.warning(
                    "test_package: re-emit upstream evidence failed: %s" % e)
