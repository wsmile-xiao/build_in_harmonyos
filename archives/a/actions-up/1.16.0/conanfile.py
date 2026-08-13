import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class ActionsUpConan(ConanFile):
    name = "actions-up"
    version = "1.16.0"
    description = "Interactive CLI tool to update GitHub Actions with SHA pinning or preserved refs"
    license = "MIT"
    homepage = "https://github.com/azat-io/actions-up"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"actions-up is prepared for Linux/OHOS targets only, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("actions-up supports OHOS armv8 only")
        if not shutil.which("node"):
            raise ConanInvalidConfiguration("actions-up requires Node.js in PATH")
        if not shutil.which("npm"):
            raise ConanInvalidConfiguration("actions-up requires npm in PATH")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        workspace = self._workspace()
        if os.path.isdir(workspace):
            shutil.rmtree(workspace)
        shutil.copytree(self.source_folder, workspace, symlinks=True)

        npm_cache = os.path.join(self._workspace_root(), "npm-cache")
        tmpdir = os.path.join(self._workspace_root(), "tmp")
        os.makedirs(npm_cache, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)

        hb_bin = os.path.expanduser("~/.harmonybrew/bin")
        prefix = f'PATH="{hb_bin}:$PATH" '

        self.run(
            prefix
            + f'NPM_CONFIG_CACHE="{npm_cache}" TMPDIR="{tmpdir}" '
            + "npm install --omit=dev --ignore-scripts --no-audit --no-fund "
            + "--package-lock=false --no-save "
            + "enquirer@2.4.1 nanospinner@1.2.2 picocolors@1.1.1 "
            + "semver@7.8.5 yaml@2.9.0",
            cwd=workspace,
        )

        self.run(prefix + "node bin/actions-up.js --version", cwd=workspace)
        self.run(prefix + "node bin/actions-up.js --help", cwd=workspace)

    def package(self):
        workspace = self._workspace()
        app_dir = os.path.join(self.package_folder, "res", "actions-up")

        for directory in ("bin", "dist", "node_modules"):
            src = os.path.join(workspace, directory)
            dst = os.path.join(app_dir, directory)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)

        for filename in ("package.json", "license.md", "readme.md"):
            copy(
                self,
                filename,
                src=workspace,
                dst=app_dir,
                keep_path=False,
            )

        copy(
            self,
            "license.md",
            src=workspace,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        launcher = os.path.join(self.package_folder, "bin", "actions-up")
        save(
            self,
            launcher,
            "#!/system/bin/sh\n"
            "set -eu\n"
            'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
            'exec node "$script_dir/../res/actions-up/bin/actions-up.js" "$@"\n',
        )
        os.chmod(
            launcher,
            os.stat(launcher).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _workspace_root(self):
        if str(self.settings.os) == "OHOS":
            root = os.environ.get(
                "OHOS_NODE_WORKDIR",
                "/data/storage/el2/base/cache/actions-up-conan",
            )
        else:
            root = os.path.join(self.build_folder, ".node-work")
        os.makedirs(root, exist_ok=True)
        return root

    def _workspace(self):
        return os.path.join(self._workspace_root(), self.version)
