import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class AwscliConan(ConanFile):
    """AWS CLI v2 2.34.56 - pure Python CLI, vendored botocore/s3transfer.

    Product: lib/python3.12/site-packages/awscli/ (incl. vendored
    botocore/s3transfer and data/ service models) + bin/aws entry script.
    flit_core custom backend (backends/pep517.py) is only used by the
    official wheel build; this port follows the python-require template:
    copytree staging + generated bin/aws entry (docutils precedent).
    Top-level `import botocore/s3transfer` is aliased to the vendored
    packages by TopLevelImportAliasFinder in awscli/__init__.py.
    """
    name = "awscli"
    version = "2.34.56"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://aws.amazon.com/cli/"
    description = ("AWS Command Line Interface v2 - pure Python CLI "
                   "(vendored botocore/s3transfer, Apache-2.0)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        # 把 conandata.yml 声明的 patch 文件导出到 conan cache。
        # 注意：必须在 export_sources()（而非 export()）中调用——
        # conan 2.29 export() 阶段 export_sources_folder 尚未设置，
        # export_conandata_patches 内部 os.path.join(…None) 会抛 TypeError
        # （a52dec 先例）。
        export_conandata_patches(self)

    # awscli 2.34.56 upstream declared deps (pyproject.toml):
    #   colorama>=0.2.5,<0.4.7 | docutils>=0.10,<0.20 | ruamel_yaml>=0.15.0,<=0.19.1
    #   ruamel_yaml_clib>=0.2.0,<=0.2.15 | prompt-toolkit>=3.0.24,<3.0.52
    #   distro>=1.5.0,<1.9.0 | awscrt==0.32.2 | python-dateutil>=2.1,<=2.9.0
    #   jmespath>=0.7.1,<1.1.0 | urllib3>=1.25.4,<=2.6.3 | wcwidth<0.3.0
    #
    # Dependency decision (R36 gate: declaring unpublished deps fails L0i,
    # so only published + startup-chain-required deps are declared; the
    # missing/out-of-range deps are recorded in README.md and this round's
    # report, not silently dropped):
    #   - in-range & published: colorama/0.4.6, ruamel-yaml/0.19.1,
    #     ruamel-yaml-clib/0.2.15
    #   - published but out-of-range (top-level imports of vendored
    #     botocore require them at startup; declared to form a resolvable
    #     graph; exact version alignment needs separately published
    #     old recipes: jmespath 1.0.x / python-dateutil 2.9.0 / urllib3
    #     2.6.x): jmespath/1.1.0, python-dateutil/2.9.0.post0,
    #     urllib3/2.7.0
    #   - runtime dep of dateutil: six/1.17.0 (published)
    #   - docutils/0.23: published on ohpcd (web-review + 实测) and
    #     measured API-compatible with awscli 2.34.56 help.py
    #     (publish_string + manpage.Writer render, 见 builder-round3-
    #     report 实测输出). Declared. Note: `aws help` output still fails
    #     at the groff/mandoc + pager pipeline because OHOS Python
    #     subprocess cannot resolve bare command names via PATH (F5) ->
    #     受控报错, see patches/0002 + README.
    #   - NOT published (declaring would fail R36) -> this round's blocker:
    #     distro (top-level import in clidriver, required at startup),
    #     awscrt==0.32.2 (unconditional top-level imports in vendored
    #     botocore credentials.py:30 / utils.py:42 / httpchecksum.py:28,
    #     required at startup; C extension needs separate adaptation),
    #     prompt-toolkit/wcwidth (autoprompt feature paths only)
    requires = (
        "colorama/0.4.6",
        "ruamel-yaml/0.19.1",
        "ruamel-yaml-clib/0.2.15",
        "jmespath/1.1.0",
        "python-dateutil/2.9.0.post0",
        "urllib3/2.7.0",
        "six/1.17.0",
        "docutils/0.23",
    )

    def source(self):
        get(self, **self.conan_data["sources"]["awscli"], strip_root=True)

    def build(self):
        # round 2: 应用 conandata.yml 声明的守护补丁（awscrt/distro/
        # docutils 缺失时启动链可降级，见 patches/ 与 README）
        apply_conandata_patches(self)
        # pip metadata builds are unreliable in CI - copytree source to
        # a staging dir under self.build_folder - pure Python, no compilation
        # round 3 (WR-008): staging 用 build_folder 子目录而非硬编码绝对路径
        # （避免并发构建互相覆盖/残留）。
        staging = os.path.join(self.build_folder, "awscli-stage")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                ".changes", ".github", ".git", ".gitignore",
                ".coveragerc", ".pre-commit-config.yaml",
                "CHANGELOG.rst", "CODE_OF_CONDUCT.md",
                "CONTRIBUTING.rst", "README*", "LICENSE*",
                "Makefile.in", "pyproject.toml",
                "requirements*", "backends", "bin", "docker",
                "doc", "exe", "m4", "macpkg", "proposals",
                "tests"))

    def package(self):
        # round 3 (WR-008): 与 build() 共用 self.build_folder 下的
        # 同一 staging 子目录，不再硬编码绝对路径。
        staging = os.path.join(self.build_folder, "awscli-stage")
        if not os.path.isdir(staging):
            # [OHOS 守护 round 3] staging 缺失 = build() 未成功或构建目录
            # 被清理——拒绝继续打包，避免产出残缺包。
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # copy awscli/ (incl. vendored botocore/s3transfer and data/)
        src_pkg = os.path.join(staging, "awscli")
        if not os.path.isdir(src_pkg):
            # [OHOS 守护 round 3] staging 内无 awscli/ 源码包 = 源码布局
            # 异常（如 ignore_patterns 误伤）——如实报错而非静默产出残包。
            raise ConanException(f"awscli package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "awscli"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        # generate bin/aws entry (docutils precedent: shebang + sys.path
        # injection + call awscli.clidriver.main)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        site_packages_rel = os.path.join("lib", pyver, "site-packages")
        script_content = (
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
            "_sp = os.path.join(_pkg_root, \"{}\")\n".format(site_packages_rel) +
            "if _sp not in sys.path:\n"
            "    sys.path.insert(0, _sp)\n"
            "from awscli.clidriver import main\n"
            "if __name__ == \"__main__\":\n"
            "    sys.argv[0] = sys.argv[0].removesuffix(\".exe\")\n"
            "    sys.exit(main())\n"
        )
        script_path = os.path.join(bin_dir, "aws")
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

    def package_info(self):
        # python-require type - runtime env provided by conanrun;
        # bin/aws entry is executed directly by the L2 smoke test
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
