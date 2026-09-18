import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        cc = compilers.get("c") or "clang"
        src = os.path.join(self.source_folder, "test_kqwait.c")
        out = os.path.join(self.build_folder, "test_kqwait")
        self.run(
            f'"{cc}" -std=c99 -Wall -Wextra -O2 '
            f'-o "{out}" "{src}"'
        )

    def test(self):
        if not can_run(self):
            return
        # L0d: test() 必须有 self.run()；CI #15438: 二进制不在 PATH → 用完整路径
        dep = self.dependencies["kqwait"]
        bin_dir = dep.cpp_info.bindirs[0]
        kqwait = os.path.join(dep.package_folder, bin_dir, "kqwait")
        if not os.path.exists(kqwait):
            raise ConanException(f"kqwait binary not found at {kqwait}")

        helper = os.path.join(self.build_folder, "test_kqwait")
        if not os.path.exists(helper):
            raise ConanException(f"test helper not found at {helper}")

        tmp = os.path.join(self.build_folder, "kqwait_pkg_test")
        os.makedirs(tmp, exist_ok=True)

        # ── 消费者冒烟: --help / -v 退出码 0 ──
        self.run(f'"{kqwait}" -h', env="conanrun")
        self.run(f'"{kqwait}" -v', env="conanrun")

        # ── 消费者功能测试: 单文件写等待（上游 t/kqwait.pl 场景 1 核心）──
        # kqwait 后台等待 → 写文件 → 必须打印文件路径并退出 0
        watched = os.path.join(tmp, "watched.txt")
        with open(watched, "w") as f:
            f.write("init\n")
        cmd = (
            f'"{helper}" append "{watched}" & H=$!; '
            f'timeout 10 "{kqwait}" "{watched}" > "{tmp}/out1.txt" 2> "{tmp}/err1.txt"; '
            f'R=$?; wait $H; HR=$?; '
            f'echo "RC=$R HELPER_RC=$HR" > "{tmp}/rc1.txt"; exit 0'
        )
        self.run(cmd, shell=True)
        with open(os.path.join(tmp, "rc1.txt")) as f:
            rc = f.read().strip()
        with open(os.path.join(tmp, "out1.txt")) as f:
            out = f.read().strip()
        with open(os.path.join(tmp, "err1.txt")) as f:
            err = f.read()
        if rc != "RC=0 HELPER_RC=0":
            raise ConanException(f"kqwait did not exit 0 on file write: {rc} (stderr: {err.strip()[:200]})")
        if out != watched:
            raise ConanException(f"kqwait printed {out!r}, expected the watched path {watched!r}")
        if err:
            raise ConanException(f"kqwait wrote to stderr on the happy path: {err[:200]}")

        # ── OHOS 专项: 目录内删除事件 → dirinfo diff(上游 t/kqwait.pl 场景 4)──
        # 验证 inotify IN_DELETE 映射走 dirinfo-diff 分支(非 IN_DELETE_SELF 短路)
        # 测试隔离: 每场景重建干净目录。touch 已存在文件只发 IN_ATTRIB
        # (kqueue NOTE_WRITE 也不含 utimens → 上游同样不触发),状态污染会造成假超时
        d = os.path.join(tmp, "dir")
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        victim = os.path.join(d, "victim.txt")
        with open(victim, "w") as f:
            f.write("x\n")
        cmd = (
            f'"{helper}" delete "{victim}" & H=$!; '
            f'timeout 10 "{kqwait}" "{d}/" > "{tmp}/out2.txt" 2> "{tmp}/err2.txt"; '
            f'R=$?; wait $H; HR=$?; '
            f'echo "RC=$R HELPER_RC=$HR" > "{tmp}/rc2.txt"; exit 0'
        )
        self.run(cmd, shell=True)
        with open(os.path.join(tmp, "rc2.txt")) as f:
            rc2 = f.read().strip()
        with open(os.path.join(tmp, "out2.txt")) as f:
            out2 = f.read().strip()
        expected2 = f"- {victim}"
        if rc2 != "RC=0 HELPER_RC=0":
            raise ConanException(f"kqwait dir-delete test exit {rc2}, expected 0")
        if out2 != expected2:
            raise ConanException(f"kqwait dir-delete printed {out2!r}, expected {expected2!r}")

        # ── OHOS 专项: 目录内新建事件 → "+ path/name"（场景 3）──
        # 测试隔离: 同上,清掉场景 4 残留的 victim.txt,保证 created.txt 是真新建(IN_CREATE)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        created = os.path.join(d, "created.txt")
        cmd = (
            f'"{helper}" create "{created}" & H=$!; '
            f'timeout 10 "{kqwait}" "{d}/" > "{tmp}/out3.txt" 2> "{tmp}/err3.txt"; '
            f'R=$?; wait $H; HR=$?; '
            f'echo "RC=$R HELPER_RC=$HR" > "{tmp}/rc3.txt"; exit 0'
        )
        self.run(cmd, shell=True)
        with open(os.path.join(tmp, "rc3.txt")) as f:
            rc3 = f.read().strip()
        with open(os.path.join(tmp, "out3.txt")) as f:
            out3 = f.read().strip()
        if rc3 != "RC=0 HELPER_RC=0" or out3 != f"+ {created}":
            raise ConanException(f"kqwait dir-create: rc={rc3} out={out3!r}, expected '+ {created}'")

        self.output.info("kqwait test_package: all functional tests PASSED "
                         "(file write / dir delete diff / dir create diff)")
