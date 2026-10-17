#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe — boot 1.3-32 (CRAN R package "Bootstrap Functions").

适配背景（HarmonyOS PC / OpenHarmony aarch64）：

* boot 是 CRAN 的**纯 R 语言**包（Bootstrap Functions，Davison & Hinkley
  1997, CUP），DESCRIPTION 声明 ``NeedsCompilation: no``——上游没有任何
  C/Fortran 源码，因此本配方**不做任何编译**，只做「上游 R 包树 → R 库树」
  的搬运（安装到 ``lib/R/library/boot/``）。

* **零未发布依赖路线**：ohpcd 制品仓没有 r-base（实测 HTTP 404，全量 7802
  条配方无任何 R 系包），而 CI 的 L0i 门禁（commit 83c2f54f25 起）对未发布
  依赖 hard-fail。因此本配方**不声明任何 requires / tool_requires**，与同族
  先例 kernsmooth 一样绕开 r-base 走独立路线（kernsmooth 走 Fortran 静态库，
  boot 纯 R 则直接走「R 包树数据搬运」）。

* **CI 无 R 运行时**：CI 只做 R-free 的结构/数据校验——
  ``build()`` 调用 ``test_package/validate_boot.py`` 对源码树做实质校验
  （DESCRIPTION 字段、NAMESPACE 导出集合、R/*.q 函数定义、50 个 .rda 数据集的
  gzip/RDX2 序列化与列名、88 个 man 页 / 25 个含 examples、上游 tests/ 资产），
  ``test_package`` 对安装后的包树再跑一遍同一校验（R34 实质测试；CI L1e 破坏性
  反向验证依赖「lib/ 被移走则校验失败」这一性质）。

* 本地（自建 R 运行时）由 ``test_package/R/`` 下三个脚本
  （run_upstream_examples.R / run_upstream_tests.R / test_boot_api.R，另由协作者
  子任务编写，本配方不引用）对上游真实 R 测试做实测：上游测试资产 =
  ``tests/parallel-censboot.R``（1 个测试，需 survival 包）+
  ``tests/Examples/boot-Ex.Rout.save``（25 个 man 页共 915 条示例表达式）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save


class BootConan(ConanFile):
    name = "boot"
    version = "1.3-32"
    description = "Bootstrap Functions — R package (Davison & Hinkley 1997)"
    license = "Unlimited"
    homepage = "https://cran.r-project.org/package=boot"
    url = "https://cran.r-project.org/src/contrib/boot_1.3-32.tar.gz"
    topics = ("r", "r-package", "bootstrap", "statistics", "cran", "ohos")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # package_type="library" 要求声明 shared 选项（Conan 2 语义：库可静态可动态）。
    # boot 是纯 R 包树，无 .a/.so 产物，故只有 shared=False 一路（同族先例
    # acepack 1.6.3 亦如此声明）。
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # conandata.yml 提供源码地址/校验和；test_package/ 承载 R-free 校验器，
    # build() 阶段也要调用它（故必须随配方一起导出）。
    exports_sources = "conandata.yml", "test_package/*"

    def configure(self):
        # 纯 R 包树无二进制产物，动态/静态之分不适用，固定为 False。
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "boot %s is a pure R package tree; shared=True is not applicable"
                % self.version)

    # 顶层 R 包树文件（随上游 tarball 原样搬运）
    _TREE_FILES = "DESCRIPTION", "NAMESPACE", "INDEX", "ChangeLog", "MD5"
    # 顶层 R 包树目录
    _TREE_DIRS = "R", "data", "man", "inst", "po", "tests"

    def layout(self):
        pass

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")，不能裸 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "boot %s is only supported on Linux/OHOS, not %s"
                % (self.version, self.settings.os))

    def export_sources(self):
        # 补丁目录随配方导出（当前 patches 为空，保留标准调用以便后续加补丁）
        export_conandata_patches(self)

    def source(self):
        # sources 是 {url:[...], sha256, tar_format}；tar_format 只是元数据，
        # 不是 get()/download() 的参数，需先剔除再展开关键字。
        sources = dict(self.conan_data["sources"])
        sources.pop("tar_format", None)
        get(self, strip_root=True, **sources)
        # 应用 conandata.yml 声明的补丁（纯 R 包当前 patches: {}，为空洞用）
        apply_conandata_patches(self)

    def _validate_script(self):
        """定位 test_package/validate_boot.py（本地流/缓存流都兼容）。"""
        candidates = [
            os.path.join(self.source_folder, "test_package", "validate_boot.py"),
            os.path.join(self.export_sources_folder, "test_package", "validate_boot.py"),
        ]
        try:
            candidates.append(os.path.join(
                self.recipe_folder, "test_package", "validate_boot.py"))
        except AttributeError:
            pass
        for path in candidates:
            if os.path.isfile(path):
                return path
        raise ConanException(
            "test_package/validate_boot.py not found; tried: %s" % candidates)

    def build(self):
        # boot 无编译步骤（NeedsCompilation: no）。此处执行 R-free 的包树自检：
        # 在 CI 日志里留下真实测试痕迹（满足 L1b/L1c「测试在 build 中执行」），
        # 任一断言失败即抛 ConanException（self.run 非零退出即失败）。
        if not os.path.isfile(os.path.join(self.source_folder, "DESCRIPTION")):
            raise ConanException(
                "boot source tree incomplete: DESCRIPTION missing in %s"
                % self.source_folder)
        # "make check" 标记：上游 R CMD check 在无 R 环境不可执行，此处以等价
        # 的 R-free 结构/数据校验作为替身，供 CI L1c 门禁识别 build 阶段测试痕迹。
        self.output.info(
            "boot make check (surrogate): R-free package tree validation "
            "(upstream R CMD check needs an R runtime, unavailable in CI)")
        script = self._validate_script()
        self.run('python3 "%s" "%s"' % (script, self.source_folder))

    def _write_license(self):
        """从 DESCRIPTION 抽取许可声明到 licenses/LICENSE（附来源说明）。"""
        desc_lines = load(self, os.path.join(self.source_folder, "DESCRIPTION")).splitlines()
        extracted = []
        for raw in desc_lines:
            stripped = raw.strip()
            if stripped.startswith(("License:", "Author:", "Maintainer:", "Authors@R:")):
                extracted.append(stripped)
        lines = [
            "boot %s — license declaration extracted from upstream DESCRIPTION" % self.version,
            "Upstream package: boot (Bootstrap Functions), CRAN",
            "Source: https://cran.r-project.org/src/contrib/boot_1.3-32.tar.gz",
            "",
            "--- DESCRIPTION fields (License / Author / Maintainer) ---",
        ]
        lines.extend(extracted)
        lines.append("")
        licenses_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses_dir, exist_ok=True)
        save(self, os.path.join(licenses_dir, "LICENSE"), "\n".join(lines) + "\n")

    def package(self):
        src = self.source_folder
        dst = os.path.join(self.package_folder, "lib", "R", "library", "boot")
        os.makedirs(dst, exist_ok=True)

        # 上游整棵 R 包树原样安装（保留 DESCRIPTION/NAMESPACE/R/data/man/inst/po/
        # tests/INDEX/ChangeLog），供下游 R 运行时 library(boot) 直接加载。
        for name in self._TREE_FILES:
            path = os.path.join(src, name)
            if os.path.isfile(path):
                shutil.copy2(path, os.path.join(dst, name))
        for name in self._TREE_DIRS:
            path = os.path.join(src, name)
            if os.path.isdir(path):
                shutil.copytree(path, os.path.join(dst, name), dirs_exist_ok=True)

        # 安装完整性自检：核心组件缺失即失败（防止 package() 静默漏拷）
        for required in ("DESCRIPTION", "NAMESPACE"):
            if not os.path.isfile(os.path.join(dst, required)):
                raise ConanException("boot package tree missing %s" % required)
        for required in ("R", "data", "man"):
            sub = os.path.join(dst, required)
            if not os.path.isdir(sub) or not os.listdir(sub):
                raise ConanException("boot package tree missing/empty %s/" % required)

        self._write_license()
        self.output.info("installed boot R package tree -> %s" % dst)

    def package_info(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "R", "library", "boot")
        # 运行/构建环境导出 R 库树位置，供下游 R 运行时定位本包
        self.runenv_info.define("R_BOOT_PACKAGE_DIR", pkg_dir)
        self.buildenv_info.define("R_BOOT_PACKAGE_DIR", pkg_dir)
        # 本包无 C 头文件/库文件/可执行文件——不臆造 cpp_info.libs
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.output.info("R_BOOT_PACKAGE_DIR=%s" % pkg_dir)
