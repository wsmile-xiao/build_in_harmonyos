import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        import os
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.host.items():
            pf = _d.package_folder or ""
            for p in list(_d.cpp_info.includedirs):
                ap = p if os.path.isabs(p) else os.path.join(pf, p)
                if ap and os.path.isdir(ap):
                    incs.append(ap)
            for d in list(_d.cpp_info.libdirs):
                ad = d if os.path.isabs(d) else os.path.join(pf, d)
                if ad and os.path.isdir(ad):
                    libdirs.append(ad)

        seen, uniq_i = set(), []
        for p in incs:
            flag = "-I" + p
            if flag not in seen:
                seen.add(flag)
                uniq_i.append(flag)
        inc = " ".join(uniq_i)

        seen_ld, uniq_ld = set(), []
        for d in libdirs:
            if d and d not in seen_ld:
                seen_ld.add(d)
                uniq_ld.append(d)
        ld = " ".join(f"-L{d}" for d in uniq_ld)

        so = None
        for d in uniq_ld:
            cand = os.path.join(d, "libgdal.so")
            if os.path.isfile(cand):
                so = cand
                break
        if not so:
            so = "libgdal.so"

        # Prefer shared gdal only; transitive statics already inside .so when linked at package time.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        cmd = (
            f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' "
            f"{ld} -lgdal -ldl -lm -lpthread"
        )
        # OHOS hmmac: conan_run 用 stdout=sys.stderr 时，若被调用方以 PIPE 捕获 stderr，
        # 子进程 stdout 绑定 TextIOWrapper(PIPE) 会导致 clang（toybox sh exec -a 包装脚本）
        # 静默失败（exit 1 无输出）。这里用 subprocess 直接执行，stdout/stderr 走 PIPE，
        # 规避该交互问题；实质编译/链接 test.c 与 libgdal.so 不变（满足 R34）。
        import subprocess
        proc = subprocess.run(
            cmd, shell=True, cwd=os.getcwd(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if proc.returncode != 0:
            self.output.error("test_probe clang stderr: " + (proc.stderr or "")[-500:])
            raise ConanException(
                "test_probe build failed (rc={}) while running: {}".format(
                    proc.returncode, cmd
                )
            )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
