import os
from conan import ConanFile
from conan.errors import ConanException  # aireview Critical: 行38 用 ConanException 需导入避 NameError
from conan.tools.build import can_run

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # aireview P2: 增实际 inotify 功能验证非仅 --help（避 --help 过但 inotify 实际不工作）
            # 用 inotifywait 监听临时文件 create 事件验证 inotify 内核接口可用
            # CI #15438: 裸 inotifywait 不在 PATH（exec: No such file or directory, ret=127）
            # → 用 conanrun 环境里的完整二进制路径（bindirs），fallback --help 冒烟同改
            bin_dir = self.dependencies["inotify-tools"].cpp_info.bindirs[0]
            inotifywait = os.path.join(self.dependencies["inotify-tools"].package_folder, bin_dir, "inotifywait")
            inotifywatch = os.path.join(self.dependencies["inotify-tools"].package_folder, bin_dir, "inotifywatch")
            if not os.path.exists(inotifywait):
                raise ConanException(f"inotifywait binary not found at {inotifywait}")
            tmpdir = os.path.join(self.build_folder, "inotify_test")
            os.makedirs(tmpdir, exist_ok=True)
            # aireview P1: shell 命令 rm -f 掩盖 wait 退出码 → 改 RET=$?; exit $RET 避空壳测试
            watch_cmd = (
                f'timeout 10 "{inotifywait}" -e create -q "{tmpdir}" & '
                f'WATCH_PID=$!; '
                f'sleep 1; touch "{tmpdir}/trigger.txt"; '
                f'wait $WATCH_PID; RET=$?; '
                f'rm -f "{tmpdir}/trigger.txt"; '
                f'exit $RET'
            )
            ret = self.run(watch_cmd, env="conanrun", shell=True, ignore_errors=True)
            if ret != 0:
                # aireview Medium: 功能测试失败静默降级永真冒烟违 R9（禁止伪造通过）
                # 改 raise ConanException 让测试失败，CI 门禁能暴露回归
                # 仅在已知 inotify 不可用的 CI 环境变量标记下才走降级路径
                ci_skip = os.environ.get("CI_SKIP_INOTIFY_FUNCTIONAL", "")
                if ci_skip:
                    self.output.warning(f"inotify functional test skipped (CI_SKIP_INOTIFY_FUNCTIONAL={ci_skip}), falling back to --help smoke")
                    self.run(f'"{inotifywait}" --help', env="conanrun")
                    self.run(f'"{inotifywatch}" --help', env="conanrun")
                else:
                    raise ConanException(f"inotify functional test failed (ret={ret}): inotify kernel API unavailable, not silently degrading (R9)")
            else:
                self.output.info("inotify functional test PASSED (create event detected)")
