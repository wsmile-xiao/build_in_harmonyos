#!/usr/bin/env python3
"""Conan recipe - alive 2.0.3 (Autotools, Guile script tool)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AliveConan(ConanFile):
    name = "alive"
    version = "2.0.3"
    description = "GNU Alive periodic ping keep-alive program"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/alive/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Unsupported OS: %s" % self.settings.os)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # guile provides the `guile` interpreter baked into bin/alive's
        # shebang (#!/usr/bin/env guile). run=True so downstream runenv
        # (test_package + consumers) resolves guile via PATH; otherwise
        # `alive --version` fails with "guile: not found" on clean CI.
        self.requires("guile/2.2.7.1", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Guix proven: preset the ping capability probe so configure does not
        # execute "$PING -n -c 1 localhost" at build time (flaky without net).
        # The installed script still requires ping(1) with "-n -c COUNT".
        tc.configure_args.append("alive_cv_nice_ping=yes")
        tc.generate()

        # OHOS has no texinfo/makeinfo: doc/ would fail with Error 127.
        # Provide a fake makeinfo that touches the output (same as akku).
        fake_bin = os.path.join(self.build_folder, "fake-bin")
        os.makedirs(fake_bin, exist_ok=True)
        fake_makeinfo = os.path.join(fake_bin, "makeinfo")
        with open(fake_makeinfo, "w", newline="\n") as fh:
            fh.write("#!/bin/sh\n")
            fh.write('out=""\n')
            fh.write('prev=""\n')
            fh.write('for arg in "$@"; do\n')
            fh.write('  if [ "$prev" = "-o" ]; then out="$arg"; fi\n')
            fh.write('  prev="$arg"\n')
            fh.write('done\n')
            fh.write('[ -n "$out" ] && touch "$out"\n')
            fh.write("exit 0\n")
        # HMBS_CAP_CHMOD may be 0 (chmod unsupported on HMDFS): best effort.
        try:
            os.chmod(fake_makeinfo, 0o755)
        except OSError:
            pass

        env = tc.environment()
        env.define("MAKEINFO", fake_makeinfo)
        env.append_path("PATH", fake_bin)
        guile_dep = self.dependencies.get("guile")
        if guile_dep:
            bin_dir = os.path.join(guile_dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.append_path("PATH", bin_dir)
                guile_bin = os.path.join(bin_dir, "guile")
                if os.path.isfile(guile_bin):
                    env.define("GUILE", guile_bin)
                cfg_bin = os.path.join(bin_dir, "guile-config")
                if os.path.isfile(cfg_bin):
                    env.define("GUILE_CONFIG", cfg_bin)
                tools_bin = os.path.join(bin_dir, "guile-tools")
                if os.path.isfile(tools_bin):
                    env.define("GUILE_TOOLS", tools_bin)
            for libdir in guile_dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
            scm_dir = os.path.join(guile_dep.package_folder, "share", "guile", "2.2")
            if os.path.isdir(scm_dir):
                env.append_path("GUILE_LOAD_PATH", scm_dir)
            ccache_dir = os.path.join(guile_dep.package_folder, "lib", "guile", "2.2", "ccache")
            if os.path.isdir(ccache_dir):
                env.append_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
        env.define("GUILE_AUTO_COMPILE", "0")
        env.define_path("SHELL", "/bin/sh")
        env.define_path("CONFIG_SHELL", "/bin/sh")
        tc.generate(env=env)

        fix = Environment()
        fix.define_path("SHELL", "/bin/sh")
        fix.define_path("CONFIG_SHELL", "/bin/sh")
        fix.vars(self, scope="build").save_script("conanfixenv")

    def build(self):
        apply_conandata_patches(self)
        for fn in ("configure", "config.status"):
            p = os.path.join(self.source_folder, fn)
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    c = f.read()
                if "umask 077" in c:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(c.replace("umask 077", "umask 022"))
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(conanbuild_sh):
            with open(conanbuild_sh, "r", encoding="utf-8") as f:
                content = f.read()
            marker = 'export CONFIG_SHELL="/bin/sh"'
            if marker not in content:
                fix = '\n# Override HMBS buildenv SHELL/CONFIG_SHELL\n'
                fix += 'export SHELL="/bin/sh"\n'
                fix += 'export CONFIG_SHELL="/bin/sh"\n'
                with open(conanbuild_sh, "w", encoding="utf-8") as f:
                    f.write(content + fix)
        autotools = Autotools(self)
        autotools.configure()
        # -j1 caps peak link memory on the device (Signal 9/OOM hardening,
        # same as akku); SHELL pins the HMBS-injected POSIX shell.
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])
        # Guarantee bin/alive is a real, runnable script even on HMDFS
        # (hardlink=0/chmod=0/symlink quirks): `make install` may leave a
        # dangling/absolute symlink or skip the script. Fall back to the
        # built src/alive and materialize a regular file.
        alive_bin = os.path.join(self.package_folder, "bin", "alive")
        if os.path.islink(alive_bin):
            try:
                target = os.readlink(alive_bin)
                self.output.info("bin/alive is symlink -> %s" % target)
            except OSError:
                target = "<unreadable>"
                self.output.warning("bin/alive symlink unreadable")
            # Materialize: read through the link if valid, else replace.
            real_content = None
            if os.path.isfile(alive_bin):
                try:
                    with open(alive_bin, "r", encoding="utf-8",
                              errors="ignore") as f:
                        real_content = f.read()
                except OSError:
                    real_content = None
            if real_content is None:
                try:
                    os.unlink(alive_bin)
                except OSError:
                    pass
            else:
                # Valid link now, but absolute build-path target breaks on
                # other machines: materialize as a regular file.
                try:
                    os.unlink(alive_bin)
                    with open(alive_bin, "w", encoding="utf-8",
                              newline="\n") as f:
                        f.write(real_content)
                except OSError as e:
                    self.output.warning("materialize symlink failed: %s" % e)
        if not os.path.isfile(alive_bin):
            cands = [
                os.path.join(self.build_folder, "src", "alive"),
                os.path.join(self.source_folder, "src", "alive"),
                os.path.join(self.build_folder, "alive"),
                os.path.join(self.source_folder, "alive"),
            ]
            for c in cands:
                if os.path.isfile(c) and not os.path.islink(c):
                    self.output.info("fallback install bin/alive from %s" % c)
                    try:
                        os.makedirs(os.path.join(self.package_folder, "bin"),
                                    exist_ok=True)
                    except OSError:
                        pass
                    try:
                        with open(c, "r", encoding="utf-8",
                                  errors="ignore") as f:
                            body = f.read()
                        with open(alive_bin, "w", encoding="utf-8",
                                  newline="\n") as f:
                            f.write(body)
                    except OSError as e:
                        self.output.warning("fallback copy failed: %s" % e)
                    break
        # Relocatable shebang: configure bakes the build-time guile absolute
        # path into bin/alive. Downstream machines have a different cache
        # path, so rewrite to /usr/bin/env guile which the conanrun PATH
        # (guile bin dir) resolves. Keeps runtime behavior unchanged.
        # NOTE: open(..., "w") on an existing inode preserves its mode on
        # POSIX/HMDFS, so this does not strip the exec bit; chmod below is
        # best-effort for HMBS_CAP_CHMOD=0.
        if os.path.isfile(alive_bin) and not os.path.islink(alive_bin):
            with open(alive_bin, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
            if lines and lines[0].startswith("#!"):
                lines[0] = "#!/usr/bin/env guile -s"
                with open(alive_bin, "w", encoding="utf-8", newline="\n") as f:
                    f.write("\n".join(lines) + "\n")
            try:
                os.chmod(alive_bin, 0o755)
            except OSError:
                pass
        else:
            self.output.warning(
                "bin/alive still missing after fallback; listing package")
        try:
            for root, _ds, fs in os.walk(
                    os.path.join(self.package_folder, "bin")):
                for fn in fs:
                    fp = os.path.join(root, fn)
                    self.output.info("pkg bin entry: %s link=%s size=%s" % (
                        fp, os.path.islink(fp),
                        os.path.getsize(fp) if os.path.exists(fp) else -1))
                break
        except OSError:
            pass
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.runenv_info.append_path("PATH", bin_dir)
            self.buildenv_info.append_path("PATH", bin_dir)
        self.runenv_info.define("GUILE_AUTO_COMPILE", "0")
        self.buildenv_info.define("GUILE_AUTO_COMPILE", "0")
        alive_bin = os.path.join(bin_dir, "alive")
        if os.path.isfile(alive_bin):
            self.runenv_info.define("ALIVE", alive_bin)
            self.buildenv_info.define("ALIVE", alive_bin)
