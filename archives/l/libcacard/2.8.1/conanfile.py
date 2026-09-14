#!/usr/bin/env python3
"""Conan recipe — libcacard 2.8.1 (Meson).

CAC (Common Access Card) library that provides emulation of smart cards
to a virtual card reader (SPICE project, formerly part of QEMU).

OHOS adaptation notes:
- Meson is the upstream-supported build path (same choice as pcsc-lite
  2.4.0 and libslirp 4.9.3 in this repo); the shipped autotools
  `configure` is not used.
- PC/SC pass-through (`pcsc` option) is disabled: it would pull
  pcsc-lite/libusb and a USB stack that is unavailable on OHOS.
- Upstream tests are enabled (`disable_tests=false`, the upstream
  default) and executed via `meson test` in build(); the hwtests pair
  registers only when pkcs11-tool/p11tool/modutil/openssl/softhsm2-util
  are all present, otherwise meson runs the 6 unconditional programs.
- `meson install` rewrites rpath and invalidates the linker
  self-signature, so installed ELF files are re-signed with
  binary-sign-tool (same handling as pcsc-lite).
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy
from conan.tools.files import export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibcacardConan(ConanFile):
    name = "libcacard"
    version = "2.8.1"
    description = (
        "CAC (Common Access Card) library that provides emulation "
        "of smart cards to a virtual card reader"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/spice/libcacard"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # NOTE (2026-09-14, cycle 7): deliberately NO per-dependency
        # option tweaks. The fix is at the requirements() level
        # (glib track selection + overrides pinning colliding leaves
        # to ohpcd-only suffixed revisions), not here.

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcacard is only supported on Linux/OHOS, "
                "got: {}".format(self.settings.os)
            )

    def requirements(self):
        # NOTE (2026-09-14, cycle 7): cycle 6 fixed remote competition
        # (pcre2/zlib overrides resolved ohpcd revisions, bzip2 left
        # the graph) but exposed the next blocker inside glib/2.88.3
        # itself: its _resolve_llvm_tools() blindly derives
        # compiler_dir/llvm-ar on OHOS and build() hard-fails when it
        # is not executable -- this preflight machine has binutils
        # `ar` but no `llvm-ar`. glib/2.84.0 instead degrades
        # gracefully (skips injection, meson falls back to PATH `ar`)
        # and is the proven libslirp/4.9.3 pairing (shared consumer +
        # static glib + flat cpp_info, CI-green). Its pins are
        # libffi/3.4.4 + pcre2/10.40 (both collide with conancenter),
        # zlib is system pre-installed (no conan edge), so override
        # only the two colliding pins to ohpcd-only suffixed revisions
        # (libffi/3.5.2 override already proven resolving in cycle 1).
        # NOTE (2026-09-14, cycle 16): NSS must be shared. The static
        # package only ships aggregator stubs (libnss.a etc); the real
        # objects live in the fully-aggregated shared libs (libnss3.so
        # etc). Linking libcacard.so against the static stubs fails
        # with undefined PK11_*/CERT_*/SECKEY_* (see nss/3.118.1
        # test_package docstring). Request shared so PkgConfigDeps
        # emits -lnss3/-lssl3/... which resolve every symbol.
        self.requires(
            "glib/2.84.0", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "nss/3.118.1",
            transitive_headers=True,
            transitive_libs=True,
            options={"shared": True},
        )
        self.requires("pcre2/10.45.1.1", override=True)
        self.requires("libffi/3.5.2", override=True)

    def build_requirements(self):
        # Preflight worker PATH provides cmake/make/ninja/python3 (HMBS)
        # but no pkg-config binary; meson setup needs one to query the
        # PkgConfigDeps-generated glib-2.0.pc. Same canonical provider as
        # libmrss/0.19.4 and libxklavier/5.4 in this repo.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # PC/SC pass-through needs pcsc-lite + libusb + USB daemon
        # support; keep the library self-contained on OHOS.
        tc.project_options["pcsc"] = "disabled"
        # Keep the upstream default: build the test programs so that
        # `meson test` in build() runs the real upstream suite.
        tc.project_options["disable_tests"] = False
        tc.pkg_config_path = self.generators_folder
        tc.generate()
        self._repair_meson_compilers()
        self._inject_ar_ranlib()
        self._inject_pkg_config()

    def build(self):
        apply_conandata_patches(self)
        # One-line diagnostic to separate environment failures
        # (toolchain/tmpfs) from recipe failures in the next log.
        self.output.info(
            "HMBS_TMPDIR=%s HMBS_CAP_CHMOD=%s HMBS_CAP_SYMLINK=%s"
            % (
                os.environ.get("TMPDIR", ""),
                os.environ.get("HMBS_CAP_CHMOD", ""),
                os.environ.get("HMBS_CAP_SYMLINK", ""),
            )
        )
        # Build under the writable TMPDIR (see _build_environment):
        # clang/meson probes otherwise spill into read-only /tmp.
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                self._sign_build_tree_tests()
            self._run_upstream_tests()
        else:
            self.output.warning(
                "Cross build: upstream test programs were built "
                "but not executed on this host."
            )
            self._persist_upstream_result({
                "status": "skipped",
                "framework": "meson",
                "command": "meson test -C {} --no-rebuild "
                           "--print-errorlogs".format(self.build_folder),
                "discovered": 6,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 6,
                "reason": "cross build: test programs built but not "
                          "executed on this host",
            })

    def package(self):
        # meson install reuses toolchain probes on some platforms;
        # keep it on the writable TMPDIR as well (readonly_tmp:
        # read-only /tmp breaks compiler temp files).
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._persist_upstream_result_into_package()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_libs()

    def package_info(self):
        # meson library('cacard', ...) produces libcacard.so / libcacard.a
        self.cpp_info.libs = ["cacard"]
        # Upstream installs headers to include/cacard/ and ships
        # libcacard.pc (filebase 'libcacard'), keep both names working
        # for consumers.
        self.cpp_info.set_property("pkg_config_name", "libcacard")
        self.cpp_info.set_property("cmake_file_name", "libcacard")
        self.cpp_info.set_property("cmake_target_name", "libcacard::cacard")
        # glib/2.84.0 has a flat cpp_info (no components, proven by the
        # merged libslirp/4.9.3 recipe which uses exactly this form).
        # nss is shared (see requirements()): propagate it so consumers
        # get the NSS run-time libs via CMakeDeps/VirtualRunEnv; the
        # shared libcacard.so has DT_NEEDED on libnss3.so etc.
        self.cpp_info.requires = ["glib::glib", "nss::nss"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # -- helpers ----------------------------------------------------

    def _build_environment(self):
        # HMBS injects a task-independent writable TMPDIR/TMP/TEMP
        # (read-only /tmp diagnosis: readonly_tmp). Prefer it when
        # present; only fall back to a build-folder tmp dir.
        for candidate in (
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ):
            if candidate and os.path.isdir(candidate):
                tmpdir = candidate
                break
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # Repaired compilers (if any) must also reach meson child
        # processes: export CC/CXX so compiler probes do not fall back
        # to the stale profile path.
        for kind, var in (("c", "CC"), ("cpp", "CXX")):
            exe = self._discover_compiler(kind)
            if exe and os.path.isfile(exe):
                env.define(var, exe)
                bindir = os.path.dirname(exe)
                if bindir and os.path.isdir(bindir):
                    try:
                        env.prepend_path("PATH", bindir)
                    except Exception:
                        pass
        # Meson looks up the pkg-config binary via PATH (or the native
        # file entry). The preflight worker PATH does not always contain
        # it, so prepend well-known locations when they exist.
        pkg_exe = self._discover_pkg_config()
        if pkg_exe and os.path.isfile(pkg_exe):
            pkgdir = os.path.dirname(pkg_exe)
            if pkgdir and os.path.isdir(pkgdir):
                try:
                    env.prepend_path("PATH", pkgdir)
                except Exception:
                    pass
        for known_dir in ("/data/service/hnp/bin", "/usr/bin"):
            if os.path.isdir(known_dir):
                try:
                    env.prepend_path("PATH", known_dir)
                except Exception:
                    pass
        try:
            env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        except Exception:
            pass
        return env

    def _discover_compiler(self, kind):
        """Return a usable compiler path for `kind` ("c"/"cpp").

        The profile value (tools.build:compiler_executables) is
        authoritative when the file exists; otherwise search CC/CXX,
        PATH and well-known HNP/SDK locations. Returns the raw
        configured value (possibly missing) when nothing usable is
        found so the original meson error is preserved.
        """
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = ""
        if isinstance(conf, dict):
            configured = (conf.get(kind) or "").strip()
        if configured and os.path.isfile(configured):
            return configured
        env_name = "CC" if kind == "c" else "CXX"
        env_val = (os.environ.get(env_name) or "").strip()
        if env_val:
            resolved = shutil.which(env_val)
            if resolved:
                return resolved
            if os.path.isfile(env_val):
                return env_val
        bare = "clang" if kind == "c" else "clang++"
        for probe in (bare, bare + "-15"):
            found = shutil.which(probe)
            if found:
                return found
        for candidate in (
            "/data/service/hnp/bin/" + bare,
            "/data/service/hnp/bin/clang",
            "/data/service/hnp/bin/clang++",
        ):
            if os.path.isfile(candidate):
                return candidate
        try:
            import glob

            for pattern in (
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/" + bare,
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang*",
            ):
                for hit in sorted(glob.glob(pattern)):
                    if os.path.isfile(hit):
                        return hit
        except Exception:
            pass
        return configured or None

    def _repair_meson_compilers(self):
        """Patch stale c/cpp paths in meson machine files.

        This round fails at libcacard's own `meson setup` (not in a
        dependency): `Unknown compiler(s): [['/data/service/hnp/bin/clang']]`
        + `Errno 2` on `clang --version`. The profile path does not exist
        on this preflight worker, so no dependency-graph change can fix it.
        Replace only entries whose file is missing; keep good paths intact
        and log every substitution for the next preflight log.
        """
        targets = []
        for filename in (
            MesonToolchain.native_filename,
            MesonToolchain.cross_filename,
        ):
            path = os.path.join(self.generators_folder, filename)
            if os.path.isfile(path):
                targets.append(path)
        if not targets:
            return
        replacements = {}
        for kind, key in (("c", "c"), ("cpp", "cpp")):
            exe = self._discover_compiler(kind)
            if exe and os.path.isfile(exe):
                replacements[key] = exe
        if not replacements:
            return
        for path in targets:
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            for key, exe in replacements.items():
                content = re.sub(
                    r"^(\s*" + key + r"\s*=\s*)(['\"])(.*?)(\2\s*(?:#.*)?)$",
                    lambda m: m.group(1) + "'{}'".format(exe)
                    if not os.path.isfile(
                        m.group(3).strip().strip("'\"")
                    )
                    else m.group(0),
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
                # Fallback for list-style entries: c = ['/bad/clang', ...]
                def _swap_list(match):
                    inner = match.group(2)
                    first = re.search(r"['\"](.*?)['\"]", inner)
                    current = first.group(1) if first else ""
                    if current and os.path.isfile(current):
                        return match.group(0)
                    self.output.info(
                        "HMBS compiler repair: {} '{}' -> '{}' in {}".format(
                            key, current, exe, os.path.basename(path)
                        )
                    )
                    if first:
                        inner = inner.replace(first.group(0),
                                              "'{}'".format(exe), 1)
                    return match.group(1) + inner + match.group(3)
                content = re.sub(
                    r"^(\s*" + key + r"\s*=\s*\[)(.*?)(\]\s*(?:#.*)?)$",
                    _swap_list,
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _resolve_archive_tool(self, tool):
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = ""
        if isinstance(conf, dict):
            configured = (conf.get(tool) or "").strip()
        if configured and os.path.isfile(configured):
            return configured
        for probe in ("llvm-" + tool, tool):
            found = shutil.which(probe)
            if found:
                return found
        for kind in ("c", "cpp"):
            exe = self._discover_compiler(kind)
            bindir = os.path.dirname(exe) if exe else ""
            if bindir:
                for name in ("llvm-" + tool, tool):
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        return candidate
        for candidate in (
            "/data/service/hnp/bin/llvm-" + tool,
            "/data/service/hnp/bin/" + tool,
        ):
            if os.path.isfile(candidate):
                return candidate
        return configured or None

    def _inject_ar_ranlib(self):
        """Meson probes the archiver as bare `llvm-ar`; on OHOS it is not
        on PATH, so inject the absolute paths into the machine files
        (same handling as the pcsc-lite recipe, extended to the cross
        file and to PATH search like the libslirp recipe)."""
        targets = []
        for filename in (
            MesonToolchain.native_filename,
            MesonToolchain.cross_filename,
        ):
            path = os.path.join(self.generators_folder, filename)
            if os.path.isfile(path):
                targets.append(path)
        if not targets:
            return
        ar = self._resolve_archive_tool("ar")
        ranlib = self._resolve_archive_tool("ranlib")
        if not ar or not os.path.isfile(ar):
            return
        for machine_file in targets:
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" in content:
                continue
            if "[binaries]" not in content:
                continue
            insert = "[binaries]\nar = '{}'\n".format(ar)
            if ranlib and os.path.isfile(ranlib):
                insert += "ranlib = '{}'\n".format(ranlib)
            content = content.replace("[binaries]\n", insert, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _pkgconf_exe_from_conan(self):
        # Cycle 7 (2026-09-14): cycles 5-6 injected only system-PATH
        # binaries and declared tool_requires, but _discover_pkg_config()
        # never looked at the conan pkgconf package itself, so on a
        # worker with zero system pkg-config/pkgconf the injection was
        # a no-op ("no binary found on PATH") and meson still failed
        # with `Pkg-config for machine host machine not found`.
        # Resolve the absolute binary from the build context first.
        try:
            build_deps = self.dependencies.build
        except Exception:
            return None
        dep = None
        for ref in ("pkgconf/3.0.5", "pkgconf"):
            try:
                dep = build_deps[ref]
                break
            except Exception:
                continue
        if dep is None:
            return None
        candidates = []
        try:
            for bindir in dep.cpp_info.bindirs:
                candidates.append(str(bindir))
        except Exception:
            pass
        try:
            candidates.append(str(dep.package_folder))
            candidates.append(
                os.path.join(str(dep.package_folder), "bin")
            )
        except Exception:
            pass
        for bindir in candidates:
            for name in ("pkgconf", "pkg-config"):
                exe = os.path.join(bindir, name)
                if os.path.isfile(exe):
                    return exe
        return None

    def _discover_pkg_config(self):
        """Locate a usable pkg-config/pkgconf binary.

        Meson reports `Pkg-config for machine host machine not found`
        when neither the native-file entry nor PATH provides one. Prefer
        the conan-supplied pkgconf (build context), then an existing
        PATH entry, then well-known HNP/system locations.
        Returns None when nothing is found (original error preserved).
        """
        exe = self._pkgconf_exe_from_conan()
        if exe and os.path.isfile(exe):
            return exe
        for probe in ("pkg-config", "pkgconf"):
            found = shutil.which(probe)
            if found and os.path.isfile(found):
                return found
        for candidate in (
            "/data/service/hnp/bin/pkg-config",
            "/data/service/hnp/bin/pkgconf",
            "/usr/bin/pkg-config",
            "/usr/bin/pkgconf",
            "/usr/local/bin/pkg-config",
            "/usr/local/bin/pkgconf",
        ):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _inject_pkg_config(self):
        """Write an absolute `pkgconfig` entry into meson machine files.

        Only fills the entry when meson would otherwise search PATH;
        never overwrites an existing valid entry. Logs the injection so
        the next preflight log shows which binary meson will use.
        """
        exe = self._discover_pkg_config()
        if not exe or not os.path.isfile(exe):
            self.output.info("HMBS pkgconfig: no binary found (conan+PATH)")
            return
        for filename in (
            MesonToolchain.native_filename,
            MesonToolchain.cross_filename,
        ):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if re.search(r"^\s*pkgconfig\s*=", content, flags=re.MULTILINE):
                continue
            if "[binaries]" not in content:
                continue
            insert = "[binaries]\npkgconfig = '{}'\n".format(exe)
            content = content.replace("[binaries]\n", insert, 1)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info(
                "HMBS pkgconfig repair: injected '{}' into {}".format(
                    exe, os.path.basename(path)
                )
            )

    def _meson_exe(self):
        meson_bin = shutil.which("meson")
        if meson_bin:
            return [meson_bin]
        return [sys.executable, "-m", "mesonbuild.mesonmain"]

    def _find_ohos_tool(self, name):
        # Canonical discovery used by libevent/2.1.13, lapack/3.12.1 and
        # the cronutils signing draft: compiler dir first, then the
        # worker convention path, then PATH. For the signer also honor
        # the documented overrides (user.ohos:sign_tool / OHOS_SIGN_TOOL).
        candidates = []
        if name == "binary-sign-tool":
            try:
                conf_val = self.conf.get(
                    "user.ohos:sign_tool", default="", check_type=str
                )
            except Exception:
                conf_val = ""
            if conf_val and conf_val.strip():
                candidates.append(conf_val.strip())
            env_val = (os.environ.get("OHOS_SIGN_TOOL") or "").strip()
            if env_val:
                candidates.append(env_val)
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict,
            ) or {}
        except Exception:
            compilers = {}
        compiler = (
            compilers.get("c", "") or compilers.get("cpp", "")
            if isinstance(compilers, dict) else ""
        )
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sign_one_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        readelf = self._find_ohos_tool("llvm-readelf")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not readelf or not signer:
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required for target "
                "execution (missing: {})".format(
                    ",".join(
                        label for label, tool in (
                            ("llvm-objcopy", objcopy),
                            ("llvm-readelf", readelf),
                            ("binary-sign-tool", signer),
                        ) if not tool
                    )
                )
            )
        self.output.info(
            "HMBS sign tools: objcopy='{}' readelf='{}' signer='{}'".format(
                objcopy, readelf, signer
            )
        )
        clean_path = path + ".codesign-clean"
        signed_path = path + ".signed"
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                "{} --remove-section .codesign {} {}".format(
                    shlex.quote(objcopy),
                    shlex.quote(path),
                    shlex.quote(clean_path),
                )
            )
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(clean_path),
                    shlex.quote(signed_path),
                )
            )
            sections = subprocess.run(
                [readelf, "-SW", signed_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    "signed ELF has invalid .codesign count: {}".format(path)
                )
            # Preserve the original exec mode without requiring chmod:
            # os.replace() would swap in the signer output inode (often
            # 0644), losing +x on the HMBS_CAP_CHMOD=0 tmpfs where chmod
            # is refused. Writing the signed bytes back into the
            # original inode keeps its mode; the chmod below is
            # best-effort for signers that need an explicit 0755.
            try:
                original_mode = os.stat(path).st_mode & 0o7777
            except OSError:
                original_mode = 0o755
            with open(signed_path, "rb") as handle:
                signed_bytes = handle.read()
            try:
                with open(path, "wb") as handle:
                    handle.write(signed_bytes)
            except OSError as exc:
                # HMBS_CAP_CHMOD=0 tmpfs: meson-private sanity probes can
                # be read-only (0444) so in-place "wb" raises EPERM.
                # The build dir itself is writable, so fall back to an
                # atomic replace via rename; keep chmod best-effort.
                import errno as _errno
                if exc.errno not in (_errno.EPERM, _errno.EACCES,
                                     _errno.EROFS):
                    raise
                self.output.info(
                    "HMBS sign: in-place rewrite refused ({}), "
                    "falling back to replace: {}".format(exc, path)
                )
                os.remove(path)
                os.rename(signed_path, path)
                # signed_path was consumed by the rename; mark it gone
                # so the finally-cleanup does not trip.
                signed_path = signed_path + ".consumed"
            target_mode = original_mode | 0o111
            if not (target_mode & 0o100):
                target_mode = 0o755
            self._chmod_if_supported(path, target_mode)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    @staticmethod
    def _chmod_if_supported(path, mode):
        # HMBS may report HMBS_CAP_CHMOD=0 on this tmpfs, but the
        # signer output can lose the exec bit (0644), which makes
        # `meson test` fail with PermissionError on exec
        # (fuzz/fuzz_options). Always attempt the chmod so a runnable
        # file stays runnable; only tolerate filesystems that refuse
        # the operation. Never fail the build on chmod alone.
        try:
            os.chmod(path, mode)
        except OSError as exc:
            import errno
            if exc.errno in (errno.EPERM, errno.EACCES, errno.EROFS,
                             errno.ENOTSUP, errno.EOPNOTSUPP):
                return
            raise

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_build_tree_tests(self):
        """Test executables must be signed before `meson test` can exec
        them on OHOS (same ordering as the libslirp recipe).

        Cycle 18 fix: the previous hard-coded 7-name walk missed the
        build-tree shared lib and left signed files without the exec
        bit on the HMBS_CAP_CHMOD=0 tmpfs, so `meson test` died with
        `PermissionError: .../fuzz/fuzz_options` (exit 13) before any
        test ran (discovered=0). Sign every test binary reported by
        `meson introspect --tests` plus the build-tree libcacard.so*,
        and always restore the exec bit after signing (tolerating
        chmod-refusing filesystems). No test is skipped.
        """
        signed = set()
        # 1) Exact test executables from meson introspection.
        try:
            proc = subprocess.run(
                self._meson_exe()
                + ["introspect", self.build_folder, "--tests"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                tests = json.loads(proc.stdout)
                for entry in tests if isinstance(tests, list) else []:
                    cmd = entry.get("cmd") if isinstance(entry, dict) else None
                    if not cmd:
                        continue
                    candidate = cmd[0] if isinstance(cmd, list) else cmd
                    if not os.path.isabs(candidate):
                        candidate = os.path.join(self.build_folder, candidate)
                    if (
                        os.path.isfile(candidate)
                        and not os.path.islink(candidate)
                        and self._is_elf(candidate)
                        and candidate not in signed
                    ):
                        self._sign_one_elf(candidate)
                        signed.add(candidate)
        except Exception as exc:
            self.output.info(
                "HMBS sign: introspect --tests unavailable ({}), "
                "falling back to directory walk".format(exc)
            )
        # 2) Fallback/widening walk: known names + build-tree libs +
        #    any ELF executable bit holder (covers fuzz/* and
        #    tests/* regardless of meson naming). Meson-private probes
        #    (meson-private/sanitycheck*, meson-info, meson-logs) are
        #    not test artifacts and may be read-only; never sign them.
        for root, _dirs, files in os.walk(self.build_folder):
            _dirs[:] = [
                d for d in _dirs
                if d not in ("meson-private", "meson-info", "meson-logs")
            ]
            if "meson-private" in root.replace(os.sep, "/"):
                continue
            for name in files:
                if name.startswith("sanity_check_"):
                    continue
                candidate = os.path.join(root, name)
                if candidate in signed:
                    continue
                if os.path.islink(candidate):
                    continue
                if name.endswith((".o", ".a", ".obj")):
                    continue
                if not self._is_elf(candidate):
                    continue
                is_known = name in (
                    "libcacard",
                    "simpletlv",
                    "initialize",
                    "hwtests",
                    "hwtests_no_raw",
                    "fuzz_xfer",
                    "fuzz_simpletlv",
                    "fuzz_options",
                )
                is_lib = (
                    name.startswith("libcacard.so")
                    or name.endswith(".so")
                    or name.endswith(".so.0")
                )
                try:
                    executable = os.access(candidate, os.X_OK)
                except OSError:
                    executable = False
                if not (is_known or is_lib or executable):
                    continue
                self._sign_one_elf(candidate)
                signed.add(candidate)
        self.output.info(
            "HMBS sign: signed {} build-tree ELF(s) before meson test".format(
                len(signed)
            )
        )

    def _sign_installed_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            if (
                os.path.isfile(path)
                and not os.path.islink(path)
                and self._is_elf(path)
            ):
                self._sign_one_elf(path)

    def _run_upstream_tests(self):
        """Run `meson test` and emit the HMBS_UPSTREAM_TEST_RESULT marker
        with counts parsed from the real meson output."""
        command = "meson test -C {} --no-rebuild --print-errorlogs".format(
            self.build_folder
        )
        with self._build_environment().vars(self).apply():
            proc = subprocess.run(
                self._meson_exe()
                + [
                    "test",
                    "-C",
                    self.build_folder,
                    "--no-rebuild",
                    "--print-errorlogs",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
        output = proc.stdout or ""
        # Per-program lines look like:
        #   1/6 libcacard:libcacard        OK              0.05s
        passed = len(
            re.findall(
                r"^\s*\d+/\d+\s+\S+\s+OK(?:\s|$)", output, re.MULTILINE
            )
        )
        failed = len(
            re.findall(
                r"^\s*\d+/\d+\s+\S+\s+(?:FAIL|TIMEOUT|INTERRUPT)(?:\s|$)",
                output,
                re.MULTILINE,
            )
        )
        skipped = len(
            re.findall(
                r"^\s*\d+/\d+\s+\S+\s+SKIP(?:\s|$)", output, re.MULTILINE
            )
        )
        discovered = passed + failed + skipped
        if discovered == 0:
            # Fall back to the meson summary block ("Ok: 6") so a pure
            # format change never reports a silent zero-test pass.
            def _summary_count(name):
                found = re.search(
                    r"^" + name + r":\s+(\d+)", output, re.MULTILINE
                )
                return int(found.group(1)) if found is not None else 0

            passed = _summary_count("Ok")
            failed = _summary_count("Fail")
            skipped = _summary_count("Skipped")
            discovered = passed + failed + skipped
        executed = passed + failed
        status = (
            "passed"
            if discovered > 0 and failed == 0 and executed == discovered
            else "failed"
        )
        marker = {
            "status": status,
            "framework": "meson",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        )
        # Dual-channel persistence for conan cache hits: when a later
        # `conan create --build=missing` reuses this binary, build() is
        # skipped and the marker above never appears (evidence
        # incomplete). Persist the exact marker so package() can ship it
        # inside the package and test_package can re-emit it.
        self._persist_upstream_result(marker)
        if status != "passed":
            self.output.error(
                "meson test exit={} output tail:\n{}".format(
                    proc.returncode, output[-4000:]
                )
            )
            raise RuntimeError(
                "upstream meson tests failed "
                "(discovered={} executed={} passed={} failed={} "
                "skipped={})".format(
                    discovered, executed, passed, failed, skipped
                )
            )

    _HMBS_UPSTREAM_RESULT_FILENAME = "hmbs_upstream_result.json"

    def _persist_upstream_result(self, marker):
        """Write the upstream marker to the build folder.

        Dual-channel with the stdout marker above: stdout is captured
        when build() runs, the JSON file survives `--build=missing`
        cache hits via package(). Only forwards real meson counts;
        never invents a pass (cross-build writes status skipped).
        """
        try:
            path = os.path.join(
                self.build_folder, self._HMBS_UPSTREAM_RESULT_FILENAME
            )
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle)
            self.output.info(
                "HMBS upstream result persisted: {}".format(path)
            )
        except Exception as exc:
            self.output.warning(
                "HMBS upstream result persist failed: {}".format(exc)
            )

    def _persist_upstream_result_into_package(self):
        """Ship the persisted marker inside the package.

        Stored under share/libcacard/ so test_package can re-emit it
        on cache-hit runs where build() is skipped entirely.
        """
        try:
            src = os.path.join(
                self.build_folder, self._HMBS_UPSTREAM_RESULT_FILENAME
            )
            if not os.path.isfile(src):
                self.output.warning(
                    "HMBS upstream result file missing in build folder; "
                    "cache-hit runs will have no upstream evidence to "
                    "re-emit."
                )
                return
            dst_dir = os.path.join(
                self.package_folder, "share", "libcacard"
            )
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(
                dst_dir, self._HMBS_UPSTREAM_RESULT_FILENAME
            )
            shutil.copyfile(src, dst)
            self.output.info(
                "HMBS upstream result packaged: {}".format(dst)
            )
        except Exception as exc:
            self.output.warning(
                "HMBS upstream result packaging failed: {}".format(exc)
            )
