#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Embedlog, embedlog, 0.7.2, embedlog 0.7.2, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import chmod
import os


class EmbedlogConan(ConanFile):
    name = "embedlog"
    version = "0.7.2"
    description = "embedlog - Simple and fast C logging library (0.7.2)"
    license = "BSD-2-Clause"
    homepage = "https://embedlog.bofc.pl"
    url = "https://github.com/mlyszczek/embedlog"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The tarball ships no `configure` (only configure.ac + autogen.sh),
        # so build() must run `autoreconf -fi` to bootstrap (same approach
        # as abiword-plugin-*/clarisworks recipe).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") so its probe aborts configure. Pass the
        # triplet explicitly (config.sub supports *-linux-ohos) so configure
        # never runs the config.guess probe; same approach as argp-standalone.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: Autotools helper scripts lose exec bit when conan copies sources
        for script in ("configure", "config.guess", "config.sub", "install-sh", "missing", "compile", "depcomp", "test-driver"):
            p = os.path.join(self.source_folder, script)
            if os.path.exists(p):
                chmod(self, p, 0o755, update_acls=True)
        # The tarball ships no `configure`: generate one from configure.ac
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011/E046-family HMDFS fix (see knowledge draft cln-1.3.7-mktemp-0700-hmdfs):
        # config.status creates its CONFIG_FILES temp dir via `mktemp -d "./confXXXXXX"`,
        # which ALWAYS yields mode 0700 regardless of umask. On HMDFS setgid parent dirs
        # (owner uid 20001006) with uid-mapped processes (CI worker), writing/reading
        # inside a 0700 dir owned by a different effective uid fails EACCES and
        # config.status aborts with "could not setup config files machinery"
        # (`./confiCKLmd/subs1.awk: Permission denied`, PR #12564 CI #60560).
        # Patch the generated configure (its config.status heredoc) to skip mktemp and
        # use the shell-unique `conf$$-$RANDOM` name with umask 000 + mkdir -> 0777,
        # exactly the verified cln fix.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg):
            with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            old = """{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5"""
            new = """{
  tmp=./conf$$-$RANDOM
  (umask 000 && mkdir "$tmp") &&
  test -d "$tmp"
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5"""
            if old in text:
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(text.replace(old, new))
                self.output.info("patched configure: mktemp temp-dir -> mkdir 0777 (HMDFS exec/uid fix)")
            else:
                self.output.warning("configure temp-dir block not found, skip patch")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["embedlog"]
