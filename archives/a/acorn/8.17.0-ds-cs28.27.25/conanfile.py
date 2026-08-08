import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class AcornConan(ConanFile):
    name = "acorn"
    version = "8.17.0-ds-cs28.27.25"
    description = "ECMAScript parser command-line tool"
    license = "MIT"
    homepage = "https://github.com/acornjs/acorn"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch"

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("acorn supports only OHOS armv8")
        if not shutil.which("node") or not shutil.which("npm"):
            raise ConanInvalidConfiguration("acorn requires Node.js and npm in PATH")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The OHOS hnp node ships a broken npm (native errno check aborts on
        # every invocation), so prefer Harmonybrew's npm/node when present by
        # prepending its bin to PATH for this run. validate() still passes
        # because shutil.which sees hnp's npm first.
        hb_bin = os.path.expanduser("~/.harmonybrew/bin")
        path_prefix = f'PATH="{hb_bin}:$PATH"'
        self.run(f"{path_prefix} npm ci --ignore-scripts --no-audit --no-fund", cwd=self.source_folder)
        # rollup 4.x's optional @rollup/rollup-openharmony-arm64 native module
        # is an ELF dropped onto HMDFS, whose seclabel refuses exec (Permission
        # denied, ERR_DLOPEN_FAILED). rollup 4.60.1 has no auto wasm fallback,
        # so replace the native `rollup` package with @rollup/wasm-node (same
        # dist/bin/rollup CLI shape, wasm-backed parse) before running the tests.
        nm = os.path.join(self.source_folder, "node_modules")
        self.run(f"{path_prefix} npm uninstall rollup --no-audit --no-fund", cwd=self.source_folder)
        self.run(f"{path_prefix} npm install @rollup/wasm-node@^4.60.1 --no-audit --no-fund --ignore-scripts", cwd=self.source_folder)
        # Re-point .bin/rollup at the wasm CLI (rm stale symlink first, it
        # survives npm uninstall rollup) and stub the `rollup` import path so
        # acorn's rollup.config.mjs (imports @rollup/plugin-buble, not rollup
        # directly) and the `rollup -c ...` script both resolve to wasm.
        rollup_bin_link = os.path.join(nm, ".bin", "rollup")
        if os.path.lexists(rollup_bin_link):
            os.remove(rollup_bin_link)
        os.symlink(os.path.join(nm, "@rollup", "wasm-node", "dist", "bin", "rollup"),
                   rollup_bin_link)
        # @rollup/plugin-buble peer-deps `rollup`; stub a thin shim so npm's
        # module resolver still finds `rollup` and its ./dist/* subpaths via
        # @rollup/wasm-node (same dist layout, wasm-backed).
        rollup_stub = os.path.join(nm, "rollup")
        if os.path.lexists(rollup_stub):
            os.remove(rollup_stub)
        os.symlink(os.path.join(nm, "@rollup", "wasm-node"), rollup_stub)
        self.run(f"{path_prefix} npm run test", cwd=self.source_folder)

    def package(self):
        app_dir = os.path.join(self.package_folder, "res", "acorn")
        copy(self, "*", src=os.path.join(self.source_folder, "acorn", "dist"), dst=os.path.join(app_dir, "dist"), keep_path=True)
        copy(self, "acorn", src=os.path.join(self.source_folder, "acorn", "bin"), dst=os.path.join(app_dir, "bin"), keep_path=False)
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "acorn"), dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        launcher = os.path.join(self.package_folder, "bin", "acorn")
        save(self, launcher, "#!/bin/sh\nset -eu\nscript_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\nexec node --jitless \"$script_dir/../res/acorn/bin/acorn\" \"$@\"\n")
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
