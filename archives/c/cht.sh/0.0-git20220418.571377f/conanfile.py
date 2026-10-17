#!/usr/bin/env python3
"""Conan recipe — cht.sh 0.0-git20220418.571377f (pure shell CLI client).

cht.sh is the command-line client for the cheat.sh service
(https://cheat.sh): shell mode, query history, clipboard integration,
stealth mode, tab completion. It is a pure bash script — no compilation.

Package content follows the Debian packaging rules (cht.sh
0.0~git20220418.571377f-2, Architecture: all):
  share/cht.sh.txt             -> bin/cht.sh
  share/bash_completion.txt    -> share/bash-completion/completions/cht.sh
  share/fish.txt               -> share/fish/vendor_completions.d/cht.sh.fish
  share/zsh.txt                -> share/zsh/site-functions/_cht.sh

Runtime dependencies (not Conan requires): curl (required), rlwrap (shell
mode), xsel (clipboard).
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, chmod
from conan.tools.layout import basic_layout


class ChtShConan(ConanFile):
    name = "cht.sh"
    version = "0.0-git20220418.571377f"
    description = "Command line client for the cheat.sh service"
    license = "MIT"
    homepage = "https://cheat.sh"
    url = "https://github.com/chubin/cheat.sh"

    package_type = "application"
    # L0p requires all four settings; compiler/build_type unused (pure shell)
    # but kept for OHOS profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # OHOS has no /bin/bash hardlink (bash lives on $PATH), so the
        # upstream shebang `#!/bin/bash` would fail with 127 when the
        # installed script is executed directly. Rewrite to the portable
        # `#!/usr/bin/env bash` form.
        script = os.path.join(self.source_folder, "share", "cht.sh.txt")
        with open(script, "r") as f:
            content = f.read()
        if content.startswith("#!/bin/bash"):
            content = "#!/usr/bin/env bash\n" + content[len("#!/bin/bash\n"):]
            with open(script, "w") as f:
                f.write(content)
            self.output.info("Patched shebang: #!/bin/bash -> #!/usr/bin/env bash")

    def package(self):
        src = os.path.join(self.source_folder, "share")
        pkg = self.package_folder

        # CLI client: share/cht.sh.txt -> bin/cht.sh (755)
        bin_dir = os.path.join(pkg, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "cht.sh.txt", src, bin_dir)
        script = os.path.join(bin_dir, "cht.sh")
        os.replace(os.path.join(bin_dir, "cht.sh.txt"), script)
        chmod(self, script, 0o755)

        # shell completion files
        completions = [
            ("bash_completion.txt", "share/bash-completion/completions/cht.sh"),
            ("fish.txt", "share/fish/vendor_completions.d/cht.sh.fish"),
            ("zsh.txt", "share/zsh/site-functions/_cht.sh"),
        ]
        for src_name, dst_rel in completions:
            dst = os.path.join(pkg, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            copy(self, src_name, src, os.path.dirname(dst))
            os.replace(os.path.join(os.path.dirname(dst), src_name), dst)
            chmod(self, dst, 0o644)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
