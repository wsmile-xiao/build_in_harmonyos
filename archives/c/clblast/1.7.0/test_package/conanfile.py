#!/usr/bin/env python3
"""Conan test_package for clblast 1.7.0 — Conan L1 consumer test.

Compiles a small C program that calls the CLBlast C API (CLBlastSaxpy) on a real
OpenCL device and verifies the result, proving the packaged libclblast + headers
link and run correctly on the target.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Conan 2 的 test_package 里，`self.dependencies` 对 clblast 的**传递**
        # 依赖（opencl-headers / opencl-icd-loader）只返回空壳，
        # package_folder 为 None（build() 里拼绝对路径会 TypeError）。这里把
        # 它们声明为 test_package 的直接依赖（版本与主配方一致，Conan 去重，
        # 不会引入第二份），package_folder 即可用（与主配方 generate() 同款）。
        self.requires("opencl-headers/2026.05.29")
        self.requires("opencl-icd-loader/v2024.05.08")

    def build(self):
        dep = self.dependencies["clblast"].cpp_info
        incs = [p for p in dep.includedirs]
        # clblast_c.h includes <CL/opencl.h>; headers come from opencl-headers
        # (transitive dep). opencl-headers 是 header-only、无 layout，其
        # cpp_info.includedirs 是相对包目录的 "include"，直接 -Iinclude 在构建
        # 目录下找不到头文件；必须用 package_folder 拼绝对路径（与主配方
        # generate() 里 OPENCL_INCLUDE_DIRS 同款做法）。
        ocl = self.dependencies["opencl-headers"]
        incs.append(os.path.join(ocl.package_folder, "include"))
        inc = " ".join("-I" + p for p in incs)
        # Link libclblast + libOpenCL (from opencl-icd-loader) + libm.
        libdirs = [d for d in dep.libdirs]
        icd = self.dependencies["opencl-icd-loader"]
        libdirs.append(os.path.join(icd.package_folder, "lib"))
        ld = " ".join("-L" + d for d in libdirs)
        # libclblast 是 C++ 静态库，其归档内对象引用 libc++ 运行时符号
        # （operator new/delete、__cxa_*、std::__n1::* 等）。若用 C 驱动
        # （clang）链接会报 ld.lld undefined symbol。必须用 C++ 驱动
        # （clang++）编译链接，自动带上 libc++；clblast_c.h 有 extern "C"
        # 保护，test_clblast.c 按 C++ 编译不影响 C API 链接。
        cxx = self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("cpp", "/data/service/hnp/bin/clang++")
        self.run("{cxx} test_clblast.c -o test_clblast {inc} {ld} -Wl,-rpath-link,{ld0} "
                 "-lclblast -lOpenCL -lm".format(cxx=cxx, inc=inc, ld=ld, ld0=libdirs[0]))

    def _probe_opencl_runtime(self):
        """低成本补齐尝试（与主配方 _probe_opencl_configs 同款，证据驱动）：
        探测真机上已存在的 OpenCL 实现（系统 libOpenCL.so / vendor ICD）并写入
        os.environ，让消费者测试同样能激活真机 OpenCL，而非 -1001 直接中止。
        主配方探针实测（upstream_test 阶段，见 MANIFEST.yml）：仅
        LD_LIBRARY_PATH 前置系统库目录不够——test() 里 `self.run(..., env=
        "conanrun")` 的 conanrun env 会把 LD_LIBRARY_PATH 覆盖为依赖包目录，
        /vendor/lib64 丢失，测试仍报 "No OpenCL platform found"；必须用
        LD_PRELOAD 强制加载系统 libOpenCL.so（conanrun env 不包含 LD_PRELOAD，
        不会被覆盖），与主配方选中的探针配置一致。找不到实现时保持原环境，
        测试如实失败。"""
        import glob as _glob

        # 主配方探针实测有效的激活方式：LD_PRELOAD 系统 OpenCL 实现
        # （/vendor/lib64/libOpenCL.so，Maleoon 916，platforms=1 devices=1）。
        sys_lib_dirs = [
            "/system/lib64", "/system/lib",
            "/vendor/lib64", "/vendor/lib",
            "/odm/lib64", "/odm/lib",
            "/lib64", "/lib",
            "/usr/lib64", "/usr/lib",
        ]
        for d in sys_lib_dirs:
            p = os.path.join(d, "libOpenCL.so")
            if os.path.isfile(p):
                print(f"[clblast] test_package 发现系统 libOpenCL.so: {p}，LD_PRELOAD 激活")
                os.environ["LD_PRELOAD"] = p
                return
        # 无系统实现时退回 vendor ICD 目录探测
        icd_dirs = [
            "/etc/OpenCL/vendors",
            "/etc/OpenCL/vendors.d",
            "/vendor/etc/OpenCL/vendors",
            "/system/etc/OpenCL/vendors",
            "/odm/etc/OpenCL/vendors",
        ]
        for d in icd_dirs:
            try:
                icds = sorted(_glob.glob(os.path.join(d, "*.icd")))
            except OSError:
                icds = []
            if icds and not os.environ.get("OCL_ICD_VENDORS"):
                print(f"[clblast] test_package 发现 OpenCL ICD: {d} -> {icds}")
                os.environ["OCL_ICD_VENDORS"] = d
                break

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 低成本补齐尝试：探测并激活真机已存在的 OpenCL 实现，让消费者冒烟
        # 测试在真实设备上运行（无实现时如实失败，不伪造通过）。
        self._probe_opencl_runtime()
        # HMBS 注入 SHELL=/bin/sh；真机 /tmp 只读、HNP bash 在 HMFS/HMDFS 上
        # getcwd 失败（readonly_tmp 平台诊断，addchain 同款规避）：
        # 以 $TMPDIR 为 cwd 启动测试，用绝对路径调用被测二进制。
        shell = os.environ.get("SHELL", "/bin/sh")
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or \
            os.environ.get("TEMP") or "."
        bin_path = os.path.join(self.build_folder, "test_clblast")
        run_cmd = "{} -c 'cd \"{}\" && \"{}\"'".format(shell, tmpdir, bin_path)
        self.run(run_cmd, env="conanrun")

        # HMBS 硬门禁：真实运行成功（self.run 非零即抛）后才输出标记；
        # discovered/passedCount 为 test_package 真实用例数 1，绝不伪造。
        import json as _json
        marker = {
            "executed": True,
            "passed": True,
            "discovered": 1,
            "passedCount": 1,
            "command": run_cmd,
        }
        print(f'HMBS_TEST_PACKAGE_RESULT={_json.dumps(marker)}')
