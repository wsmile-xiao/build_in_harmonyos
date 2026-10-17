import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["ncdc"]
        ncdc = os.path.join(dep.package_folder, "bin", "ncdc")
        work = os.path.join(self.build_folder, "ncdcwork")
        os.makedirs(work, exist_ok=True)
        # ncdc 为动态链接可执行文件（NEEDED libgnutls.so.30 / libglib-2.0.so.0
        # / libncursesw.so.6 …）。VirtualRunEnv(conanrun) 的 LD_LIBRARY_PATH 未
        # 覆盖传递依赖（gnutls 等）的 libdir，实测 test 期直接
        # `Error loading shared library libgnutls.so.30: (needed by .../p/bin/ncdc)`
        # （CI #44337，7 项断言全 FAIL）。故显式汇总图中全部依赖 libdir，
        # 以前缀形式并入 LD_LIBRARY_PATH（保留 conanrun 既有取值）。
        libdirs = []
        for d in self.dependencies.values():
            pf = getattr(d, "package_folder", None)
            if not pf:
                continue
            for libdir in d.cpp_info.aggregated_components().libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(pf, libdir))
        prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(
            ":".join(dict.fromkeys(libdirs)))
        # OHOS /system/bin/sh（mksh）不能执行 ELF 二进制 → 用 bash 包一层；
        # HMFS sh 的 here-doc 临时文件无视 TMPDIR 硬落只读 /tmp
        # （ctemplate CI #44049 实测）→ 改用 hnp bash + TMPDIR 重定向。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{prefix}TMPDIR="{work}" "{bash}" '
                 f'"{os.path.join(self.source_folder, "test.sh")}" "{ncdc}" "{work}"',
                 env="conanrun")
