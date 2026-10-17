#!/usr/bin/env python3
"""Conan recipe for libqd 2.3.24 (QD double-double / quad-double)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibqdConan(ConanFile):
    name = "libqd"
    version = "2.3.24"
    description = "Double-double and quad-double floating-point arithmetic for C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/BL-highprecision/QD"
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

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libqd is validated only for Linux and OHOS")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "src"

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import shutil
            import tarfile
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def _host_perl(self):
        for candidate in (
            "/data/app/bin/perl",
            "/data/service/hnp/bin/perl",
            "/usr/bin/perl",
            shutil.which("perl"),
        ):
            if not candidate or not os.path.isfile(candidate):
                continue
            real = os.path.realpath(candidate).replace("\\", "/")
            if "/conan2/p/perl" in real:
                continue
            return candidate
        return None

    def _tool_share(self, tool, share_name):
        path = shutil.which(tool)
        if not path:
            return ""
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(path)))
        return os.path.join(prefix, "share", share_name)

    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        perl = self._host_perl()
        if perl:
            env.define("PERL", perl)
            env.prepend_path("PATH", os.path.dirname(perl))
        am = self._tool_share("aclocal", "automake-1.18")
        ac = self._tool_share("autoconf", "autoconf")
        libs = os.pathsep.join([p for p in (am, ac) if p])
        if libs:
            env.define("PERL5LIB", libs)
        env.vars(self).save_script("libqd_perl")
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-fortran")
        tc.configure_args.append("--enable-inline")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def _patch_hmdfs_configure(self):
        import glob
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            with open(cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            orig = text
            for umask in ("077", "000", "022"):
                text = text.replace(
                    'tmp=`(umask %s && mktemp -d "./confXXXXXX") 2>/dev/null`' % umask,
                    'tmp=./conf$$-$RANDOM; (umask 000 && mkdir "$tmp")',
                )
            text = text.replace("umask 077", "umask 000")
            if text != orig:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text)

    def _disable_docs(self):
        for name in ("Makefile.am", "Makefile.in"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            text = text.replace("BUILT_SOURCES = docs/qd.pdf", "BUILT_SOURCES =")
            text = text.replace("dist_doc_DATA = README README.md docs/qd.pdf", "dist_doc_DATA = README README.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._disable_docs()
        perl = self._host_perl() or "perl"
        self.run(
            "sh -c '"
            "set -e; "
            "export PERL=%s; "
            "libtoolize --copy --force || true; "
            "ACL=$(command -v aclocal); "
            "ACF=$(command -v autoconf); "
            "test -n \"$ACL\" || { echo aclocal-not-found; exit 1; }; "
            "AMP=$(dirname \"$(dirname \"$ACL\")\"); "
            "ACP=$(dirname \"$(dirname \"$ACF\")\"); "
            "AMSHARE=; "
            "for d in \"$AMP\"/share/automake-*; do "
            "  if [ -f \"$d/Automake/Config.pm\" ]; then AMSHARE=$d; break; fi; "
            "done; "
            "test -n \"$AMSHARE\" || { echo missing-Automake-Config.pm under \"$AMP/share\"; ls -la \"$AMP/share\" || true; exit 1; }; "
            "export PERL5LIB=\"$AMSHARE\"; "
            "echo PERL5LIB=$PERL5LIB; "
            "aclocal; "
            "if [ -d \"$ACP/share/autoconf\" ]; then export PERL5LIB=\"$ACP/share/autoconf\"; fi; "
            "autoconf; "
            "autoheader || true; "
            "export PERL5LIB=\"$AMSHARE\"; "
            "automake --add-missing --copy --force-missing"
            "'" % perl,
            cwd=self.source_folder,
        )
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            os.chmod(cfg, 0o755)
        self._patch_hmdfs_configure()
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        import glob
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["qd"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libqd")
        self.cpp_info.set_property("cmake_target_name", "libqd::libqd")
        self.cpp_info.set_property("pkg_config_name", "qd")
