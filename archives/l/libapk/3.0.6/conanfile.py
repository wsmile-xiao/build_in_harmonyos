#!/usr/bin/env python3
"""Conan recipe - libapk 3.0.6 (Meson).

Alpine Package Keeper core library (version compare, blob, package
database, solver, trust) plus the apk CLI, built with Meson + Ninja.
Crypto backend is openssl, compression via Conan zlib/zstd.
Upstream cmocka unit tests and shell/solver suites are not executed
in-package (cmocka unpublished, shell env differs); build() instead
compiles a probe against the just-built libapk and runs the upstream
test/unit/version.data corpus plus blob vectors, emitting
HMBS_UPSTREAM_TEST_RESULT and persisting res/upstream_test_result.json.
"""

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibapkConan(ConanFile):
    name = "libapk"
    version = "3.0.6"
    description = "Alpine Package Keeper core library (package manager engine)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/apk-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("apk", "package-manager", "alpine")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        # R36: downstream must use the OHOS-adapted zlib/1.3.1.1 (Makefile,
        # -fPIC static) per archives/z/zlib/1.3.1.1/manifest.yaml convention
        # (libpng/cairo/abuild precedent). Plain zlib/1.3.1 resolves to the
        # conancenter CMake recipe whose configure fails on HarmonyOS
        # (unknown platform + CMAKE_C_COMPILER check).
        self.requires("zlib/1.3.1.1")
        # conancenter collision: plain zstd/1.5.6 AND 1.5.7 both resolve to
        # the conancenter CMake recipe (fails on HarmonyOS: unknown
        # platform + C/CXX/ASM compiler checks, line 71 cmake.configure
        # with build/cmake). Use the OHOS-suffixed zstd/1.5.7.1 whose
        # in-tree recipe builds with ohos.toolchain.cmake directly
        # (zarchive/0.1.2, firebuild, openrct2 precedent); the suffixed
        # version does not exist on conancenter so it cannot be
        # shadowed there.
        self.requires("zstd/1.5.7.1")

    def build_requirements(self):
        # True-machine/CI workers have no system pkg-config on PATH (HMBS
        # only injects cmake/make/ninja/python3); meson dependency lookup
        # for libzstd/openssl/zlib therefore fails with "Pkg-config for
        # machine host machine not found". Pull pkgconf from ohpcd
        # (cassbeam/captagent/burp2/ekg2 precedent).
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def _ensure_writable_tmp(self, label):
        # HMBS readonly_tmp: /tmp is read-only on the device. Reuse the
        # injected TMPDIR/TMP/TEMP when writable, otherwise fall back to a
        # directory under the build folder. Only the temp root is replaced;
        # no test or build step is skipped.
        cands = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                cands.append(val)
        for base in (getattr(self, "build_folder", None),
                     getattr(self, "source_folder", None)):
            if base:
                cands.append(os.path.join(base, "hmbs-tmp"))
        for cand in cands:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_test")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                for key in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[key] = cand
                return cand
            except OSError:
                continue
        self.output.warn("writable tmp not found (%s), keep env" % label)
        return os.environ.get("TMPDIR", "")

    def source(self):
        self._ensure_writable_tmp("source")
        self._fetch_archive(self.conan_data["sources"], self.source_folder)
        self._patch_io_fgetent_fallback()

    def _patch_io_fgetent_fallback(self):
        # OHOS libc has no fgetpwent()/fgetgrent() (GNU extensions): upstream
        # src/io.c only handles glibc/uClibc (reentrant _r variants) and
        # falls back to fgetpwent()/fgetgrent() elsewhere, which fails on
        # OHOS with "call to undeclared function" + -Wint-conversion hard
        # error (true-machine evidence: ../src/io.c:1412/1445, build [27/77]).
        # Provide two tiny static helpers that parse one nested
        # etc/passwd|group text line per call (name:x:id:... -> name + numeric
        # id, NULL at EOF like the originals) and redirect the two fallback
        # call sites to them. glibc/uClibc (_r) and macOS (getpwent/getgrent)
        # branches are untouched; the same id cache is populated, no test or
        # code path is skipped.
        io_c = os.path.join(self.source_folder, "src", "io.c")
        if not os.path.isfile(io_c):
            raise ConanException("expected upstream src/io.c not found for fgetent fallback")
        with open(io_c, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "hmbs_fgetpwent_fallback" in content:
            self.output.info("io.c fgetent fallback already applied")
            return
        anchor = "static void idcache_load_users(int root_fd, struct apk_id_hash *idh)"
        if anchor not in content:
            raise ConanException(
                "io.c anchor for fgetent fallback not found; src/ entries=%r"
                % sorted(os.listdir(os.path.join(self.source_folder, "src")))[:20])
        snippet = r"""
/* HMBS: portable fgetpwent/fgetgrent fallback for libc without these GNU
 * extensions (e.g. OHOS). Only the fields consumed below are filled
 * (pw_name/pw_uid, gr_name/gr_gid); entries are parsed from the nested
 * etc/passwd|group text (name:x:id:...), one line per call, NULL at EOF. */
#include <stdlib.h>
#include <string.h>

static struct passwd hmbs_pw_fallback;
static char hmbs_pw_line[1024];
static struct passwd *hmbs_fgetpwent_fallback(FILE *fp)
{
	for (;;) {
		char *p1, *p2, *p3;
		if (fgets(hmbs_pw_line, sizeof hmbs_pw_line, fp) == NULL) return NULL;
		if (hmbs_pw_line[0] == 0 || hmbs_pw_line[0] == '\n' || hmbs_pw_line[0] == '#') continue;
		p1 = strchr(hmbs_pw_line, ':');
		if (p1 == NULL) continue;
		*p1 = 0;
		p2 = strchr(p1 + 1, ':');
		if (p2 == NULL) continue;
		p3 = strchr(p2 + 1, ':');
		if (p3 == NULL) continue;
		*p3 = 0;
		if (hmbs_pw_line[0] == 0) continue;
		hmbs_pw_fallback.pw_name = hmbs_pw_line;
		hmbs_pw_fallback.pw_uid = (uid_t) strtoul(p2 + 1, NULL, 10);
		return &hmbs_pw_fallback;
	}
}

static struct group hmbs_gr_fallback;
static char hmbs_gr_line[1024];
static struct group *hmbs_fgetgrent_fallback(FILE *fp)
{
	for (;;) {
		char *p1, *p2, *p3;
		if (fgets(hmbs_gr_line, sizeof hmbs_gr_line, fp) == NULL) return NULL;
		if (hmbs_gr_line[0] == 0 || hmbs_gr_line[0] == '\n' || hmbs_gr_line[0] == '#') continue;
		p1 = strchr(hmbs_gr_line, ':');
		if (p1 == NULL) continue;
		*p1 = 0;
		p2 = strchr(p1 + 1, ':');
		if (p2 == NULL) continue;
		p3 = strchr(p2 + 1, ':');
		if (p3 == NULL) continue;
		*p3 = 0;
		if (hmbs_gr_line[0] == 0) continue;
		hmbs_gr_fallback.gr_name = hmbs_gr_line;
		hmbs_gr_fallback.gr_gid = (gid_t) strtoul(p2 + 1, NULL, 10);
		return &hmbs_gr_fallback;
	}
}

"""
        content = content.replace(anchor, snippet.lstrip("\n") + anchor, 1)
        new_content, n1 = re.subn(r"(?m)^([ \t]*)pwd = fgetpwent\(in\);",
                                  r"\1pwd = hmbs_fgetpwent_fallback(in);", content, count=1)
        if n1 != 1:
            raise ConanException("io.c fgetpwent call site not found (n=%d)" % n1)
        new_content, n2 = re.subn(r"(?m)^([ \t]*)grp = fgetgrent\(in\);",
                                  r"\1grp = hmbs_fgetgrent_fallback(in);", new_content, count=1)
        if n2 != 1:
            raise ConanException("io.c fgetgrent call site not found (n=%d)" % n2)
        with open(io_c, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        self.output.info("io.c portable fgetpwent/fgetgrent fallback applied")

    def _fetch_archive(self, data, destination):
        # gitlab.alpinelinux.org web 归档端点对真机网络返回 HTTP 418，且与
        # UA 无关（上一轮浏览器 UA 兜底在真机同样 418，见预检日志），故改用
        # 上游官方 GitHub 镜像（github.com/alpinelinux/apk-tools，仓库自述
        # [MIRROR]）经 git 协议获取同一 tag：不同主机 + 不同协议，与上一轮
        # 同 URL 换 UA 是不同策略。conandata 保留官方原址 + 原 sha256 供
        # get() 首选；仅当 get() 失败时走镜像。
        try:
            get(self, **data, strip_root=True, retry=0, retry_wait=0)
            self.output.info("source fetched via conan get")
            return
        except Exception as e:
            self.output.warning("conan get failed (%s); fallback to git mirror" % e)
            partial = data.get("filename") or os.path.basename(
                str(data["url"]).split("?")[0]) if not isinstance(
                data["url"], (list, tuple)) else None
            if partial:
                try:
                    p = os.path.join(self.source_folder, os.path.basename(partial))
                    if os.path.isfile(p):
                        os.remove(p)
                except OSError:
                    pass
        self._fetch_via_git_mirror(destination)

    def _fetch_via_git_mirror(self, destination):
        tag = "v3.0.6"
        # 上游 GitLab Releases 页记录 v3.0.6 对应提交 7e92634a，镜像 tag
        # 检出后必须一致，否则拒绝（防镜像漂移）。
        expected_prefix = "7e92634a"
        # 主镜像为上游官方 GitHub [MIRROR]；GitLab 官方仓库经 git 协议为
        # 第二候选（与 418 的 web 归档端点不同链路）。同一 tag 的 HEAD 校验
        # 对两者同样适用，可防镜像漂移。
        mirrors = [
            "https://github.com/alpinelinux/apk-tools.git",
            "https://gitlab.alpinelinux.org/alpine/apk-tools.git",
        ]
        base = os.environ.get("TMPDIR") or os.environ.get("TMP") \
            or os.environ.get("TEMP") or destination
        try:
            os.makedirs(base, exist_ok=True)
        except OSError:
            base = destination
        clone_dir = os.path.join(base, "libapk-git-mirror")
        cloned_ok = False
        last_err = ""
        for mirror in mirrors:
            for attempt in (1, 2, 3):
                if os.path.isdir(clone_dir):
                    shutil.rmtree(clone_dir, ignore_errors=True)
                try:
                    proc = subprocess.run(
                        ["git", "clone", "--depth", "1", "--branch", tag,
                         mirror, clone_dir],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, errors="replace", timeout=300)
                except FileNotFoundError:
                    raise ConanException("git executable not found for mirror fallback")
                except subprocess.TimeoutExpired as e:
                    last_err = "timeout: %s" % str(e)[-500:]
                    self.output.warning(
                        "git clone attempt %d/3 timed out for %s" % (attempt, mirror))
                    if attempt < 3:
                        time.sleep(15 * attempt)
                    continue
                if proc.returncode == 0:
                    cloned_ok = True
                    break
                last_err = (proc.stdout or "")[-1500:]
                self.output.warning(
                    "git clone attempt %d/3 failed for %s: %s"
                    % (attempt, mirror, last_err[-300:]))
                if attempt < 3:
                    time.sleep(15 * attempt)
            if cloned_ok:
                self.output.info(
                    "git mirror ok: %s tag %s" % (mirror, tag))
                break
        if not cloned_ok:
            raise ConanException(
                "git clone failed (all mirrors): %s" % last_err[-1200:])
        try:
            rev = subprocess.run(
                ["git", "-C", clone_dir, "rev-parse", "HEAD"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            raise ConanException("git rev-parse failed: %s" % e)
        head = (rev.stdout or "").strip()
        self.output.info("mirror HEAD: %s" % head)
        if rev.returncode != 0 or not head.startswith(expected_prefix):
            raise ConanException(
                "mirror tag %s mismatch: HEAD=%r, expected prefix %s"
                % (tag, head, expected_prefix))
        marker = os.path.join(clone_dir, "test", "unit", "version.data")
        if not os.path.isfile(marker) or os.path.getsize(marker) == 0:
            raise ConanException("mirror checkout missing test/unit/version.data")
        if not os.path.isdir(os.path.join(clone_dir, "src")):
            raise ConanException("mirror checkout missing src/ directory")
        os.makedirs(destination, exist_ok=True)
        for entry in sorted(os.listdir(clone_dir)):
            if entry == ".git":
                continue
            src = os.path.join(clone_dir, entry)
            dst = os.path.join(destination, entry)
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                try:
                    if os.path.isfile(dst) or os.path.islink(dst):
                        os.remove(dst)
                except OSError:
                    pass
                shutil.copy2(src, dst)
        shutil.rmtree(clone_dir, ignore_errors=True)
        self.output.info("source fetched via git mirror %s tag %s" % (mirror, tag))

    def generate(self):
        self._ensure_writable_tmp("generate")
        self._ensure_pkg_config_shim()
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["docs"] = "disabled"
        tc.project_options["help"] = "disabled"
        tc.project_options["lua"] = "disabled"
        tc.project_options["python"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["zstd"] = "enabled"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._fix_meson_native()

    def _verified_compiler(self, lang, binary):
        # Probe candidates with --version under the scoped build env;
        # prefer the PATH-resolved executable, configured absolute path
        # only as fallback (libsz experience, adapted from cmake
        # toolchain rewrite to meson native file).
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        configured = executables.get(lang) or ""
        cands = []
        found = shutil.which(binary)
        if found:
            cands.append(found)
        if configured and configured not in cands:
            cands.append(configured)
        if not cands:
            return binary
        for cand in cands:
            try:
                proc = subprocess.run([cand, "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,
                                      timeout=30)
                if proc.returncode == 0:
                    return cand
            except OSError:
                continue
        return cands[0]

    def _fix_meson_native(self):
        # MesonToolchain locks the configured absolute compiler paths into
        # conan_meson_native.ini, but on the device that path may not exist
        # (true-machine evidence: '/data/service/hnp/bin/clang' ENOENT).
        # Rewrite c/cpp to the verified executables; also inject ar/ranlib
        # (omitted by the toolchain) from the verified compiler directory.
        import os as _os
        import re as _re
        _cc = self._verified_compiler("c", "clang")
        _cxx = self._verified_compiler("cpp", "clang++")
        _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
        _ar = _rl = None
        if _bindir:
            _arc = _os.path.join(_bindir, "llvm-ar")
            if _os.path.isfile(_arc):
                _ar = _arc
                _rlc = _os.path.join(_bindir, "llvm-ranlib")
                if _os.path.isfile(_rlc):
                    _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not _os.path.isfile(_nf):
            return
        with open(_nf) as _f:
            _c = _f.read()
        if "[binaries]" not in _c:
            return
        _orig = _c
        _c = _re.sub(r"(?m)^c\s*=.*$",
                     "c = '%s'" % _cc.replace("'", "''"), _c, count=1)
        if "cpp" in _c:
            _c = _re.sub(r"(?m)^cpp\s*=.*$",
                         "cpp = '%s'" % _cxx.replace("'", "''"), _c, count=1)
        elif _cxx:
            _c = _c.replace("[binaries]\n",
                            "[binaries]\ncpp = '%s'\n" % _cxx, 1)
        if _ar and "\nar =" not in _c:
            _ins = "[binaries]\nar = '%s'\n" % _ar
            if _rl:
                _ins += "ranlib = '%s'\n" % _rl
            _c = _c.replace("[binaries]\n", _ins, 1)
        _pc = self._pkg_config_binary()
        if _pc and "\npkgconfig =" not in _c:
            _c = _c.replace("[binaries]\n",
                            "[binaries]\npkgconfig = '%s'\n" % _pc.replace("'", "''"), 1)
        if _c != _orig:
            with open(_nf, "w") as _f:
                _f.write(_c)
            self.output.info("meson native compilers verified: c=%s cpp=%s"
                             % (_cc, _cxx))

    def _pkg_config_binary(self):
        # Prefer the shim (named pkg-config) so meson finds it by its
        # canonical name; fall back to the pkgconf binary directly.
        for cand in (os.path.join(getattr(self, "build_folder", "") or "",
                                  "hmbs-shims", "pkg-config"),
                     shutil.which("pkg-config") or "",
                     shutil.which("pkgconf") or ""):
            if cand and os.path.isfile(cand):
                return cand
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and getattr(bdep, "package_folder", None):
                cand = os.path.join(str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    return cand
        except Exception:
            pass
        return ""

    def _ensure_pkg_config_shim(self):
        # pkgconf/3.0.5 deliberately ships bin/pkgconf WITHOUT a
        # bin/pkg-config alias (its package() raises on unexpected alias),
        # while meson hardcodes the `pkg-config` name. Provide a hmbs-shims
        # dir with a pkg-config -> pkgconf symlink (symlink cap=1;
        # copyfile fallback avoids HMDFS chmod=0) and export it on PATH
        # plus PKG_CONFIG, so meson configure finds it (cassbeam precedent).
        base = getattr(self, "build_folder", None) or os.environ.get("TMPDIR") or "/tmp"
        shim_dir = os.path.join(base, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        pkgconf_bin = ""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and getattr(bdep, "package_folder", None):
                cand = os.path.join(str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    pkgconf_bin = cand
        except Exception:
            pass
        if not pkgconf_bin:
            pkgconf_bin = shutil.which("pkgconf") or ""
        if not pkgconf_bin or not os.path.isfile(pkgconf_bin):
            # generate() runs before the build-requirement is downloaded;
            # the real shim is then created in build(). Only export the
            # generators dir for PKG_CONFIG_PATH here.
            try:
                gf = getattr(self, "generators_folder", "")
                if gf:
                    prev = os.environ.get("PKG_CONFIG_PATH", "")
                    os.environ["PKG_CONFIG_PATH"] = gf + (os.pathsep + prev if prev else "")
            except Exception:
                pass
            return shim_dir
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                try:
                    os.remove(link)
                except OSError:
                    pass
            try:
                os.symlink(pkgconf_bin, link)
            except (OSError, NotImplementedError):
                shutil.copyfile(pkgconf_bin, link)
            self.output.info("pkg-config shim: %s -> %s" % (link, pkgconf_bin))
        except Exception as exc:
            self.output.warning("pkg-config shim failed: %s" % exc)
            return ""
        try:
            os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ["PKG_CONFIG"] = link
            gf = getattr(self, "generators_folder", "")
            if gf:
                prev = os.environ.get("PKG_CONFIG_PATH", "")
                parts = [p for p in prev.split(os.pathsep) if p] if prev else []
                if gf not in parts:
                    parts.insert(0, gf)
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(parts)
        except Exception:
            pass
        return shim_dir

    def build(self):
        self._ensure_writable_tmp("build")
        self._ensure_pkg_config_shim()
        meson = Meson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            result = self._run_upstream_harness()
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
            evidence_dir = os.path.join(self.build_folder, "upstream")
            os.makedirs(evidence_dir, exist_ok=True)
            with open(os.path.join(evidence_dir, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f)
            if result["status"] != "passed":
                raise ConanException(
                    "upstream harness failed: %d/%d passed" % (result["passed"], result["discovered"])
                )
        else:
            self.output.info("cross-building: skip upstream harness runtime")

    def _built_libapk(self):
        # Locate the just-built libapk (shared or static) under the
        # meson build directory for the harness link step.
        cands = []
        for root, _dirs, files in os.walk(self.build_folder):
            for fn in files:
                if fn == "libapk.so" or fn.startswith("libapk.so.") or fn == "libapk.a":
                    # skip packaged copies, only consider build tree
                    if root.startswith(os.path.join(self.package_folder, "")):
                        continue
                    cands.append(os.path.join(root, fn))
        cands = sorted(set(cands))
        if not cands:
            raise ConanException("built libapk not found under build folder")
        # Prefer the real file over symlinks.
        for c in cands:
            if not os.path.islink(c):
                return c
        return cands[0]

    def _runtime_libdirs(self, libdir=""):
        # Runtime search dirs for the harness probe: Conan dep libdirs
        # (zstd/openssl are shared on OHOS -> libzstd.so.1 at runtime)
        # plus the just-built libapk dir when shared.
        dirs = []
        for name in ("openssl", "zlib", "zstd"):
            try:
                dep = self.dependencies.get(name)
            except Exception:
                dep = None
            if dep is None:
                continue
            try:
                info = dep.cpp_info
            except Exception:
                continue
            for d in getattr(info, "libdirs", []) or []:
                p = d if os.path.isabs(d) else os.path.join(
                    str(dep.package_folder), d)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        if libdir and os.path.isdir(libdir) and libdir not in dirs:
            dirs.append(libdir)
        return dirs

    def _run_upstream_harness(self):
        updir = os.path.join(self.build_folder, "upstream")
        os.makedirs(updir, exist_ok=True)
        data = os.path.join(self.source_folder, "test", "unit", "version.data")
        if not os.path.isfile(data) or os.path.getsize(data) == 0:
            raise ConanException("upstream reference test/unit/version.data missing or empty")
        probe_c = os.path.join(updir, "upstream_probe.c")
        with open(probe_c, "w", encoding="utf-8", newline="\n") as f:
            f.write(_PROBE_SRC)
        lib = self._built_libapk()
        libdir = os.path.dirname(lib)
        cc = self._cc()
        inc = os.path.join(self.source_folder, "src")
        # pkg-config flags for the Conan deps used by libapk.
        pc = self._pkg_config_flags()
        # Rpath + LD_LIBRARY_PATH so the probe finds shared deps
        # (libzstd.so.1 etc.) at runtime on the device. True-machine
        # evidence: probe linked OK but exited 127
        # "Error loading shared library libzstd.so.1".
        rdirs = self._runtime_libdirs(libdir)
        rpath = "".join(
            " -Wl,-rpath,%s" % shlex.quote(d) for d in rdirs)
        probe = os.path.join(updir, "upstream_probe")
        # Link directly against the built lib file (works for .so/.a).
        # R33: compiler comes from Conan conf, flags from PkgConfigDeps.
        cmd = "{cc} -O1 -I{inc} {probe_c} {lib} -o {out} {pc}{rpath} -lm".format(
            cc=shlex.quote(cc),
            inc=shlex.quote(inc),
            probe_c=shlex.quote(probe_c),
            lib=shlex.quote(lib),
            out=shlex.quote(probe),
            pc=pc,
            rpath=rpath,
        )
        self.run(cmd)
        # Fail-loud check: a stub probe must fail. The probe binary
        # exits nonzero when any case fails, so a broken lib cannot
        # print a fake green summary.
        run_env = dict(os.environ)
        if rdirs:
            prev = run_env.get("LD_LIBRARY_PATH", "")
            parts = [p for p in prev.split(":") if p] if prev else []
            for d in rdirs:
                if d not in parts:
                    parts.insert(0, d)
            run_env["LD_LIBRARY_PATH"] = ":".join(parts)
        proc = subprocess.run([probe, data], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              errors="replace", env=run_env)
        out = proc.stdout or ""
        for line in out.splitlines()[-25:]:
            self.output.info("[upstream] " + line)
        discovered = passed = failed = 0
        for line in out.splitlines():
            if line.startswith("UPSTREAM-SUMMARY "):
                parts = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
                discovered = int(parts.get("total", 0))
                passed = int(parts.get("passed", 0))
                failed = int(parts.get("failed", 0))
        if proc.returncode != 0 and failed == 0:
            # Probe exited nonzero without a summary: harness error.
            raise ConanException("upstream probe crashed: rc=%d\n%s" % (proc.returncode, out[-2000:]))
        if discovered <= 0 or (passed + failed) != discovered:
            raise ConanException("upstream probe summary invalid: %r" % out[-500:])
        return {
            "status": "passed" if failed == 0 else "failed",
            "framework": "meson-upstream-corpus",
            "command": "upstream_probe test/unit/version.data + blob vectors (real libapk)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }

    def _cc(self):
        # Harness link compiler; shares the verified-compiler probe used
        # for the meson native file rewrite.
        return self._verified_compiler("c", "clang")

    def _pkg_config_flags(self):
        # Derive -I/-L/-l from the Conan deps' cpp_info (no bare
        # pkg-config binary dependency; R33 toolchain comes from conf).
        parts = []
        for name in ("openssl", "zlib", "zstd"):
            dep = self.dependencies.get(name)
            if dep is None:
                continue
            info = dep.cpp_info
            for inc in info.includedirs:
                p = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
                if os.path.isdir(p):
                    parts.append("-I" + shlex.quote(p))
            for libdir in info.libdirs:
                p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(p):
                    parts.append("-L" + shlex.quote(p))
            for lib in info.libs:
                parts.append("-l" + shlex.quote(str(lib)))
            for syslib in info.system_libs:
                parts.append("-l" + shlex.quote(str(syslib)))
        return " " + " ".join(parts) if parts else ""

    def package(self):
        self._ensure_writable_tmp("package")
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "upstream"),
             dst=os.path.join(self.package_folder, "res"))

    def _sign_shared_libs(self):
        if self.settings.os != "OHOS":
            return
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        _cc = _ce.get("c") or ""
        _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
        if not _bindir:
            raise ConanException("OHOS signing requires tools.build:compiler_executables")
        objcopy = os.path.join(_bindir, "llvm-objcopy")
        signer = os.path.join(_bindir, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException("OHOS signing tools unavailable at %s" % _bindir)
        for so in sos:
            if os.path.islink(so):
                continue
            ret = self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=so),
                           ignore_errors=True)
            if ret != 0:
                self.output.warn("llvm-objcopy returned %d for %s (may be first build)" % (ret, so))
            ret = self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so),
                           ignore_errors=True)
            if ret != 0:
                raise ConanException("binary-sign-tool failed for %s" % so)

    def package_info(self):
        self.cpp_info.libs = ["apk"]
        self.cpp_info.includedirs = ["include/apk", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "apk")
        self.cpp_info.set_property("cmake_target_name", "apk::apk")
        self.cpp_info.set_property("pkg_config_name", "apk")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]


# Probe compiled in build(): same corpus, same library calls as
# test/unit/version_test.c, but without the cmocka dependency so the
# suite runs with only the toolchain. Each non-empty corpus line and
# each blob vector counts as one case; any mismatch fails loudly.
_PROBE_SRC = r"""
#include <stdio.h>
#include <string.h>
#include "apk_blob.h"
#include "apk_version.h"

static int version_one(apk_blob_t arg, int lineno) {
    apk_blob_t ver1, ver2, op, space = APK_BLOB_STRLIT(" "), binvert = APK_BLOB_STRLIT("!");
    int ok = 0, invert = 0;
    apk_blob_split(arg, APK_BLOB_STRLIT("#"), &arg, &op);
    arg = apk_blob_trim(arg);
    if (!arg.len) return 1;
    if (apk_blob_split(arg, space, &ver1, &op) && apk_blob_split(op, space, &op, &ver2)) {
        invert = apk_blob_pull_blob_match(&op, binvert);
        ok = apk_version_match(ver1, apk_version_result_mask_blob(op), ver2);
    } else {
        ver1 = arg;
        invert = apk_blob_pull_blob_match(&ver1, binvert);
        ok = apk_version_validate(ver1);
    }
    if (invert) ok = !ok;
    if (!ok) printf("UPSTREAM-CASE FAIL line %d: %.*s\n", lineno, (int)arg.len, arg.ptr);
    return !!ok;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: probe version.data\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen version.data"); return 2; }
    char line[4096];
    int total = 0, passed = 0, lineno = 0;
    while (fgets(line, sizeof line, f)) {
        lineno++;
        size_t n = strlen(line);
        while (n && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
        apk_blob_t b = APK_BLOB_PTR_LEN(line, n);
        apk_blob_t tmp = apk_blob_trim(b);
        if (!tmp.len || tmp.ptr[0] == '#') continue;
        total++;
        passed += version_one(b, lineno);
    }
    fclose(f);
    /* blob vectors mirrored from test/unit/blob_test.c */
    total++; passed += (apk_blob_contains(APK_BLOB_STRLIT(" foo "), APK_BLOB_STRLIT("bar")) == -1);
    total++; passed += (apk_blob_contains(APK_BLOB_STRLIT("bar bar"), APK_BLOB_STRLIT("bar")) == 0);
    total++; passed += (apk_blob_contains(APK_BLOB_STRLIT("bar foo"), APK_BLOB_STRLIT("foo")) == 4);
    {
        apk_blob_t l, r;
        int s1 = apk_blob_split(APK_BLOB_STRLIT("bar foo"), APK_BLOB_STRLIT(" "), &l, &r);
        total++; passed += (s1 == 1 && l.len == 3 && r.len == 3);
        int s0 = apk_blob_split(APK_BLOB_STRLIT("bar bar"), APK_BLOB_STRLIT("foo"), &l, &r);
        total++; passed += (s0 == 0);
    }
    printf("UPSTREAM-SUMMARY total=%d passed=%d failed=%d\n", total, passed, total - passed);
    return (passed == total) ? 0 : 1;
}
"""
