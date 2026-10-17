#!/usr/bin/env python3
"""Conan recipe for tofuenv 1.0.7.1 — pure bash shell script tool.

tofuenv is an OpenTofu version manager (inspired by tfenv).
It is written entirely in bash — no compilation required.

OHOS adaptation:
  - All script shebangs rewritten from #!/usr/bin/env bash to
    #!/data/service/hnp/bin/bash (OHOS bash path)
  - curlw() injected with --connect-timeout/--max-time (OHOS: github.com blocked)
  - jq dependency removed: list-remote uses grep+sed instead
  - /tmp paths replaced with ${TMPDIR:-$HOME/tmp} (OHOS: /tmp read-only, E002)
  - list-remote uses TOFUENV_API_REMOTE (separate from TOFUENV_REMOTE)
  - package_info sets TOFUENV_REMOTE mirror for OHOS GitHub access
  - package() copies bin/, lib/, libexec/, scripts/, share/, CHANGELOG.md
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file


class TofuenvConan(ConanFile):
    name = "tofuenv"
    version = "1.0.7.1"
    description = "OpenTofu version manager inspired by tfenv"
    license = "MIT"
    homepage = "https://github.com/tofuutils/tofuenv"
    url = "https://cnb.cool/OpenHarmonyPCDeveloper/build_in_harmonyos/-/tree/main/archives/t/tofuenv"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No layout() method — basic_layout() causes source path issues (R26 lesson)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Rewrite shebangs for OHOS: #!/usr/bin/env bash -> #!/data/service/hnp/bin/bash
        if self.settings.os == "OHOS":
            ohos_bash = "/data/service/hnp/bin/bash"
            script_dirs = ["bin", "libexec", "lib", "scripts"]
            for script_dir in script_dirs:
                dir_path = os.path.join(self.source_folder, script_dir)
                if not os.path.isdir(dir_path):
                    continue
                for root, _, files in os.walk(dir_path):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if not os.path.isfile(filepath):
                            continue
                        # Read first line to detect shebang; skip unreadable/binary files
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                first_line = f.readline()
                        except (UnicodeDecodeError, OSError):
                            continue
                        # Replace shebang outside try: failures must surface, not be swallowed
                        if first_line.startswith("#!/usr/bin/env bash"):
                            replace_in_file(
                                self,
                                filepath,
                                "#!/usr/bin/env bash",
                                f"#!{ohos_bash}",
                            )

            # --- OHOS platform adaptations ---

            # 1. curlw: inject timeout (github.com:443 blocked on OHOS, avoid long hangs)
            helpers_path = os.path.join(self.source_folder, "lib", "tofuenv-helpers.sh")
            replace_in_file(
                self,
                helpers_path,
                "curl ${TLS_OPT} -H \"${AUTHORIZATION_HEADER}\" ${NETRC_OPT} \"$@\";",
                "curl --connect-timeout 10 --max-time 120 ${TLS_OPT} -H \"${AUTHORIZATION_HEADER}\" ${NETRC_OPT} \"$@\";",
            )

            # 2. Remove jq dependency: list-remote uses grep+sed to parse GitHub API JSON
            list_remote_path = os.path.join(self.source_folder, "libexec", "tofuenv-list-remote")
            replace_in_file(
                self,
                list_remote_path,
                'jq -r ".[].name"',
                "grep -oE '\"name\":\\s*\"[^\"]*\"' | sed -E 's/.*\"name\":\\s*\"//;s/\"$//'",
            )

            # 3. list-remote: use TOFUENV_API_REMOTE to avoid conflict with TOFUENV_REMOTE
            #    (install expects releases URL, list-remote expects API URL)
            replace_in_file(
                self,
                list_remote_path,
                'TOFUENV_REMOTE="${TOFUENV_REMOTE:-https://api.github.com/repos/opentofu/opentofu/releases}";',
                'TOFUENV_REMOTE="${TOFUENV_API_REMOTE:-https://api.github.com/repos/opentofu/opentofu/releases}";',
            )

            # 4. bashlog: replace /tmp with ${TMPDIR:-$HOME/tmp} (OHOS /tmp is read-only, E002)
            bashlog_path = os.path.join(self.source_folder, "lib", "tofuenv-bashlog.sh")
            replace_in_file(
                self,
                bashlog_path,
                'local file_path="${BASHLOG_FILE_PATH:-/tmp/${0##*/}.log}";',
                'local file_path="${BASHLOG_FILE_PATH:-${TMPDIR:-$HOME/tmp}/${0##*/}.log}";',
            )
            replace_in_file(
                self,
                bashlog_path,
                'local json_path="${BASHLOG_JSON_PATH:-/tmp/${0##*/}.log.json}";',
                'local json_path="${BASHLOG_JSON_PATH:-${TMPDIR:-$HOME/tmp}/${0##*/}.log.json}";',
            )

            # 5. install: ensure TMPDIR fallback before mktemp
            install_path = os.path.join(self.source_folder, "libexec", "tofuenv-install")
            replace_in_file(
                self,
                install_path,
                'tmpdir_arg="-t";',
                'export TMPDIR="${TMPDIR:-$HOME/tmp}"\ntmpdir_arg="-t";',
            )

    def package(self):
        # Copy script directories preserving structure
        for script_dir in ["bin", "lib", "libexec", "scripts", "share"]:
            src_dir = os.path.join(self.source_folder, script_dir)
            if os.path.isdir(src_dir):
                copy(
                    self,
                    "*",
                    src=src_dir,
                    dst=os.path.join(self.package_folder, script_dir),
                )

        # Copy essential files (CHANGELOG.md needed by tofuenv --version)
        copy(self, "CHANGELOG.md", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)
        copy(self, "README.md", src=self.source_folder, dst=self.package_folder)

        # Ensure scripts in bin/ and libexec/ are executable
        for exec_dir in ["bin", "libexec"]:
            dir_path = os.path.join(self.package_folder, exec_dir)
            if os.path.isdir(dir_path):
                for filename in os.listdir(dir_path):
                    filepath = os.path.join(dir_path, filename)
                    if os.path.isfile(filepath):
                        os.chmod(filepath, 0o755)

    def package_info(self):
        # Command-line tool — no libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        # OHOS: github.com:443 is blocked, use mirror for release downloads
        if self.settings.os == "OHOS":
            self.runenv_info.define(
                "TOFUENV_REMOTE",
                "https://ghfast.top/https://github.com/opentofu/opentofu/releases",
            )
