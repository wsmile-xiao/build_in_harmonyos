#!/usr/bin/env python3
"""Conan recipe for mysqltuner 2.9.1.

mysqltuner is a single-file Perl CLI plus runtime data files.  There is no
native compilation; build() runs the upstream no-service Perl test subset when
the host package can execute on the current machine.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class MysqltunerConan(ConanFile):
    name = "mysqltuner"
    version = "2.9.1"
    description = "MySQLTuner high performance MySQL and MariaDB tuning script"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/major/MySQLTuner-perl"
    url = "https://github.com/major/MySQLTuner-perl"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _source_urls = [
        "https://ghfast.top/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
        "https://gh-proxy.com/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
        "https://mirror.ghproxy.com/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
        "https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
    ]
    _source_sha256 = "384e4128991fb8573a61841cb838a74d59063607a817b1da6c86739e439eb4c2"
    _no_service_tests = (
        "tests/cli_options.t",
        "tests/cli_forcemem_human.t",
        "tests/version_consistency.t",
        "tests/unit_version_helpers.t",
        "tests/unit_cli_helpers.t",
        "tests/unit_utilities.t",
    )

    def requirements(self):
        self.requires("perl/5.42.2", headers=False, libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mysqltuner supports Linux/OHOS style hosts, got {self.settings.os}"
            )

    def source(self):
        get(
            self,
            url=self._source_urls,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        for relpath in (
            "mysqltuner.pl",
            "basic_passwords.txt",
            "vulnerabilities.csv",
            "LICENSE",
        ):
            path = os.path.join(self.source_folder, relpath)
            if not os.path.isfile(path):
                raise RuntimeError(f"upstream mysqltuner artifact is missing: {relpath}")

        if not can_run(self):
            self.output.warning(
                "Cannot run host Perl on this build machine; upstream tests "
                "are deferred to native OHOS validation"
            )
            return

        self.run('perl -c "mysqltuner.pl"', cwd=self.source_folder, env="conanrun")
        tests = " ".join(f'"{test}"' for test in self._no_service_tests)
        self.run(f"perl -S prove {tests}", cwd=self.source_folder, env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", "mysqltuner")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "mysqltuner")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(share_dir, exist_ok=True)

        with open(os.path.join(self.source_folder, "mysqltuner.pl"), "r", encoding="utf-8") as src:
            content = src.read()
        shebang = "#!/data/service/hnp/bin/perl" if str(self.settings.os) == "OHOS" else "#!/usr/bin/env perl"
        lines = content.splitlines()
        if lines and lines[0].startswith("#!"):
            lines[0] = shebang
        content = "\n".join(lines) + "\n"

        for name in ("mysqltuner", "mysqltuner.pl"):
            dst = os.path.join(bin_dir, name)
            save(self, dst, content)
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        for data_file in ("basic_passwords.txt", "vulnerabilities.csv"):
            copy(self, data_file, src=self.source_folder, dst=share_dir, keep_path=False)

        copy(self, "README.md", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "USAGE.md", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        perl_bin = os.path.join(self.dependencies["perl"].package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path("PATH", perl_bin)
        self.runenv_info.prepend_path("PATH", bin_dir)
