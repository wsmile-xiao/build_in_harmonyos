#!/usr/bin/env python3
"""Conan test_package — ballandpaddle 0.8.1（应用包）。

test.sh 实跑打包后的 bin/ballandpaddle，断言 --version / --help / 参数校验
三条真实输出路径与安装布局（30 项）。不是 print-only stub（R34）：CI 的
destructive 检查会把包的 bin/ 挪走再重跑，期望失败，证明断言真的依赖产物。
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class BallandpaddleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return

        pkg_folder = self.dependencies[self.tested_reference_str].package_folder

        # VirtualRunEnv(conanrun) 的 LD_LIBRARY_PATH 未覆盖**传递**依赖的 libdir
        # （ncdc CI #44337 实测：libgnutls.so.30 加载失败）。ballandpaddle 静态链
        # sdl12-compat/sdl_image/sdl_mixer/sdl_ttf，但 guile 是 shared=True，
        # 其 NEEDED（libgc / libffi / libunistring / libgmp）同样是传递依赖，
        # 故显式汇总全图 libdir 并入 LD_LIBRARY_PATH。
        # guile 的 GUILE_LOAD_PATH / GUILE_LOAD_COMPILED_PATH 由 guile 配方的
        # runenv_info 注入，conanrun 环境已带上（scm_boot_guile 启动时要用）。
        libdirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                libdirs.append(
                    libdir if os.path.isabs(libdir) else os.path.join(folder, libdir)
                )
        prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(
            ":".join(dict.fromkeys(libdirs))
        )

        # OHOS /system/bin/sh（mksh）不能可靠执行 ELF 二进制 → 用 bash 包一层；
        # HMDFS 下 here-doc 的临时文件无视 TMPDIR 硬落只读 /tmp，故显式给 work 目录。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        work = os.path.join(self.build_folder, "bapwork")
        os.makedirs(work, exist_ok=True)
        script = os.path.join(self.source_folder, "test_ballandpaddle.sh")
        self.run(
            f'{prefix}TMPDIR="{work}" "{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )
