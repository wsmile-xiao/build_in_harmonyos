#!/usr/bin/env python3
"""Conan recipe — rsnapshot 1.5.1 (Autotools, pure-Perl snapshot tool).

rsnapshot is a filesystem snapshot utility that uses rsync + hard links to
create incremental snapshots. It ships as Perl scripts (rsnapshot-program.pl,
rsnapshot-diff.pl) which autotools configure substitutes into executable
scripts; there is no C compilation.

Dependencies (all Conan packages on the ohpcd remote):
  - perl/5.42.2   — runtime interpreter (buildenv exports PATH + PERL)
  - rsync/3.3.0   — snapshot transfer backend
  - openssh/10.0p1 — remote backup transport

Platform notes:
  - E049: installed scripts get a portable `#!/usr/bin/env perl` shebang
    (configure would otherwise bake the build-time perl absolute path).
  - E114-class: config.status mktemp in CWD fails on HMDFS; fixed by
    redirecting its temp dir to TMPDIR before running config.status
    (programmatic fix in build(), mirrors archives/r/rsync approach).
  - R49: no shared/system prefix injection; all tools resolved from the
    Conan dependency graph.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsnapshotConan(ConanFile):
    name = "rsnapshot"
    version = "1.5.1"
    description = "Filesystem snapshot utility based on rsync and hard links"
    license = "GPL-2.0-or-later"
    homepage = "https://rsnapshot.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("rsync/3.3.0")
        self.requires("openssh/10.0p1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_tool(self, dep, tool):
        """Absolute path of a tool binary provided by a Conan dependency."""
        pkg = self.dependencies[dep]
        return os.path.join(pkg.package_folder, pkg.cpp_info.bindirs[0], tool)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E114: generate config.status without executing it, so the HMDFS
        # mktemp fix can be applied before it runs.
        tc.configure_args.append("--no-create")
        # Explicit tool paths from the Conan dependency graph (R33: no
        # reliance on shell PATH).
        tc.configure_args.append(f"--with-perl={self._dep_tool('perl', 'perl')}")
        tc.configure_args.append(f"--with-rsync={self._dep_tool('rsync', 'rsync')}")
        tc.configure_args.append(f"--with-ssh={self._dep_tool('openssh', 'ssh')}")
        tc.generate()
        # Aggregate build env (perl buildenv PATH etc.) into conanbuild.sh so
        # make can invoke pod2man/perl during the man-page step.
        from conan.tools.env import VirtualBuildEnv

        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: run configure with toolchain env; configure --no-create only
        # generates config.status.
        autotools = Autotools(self)
        autotools.configure()

        # E114-class: patch config.status's HMDFS-hostile `mktemp -d
        # ./confXXXXXX` (created by the configure above) before running it.
        cs_file = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(cs_file):
            cs_file = os.path.join(self.source_folder, "config.status")
        if os.path.exists(cs_file):
            tmpdir = os.environ.get("TMPDIR", os.path.join(self.build_folder, "tmp"))
            fixed_dir = os.path.join(tmpdir, "rsnapshot-config-status-tmp")
            os.makedirs(fixed_dir, exist_ok=True)
            with open(cs_file, "r") as f:
                content = f.read()
            content = content.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                "tmp=%s" % fixed_dir,
            )
            content = content.replace('(umask 077 && mkdir "$tmp")', "true")
            with open(cs_file, "w") as f:
                f.write(content)

        self.run("bash config.status", env=["conanbuild"])

        # The Makefile invokes bare `pod2man`/`pod2html`; with the OHOS
        # profile PATH, the system (HNP) pod2man may win over the Conan
        # perl's one and aborts on PERL5LIB version mismatch (5.42.0 vs
        # 5.42.2). Pin them to the Conan perl's own tools (deterministic,
        # no PATH-order dependency).
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(makefile):
            perl = self._dep_tool("perl", "perl")
            pod2man = self._dep_tool("perl", "pod2man")
            pod2html = self._dep_tool("perl", "pod2html")
            with open(makefile, "r") as f:
                mk_content = f.read()
            # Run the pod tools through the Conan perl binary: the pod2man
            # scripts in the perl package carry a broken `#!//bin/perl`
            # shebang, and system pod2man aborts on PERL5LIB mismatch.
            mk_content = mk_content.replace(
                "\tpod2man ", '\t"%s" "%s" ' % (perl, pod2man)
            )
            mk_content = mk_content.replace(
                "\tpod2html ", '\t"%s" "%s" ' % (perl, pod2html)
            )
            with open(makefile, "w") as f:
                f.write(mk_content)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E049: replace build-machine interpreter paths with a portable
        # shebang so the installed scripts run wherever perl is on PATH.
        for script in ("rsnapshot", "rsnapshot-diff"):
            fpath = os.path.join(self.package_folder, "bin", script)
            if os.path.exists(fpath):
                with open(fpath, "r") as f:
                    lines = f.readlines()
                if lines and lines[0].startswith("#!"):
                    lines[0] = "#!/usr/bin/env perl\n"
                with open(fpath, "w") as f:
                    f.writelines(lines)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
