#!/usr/bin/env python3
"""Conan recipe — ruptime 1.8 (pure shell client/server, no compilation).

poor man's ruptime (https://github.com/alexmyczko/ruptime): two bash
scripts (ruptime client + ruptimed collection daemon), two man pages and
a sample config. Installation only copies files; there is no build step
and no upstream test suite (see test_package/MANIFEST.yml audit).

Platform adaptations for OHOS:
  1. Shebang fix: #!/bin/bash -> #!/usr/bin/env bash (/bin/bash does not
     exist on HarmonyOS; bash is provided via requires bash/5.3 on PATH).
  2. Config dir: /etc/ruptime -> ${RUPTIME_CONF_DIR:-/etc/ruptime}
     (/etc is read-only on HarmonyOS PC; the env override keeps the
     default path but lets test_package stage a hermetic config
     under $TMPDIR).
"""

import os

from conan import ConanFile
from conan.tools.files import chmod, copy, get
from conan.tools.layout import basic_layout


class RuptimeConan(ConanFile):
    name = "ruptime"
    version = "1.8"
    description = "poor man's ruptime: client/server host-status overview via shell scripts"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/alexmyczko/ruptime"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Scripts use bash extensions (==, &>, process substitution);
        # OHOS ships no /bin/bash, so depend on the adapted bash package.
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        bash = os.path.join(
            self.dependencies["bash"].package_folder, "bin", "bash")
        for script in ("ruptime", "ruptimed"):
            path = os.path.join(self.source_folder, script)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            orig = content
            if content.startswith("#!/bin/bash"):
                content = ("#!/usr/bin/env bash\n"
                           + content[len("#!/bin/bash\n"):])
                self.output.info(
                    "Patched shebang: #!/bin/bash -> "
                    "#!/usr/bin/env bash (%s)" % script)
            # OHOS adaptation: /etc is read-only on HarmonyOS PC
            # (true-device mkdir /etc/ruptime fails with Read-only
            # file system). Respect $RUPTIME_CONF_DIR when set,
            # defaulting to /etc/ruptime so upstream behaviour is
            # preserved; test_package exports a $TMPDIR staging dir.
            if "/etc/ruptime" in content:
                content = content.replace(
                    "/etc/ruptime", "${RUPTIME_CONF_DIR:-/etc/ruptime}")
                self.output.info(
                    "Patched config path for RUPTIME_CONF_DIR (%s)"
                    % script)
            if content != orig:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            # No upstream test suite exists (pure shell project, no
            # Makefile/check target); validate with a bash syntax check.
            self.run('"%s" -n "%s"' % (bash, path))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for script in ("ruptime", "ruptimed"):
            copy(self, script, src=self.source_folder, dst=bin_dir)
            chmod(self, os.path.join(bin_dir, script), 0o755)
        man_dir = os.path.join(self.package_folder, "share", "man")
        copy(self, "ruptime.1",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(man_dir, "man1"))
        copy(self, "ruptimed.8",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(man_dir, "man8"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "ruptime"))
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        bash_bin = os.path.join(
            self.dependencies["bash"].package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bash_bin)
        self.runenv_info.prepend_path("PATH", bash_bin)
