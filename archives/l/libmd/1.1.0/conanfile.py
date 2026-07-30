#!/usr/bin/env python3
"""Conan recipe for libmd 1.1.0.
OHOS 上 HMDFS 禁止执行用户文件 (E046)，config.status 创建临时 awk 脚本会失败。
解决：configure 后在 config.status 中用 $AWK -f 替换直接执行。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmdConan(ConanFile):
    name = "libmd"
    version = "1.1.0"
    description = "Message Digest functions from BSD systems"
    license = "BSD-3-Clause"
    homepage = "https://libbsd.freedesktop.org"
    url = "https://libbsd.freedesktop.org/releases/libmd-1.1.0.tar.xz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # armv8_32 (AArch32) must NOT map to aarch64 — that would feed
        # config.sub a 64-bit triple for a 32-bit build. id3v2/0.1.12 keeps
        # the same {armv8, x86_64, x86} mapping without an armv8_32 entry,
        # so an unknown arch falls back to str(self.settings.arch) and
        # configure fails loudly instead of silently using the wrong triple.
        arch_map = {"armv8": "aarch64", "x86_64": "x86_64", "x86": "i386"}
        build_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        tc.configure_args.append(f"--build={build_arch}-unknown-linux-ohos")
        tc.generate()
        self._configure_args = tc.configure_args

    def build(self):
        apply_conandata_patches(self)
        # P2: autotools = Autotools(self) was dead code — all build steps
        # use manual self.run() and AutotoolsToolchain.generate() already
        # injected the conanbuild env. Removed.
        # HMDFS noexec: use /system/bin/sh to run configure, with --no-create
        configure_cmd = "/system/bin/sh ./configure --no-create " + " ".join(self._configure_args)
        self.run(configure_cmd, cwd=self.source_folder)
        # HMDFS noexec: patch config.status to use writable temp dir.
        # P1+P2: use TemporaryDirectory (auto-cleanup, no disk leak) and
        # omit dir= (defaults to $TMPDIR or /tmp) — never hardcode
        # /storage/Users/currentUser which only exists on dev machine.
        import tempfile, re, os
        with tempfile.TemporaryDirectory(prefix='.libmd-conf-') as conf_tmp:
            os.chmod(conf_tmp, 0o755)
            cs_path = os.path.join(self.source_folder, "config.status")
            if os.path.isfile(cs_path):
                with open(cs_path, 'r') as f:
                    cs_content = f.read()
                cs_content = re.sub(r'tmp=`\(umask 077 && mktemp -d[^`]+`', f'tmp="{conf_tmp}"', cs_content)
                cs_content = re.sub(r'tmp=\./conf\$\$-\$RANDOM', f'tmp={conf_tmp}', cs_content)
                with open(cs_path, 'w') as f:
                    f.write(cs_content)
            self.run("/system/bin/sh ./config.status", cwd=self.source_folder)
            self.run("make -j1", cwd=self.source_folder)
            # Upstream ships real test programs (test/{md2,md4,md5,rmd160,
            # sha1,sha2}.c with hardcoded hash assertions). `make check`
            # builds + executes them per the upstream Autotools standard
            # (TESTS = check_PROGRAMS). This validates the build beyond a
            # smoke test. On HMDFS noexec dev hosts the test binaries can't
            # exec (Operation not permitted); catch ONLY noexec-class
            # errors (PermissionError / OSError errno.EPERM / ConanException
            # whose message mentions "Operation not permitted" or
            # "Permission denied") so a real compile/link failure surfaces
            # instead of being silently swallowed. The package still builds
            # on noexec hosts, leaving the upstream tests to run on CI workers
            # where exec is allowed (petsc/sqlite3 merged PRs confirm).
            try:
                self.run("make check -j1", cwd=self.source_folder)
            except (PermissionError, OSError) as exc:
                # errno.EPERM = 1, errno.EACCES = 13 — both map to noexec.
                import errno
                if isinstance(exc, OSError) and exc.errno not in (errno.EPERM, errno.EACCES):
                    raise
                self.output.warn(
                    f"make check skipped (HMDFS noexec on dev host; "
                    f"CI worker can exec): {exc}"
                )
            except ConanException as exc:
                # ConanException wraps the subprocess error; re-raise unless
                # the message clearly indicates an exec-permission issue.
                msg = str(exc)
                if "Operation not permitted" not in msg and "Permission denied" not in msg:
                    raise
                self.output.warn(
                    f"make check skipped (HMDFS noexec on dev host; "
                    f"CI worker can exec): {exc}"
                )

    def package(self):
        self.run("make install DESTDIR={} -j1".format(self.package_folder), cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["md"]
        self.cpp_info.set_property("pkg_config_name", "libmd")