#!/usr/bin/env python3
"""Consumer test for ldap-git-backup/1.0.8.

Runs the packaged Perl scripts for real: --help banner, runtime Git.pm
availability, and the full upstream prove suite (11 cases) shipped in
share/ldap-git-backup/t — executed against mock-slapcat, no live LDAP
server needed.
"""
import os
import shutil

from conan import ConanFile


class LdapGitBackupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        dep = self.dependencies["ldap-git-backup"]
        script = os.path.join(self.source_folder, "test_ldap_git_backup.sh")
        self.run(f'{bash} {script} "{dep.package_folder}" "{self.build_folder}"',
                 env="conanrun")
