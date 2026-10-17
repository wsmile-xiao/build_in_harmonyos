import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class LibcTestConan(ConanFile):
    """test_package for LLVM libc — 用包内 libc.a/crt 真实编译链接并运行 C 程序。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resource_dir(self, clang):
        try:
            out = subprocess.check_output([clang, "-print-resource-dir"], stderr=subprocess.DEVNULL)
            return out.decode("utf-8", "replace").strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    def test(self):
        pkg = self.dependencies["libc"].package_folder
        clang = "/data/service/hnp/bin/clang"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # —— 定位包内产物（package() 布局：include/ lib/libc.a startup/crt1.o）——
        libc_a = glob.glob(os.path.join(pkg, "lib", "libc.a"))
        crt = glob.glob(os.path.join(pkg, "startup", "**", "crt1*.o"), recursive=True)
        if not crt:
            crt = glob.glob(os.path.join(pkg, "lib", "**", "crt1*.o"), recursive=True)
        inc = os.path.join(pkg, "include")
        builtins_a = glob.glob(os.path.join(pkg, "lib", "libclang_rt.builtins-aarch64.a"))
        scudo_a = glob.glob(os.path.join(pkg, "lib", "libclang_rt.scudo_standalone-aarch64.a"))
        if not libc_a or not crt or not os.path.isdir(inc) or not builtins_a or not scudo_a:
            raise ConanException(
                "libc 包内产物不完整（需 include/ + lib/libc.a + startup/crt1*.o + builtins + scudo），无法做消费验证"
            )

        resource_dir = self._resource_dir(clang)
        q = shlex.quote
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libc_probe")

        # 消费命令（实测打通）：
        #   clang -nostdinc -nostdlib app.c -I libc/include \
        #     -I $(clang -print-resource-dir)/include startup/linux/crt1.o lib/libc.a \
        #     lib/libclang_rt.builtins-aarch64.a lib/libclang_rt.scudo_standalone-aarch64.a
        # -nostdinc 排除系统头，-nostdlib 排除系统 libc；builtins 提供 TLS（__emutls_get_address），
        # scudo 提供 malloc/free。
        args = [
            q(clang), q(src), "-o", q(out),
            "-nostdinc", "-nostdlib",
            "-isystem", q(inc),
        ]
        if resource_dir:
            args += ["-isystem", q(os.path.join(resource_dir, "include"))]
        args += [q(crt[0]), q(libc_a[0]), q(builtins_a[0]), q(scudo_a[0])]

        # OHOS 要求可执行文件代码签名，否则 Operation not permitted（E077）。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        sign = '{} --remove-section .codesign {} 2>/dev/null; {} sign -inFile {} -outFile {} -selfSign 1 >/dev/null 2>&1'.format(
            objcopy, q(out), signer, q(out), q(out)
        )
        cmd = " ".join(args + ["&&", sign, "&&", q(out)])
        # R34 反空壳：test.c 真实调用 strlen/memcmp/memcpy，运行返回码区分断言。
        self.run("{} -c {}".format(q(bash), q(cmd)), env="conanrun")
