#!/usr/bin/env python3
"""Conan recipe for the pure-Python/Perl dh-ros build helper.

Runtime Python dependency: catkin_pkg (imported by dhros.common). It is not
published as a Conan recipe, so it is pinned in build() and installed from the
community pip index into the package's own site-packages tree, together with
its transitive dependencies. The packaged CLI is therefore self-contained and
needs no global pip install on the target. Same approach as the
black / advai-cli recipes.

R26: N/A — pure Python/Perl package, no .so is produced and there is no
system-name library to link statically. R38: applies (CLI tool rosbuilder).
"""

import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Community pip index carrying the OHOS-adapted wheels (catkin_pkg lives here).
PIP_COMMUNITY_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
PIP_COMMUNITY_HOST = "pypi.cnb.cool"
CATKIN_PKG_VERSION = "1.1.0"
# Pinned PEP 517 backend. The CI build Python 3.12 does not ship setuptools, so
# installing the project with --no-build-isolation fails with BackendUnavailable
# ("Cannot import 'setuptools.build_meta'") unless the backend is staged locally
# and exposed on PYTHONPATH, the same way the runtime dependencies are staged.
SETUPTOOLS_VERSION = "75.8.0"


class DhRosConan(ConanFile):
    name = "dh-ros"
    version = "0.15.0"
    description = "Debian helper for building ROS and ROS 2 packages"
    license = "MIT"
    homepage = "https://salsa.debian.org/robotics-team/dh-ros"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # catkin_pkg is a runtime Python dependency of dhros.common. It has no
        # Conan recipe in the artifact repository, so it is bundled from pip in
        # build() instead of being declared here.
        self.requires("perl/5.42.2.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        target = os.path.join(self.build_folder, "site-packages")
        os.makedirs(target, exist_ok=True)
        # Stage the PEP 517 backend first: the build interpreter may not provide
        # setuptools, and --no-build-isolation deliberately disables pip's own
        # backend provisioning. A private prefix keeps this out of shared paths.
        backend = os.path.join(self.build_folder, "build-backend")
        os.makedirs(backend, exist_ok=True)
        self.run(
            f'"{sys.executable}" -m pip install --no-compile --target "{backend}" '
            f'--index-url {PIP_COMMUNITY_INDEX} '
            f'--trusted-host {PIP_COMMUNITY_HOST} '
            f'--retries 5 --timeout 60 "setuptools=={SETUPTOOLS_VERSION}"'
        )
        # ConanFile.run(env=...) takes env *file* names, not a mapping, so the
        # staged backend is exposed by prefixing the command with PYTHONPATH.
        self.run(
            f"PYTHONPATH={shlex.quote(backend)}"
            f"${{PYTHONPATH:+:$PYTHONPATH}} "
            f'"{sys.executable}" -m pip install --no-deps --no-build-isolation '
            f'--target "{target}" "{self.source_folder}"'
        )
        # Bundle catkin_pkg and its transitive dependencies (docutils, packaging,
        # python-dateutil, pyparsing, six, setuptools) into the same tree so the
        # installed CLI can import dhros on a target without a global pip install.
        self.run(
            f'"{sys.executable}" -m pip install --no-compile --target "{target}" '
            f'--index-url {PIP_COMMUNITY_INDEX} '
            f'--trusted-host {PIP_COMMUNITY_HOST} '
            f'--retries 5 --timeout 60 "catkin_pkg=={CATKIN_PKG_VERSION}"'
        )

    def package(self):
        staged = os.path.join(self.build_folder, "site-packages")
        site_packages = os.path.join(self.package_folder, "lib", "site-packages")
        # bin/ holds pip-generated console scripts whose shebangs point at the
        # build machine; the portable rosbuilder wrapper below replaces them.
        copy(
            self,
            "*",
            src=staged,
            dst=site_packages,
            excludes=["bin", "bin/*", "__pycache__", "**/__pycache__"],
        )

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        rosbuilder = os.path.join(bin_dir, "rosbuilder")
        package_root = os.path.join("..", "lib", "site-packages")
        with open(rosbuilder, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                "import os\n"
                "import sys\n"
                f"_site = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), {package_root!r}))\n"
                "if _site not in sys.path:\n"
                "    sys.path.insert(0, _site)\n"
                "from dhros.rosbuilder import main\n"
                "raise SystemExit(main())\n"
            )
        os.chmod(rosbuilder, 0o755)

        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "ros.pm", src=os.path.join(self.source_folder, "dh"), dst=os.path.join(self.package_folder, "share", "perl5", "Debian", "Debhelper", "Buildsystem"))

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        template = os.path.join(self.source_folder, "rosbuilder.1.in")
        if os.path.isfile(template):
            with open(template, encoding="utf-8") as source:
                manpage = source.read().replace("@VERSION@", self.version)
            with open(os.path.join(man_dir, "rosbuilder.1"), "w", encoding="utf-8") as target:
                target.write(manpage)

    def package_info(self):
        site_packages = os.path.join(self.package_folder, "lib", "site-packages")
        perl_modules = os.path.join(self.package_folder, "share", "perl5")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.buildenv_info.prepend_path("PERL5LIB", perl_modules)
        self.runenv_info.prepend_path("PERL5LIB", perl_modules)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dh-ros supports Linux and OHOS only, got {self.settings.os}"
            )
