import os

from conan import ConanFile


class AlmanahTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # VirtualRunEnv：conanrun.sh 聚合全部依赖运行期环境（LD_LIBRARY_PATH
    # 等）——手工聚合 libdirs 会漏库（探索期实证 exit 126），标准通道稳健
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 纯 libc 消费者测试：不耦合依赖头文件（沙箱内 include 目录发现
        # 不稳定，探索期实证）；真实执行链放在 test() 运行包内二进制。
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        src = os.path.join(self.source_folder, "test_almanah_vfs.c")
        exe = os.path.join(self.build_folder, "test_almanah_vfs")
        self.run(f"{cc} {src} -o {exe}")

    def test(self):
        import shutil
        dep = self.dependencies["almanah"]
        exe_src = os.path.join(dep.cpp_info.bindirs[0], "almanah")
        # 包缓存文件的属主/组在 FUSE 上与进程 uid 错位（mode 770 无执行权
        # 且 chmod 被忽略，E046 同源陷阱）——按 fuse-tmp-write-guard SKILL
        # 策略：umask 000 重新创建副本（777 不依赖属主位），字节内容与包内
        # 产物一致，消费者测试语义不变。
        exe_run = os.path.join(self.build_folder, "almanah.run")
        # FUSE：残留副本属主错位（770/他属主）时覆盖写与删除都可能被拒
        # （E046 同源）——先尝试删残留；删不掉则换唯一文件名兜底。
        try:
            if os.path.exists(exe_run):
                os.remove(exe_run)
        except OSError:
            exe_run = f"{exe_run}.{os.getpid()}"
        old = os.umask(0o000)
        try:
            shutil.copyfile(exe_src, exe_run)
            os.chmod(exe_run, 0o755)
        finally:
            os.umask(old)
        # env="conanrun"：经 conanrun.sh 注入全部依赖运行期环境
        self.run(f'ALMANAH_BIN="{exe_run}" '
                 f'"{os.path.join(self.build_folder, "test_almanah_vfs")}"',
                 env="conanrun")
