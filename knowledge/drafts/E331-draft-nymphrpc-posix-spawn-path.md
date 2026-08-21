# E331 知识草稿：OHOS 下 python subprocess 裸名命令不搜索 PATH

> 编号：E331（草稿，待 graph promote 转正式；E321–E330 已占用，按设备端最大 E 编号顺延）
> 文件名：E331-draft-nymphrpc-posix-spawn-path
> 实例来源：nymphrpc 0.1.1 OpenHarmony PC 适配 CI（pre-download 裸名 curl 失败）
> 检索字段：library=nymphrpc / build=make / error=Errno2 / toolchain=clang15 / platform=ohos

## 背景

HarmonyOS PC 的 python3 subprocess 以裸名（无路径）命令调用可执行文件时，即使该命令
存在于 PATH 中，也会抛 FileNotFoundError: [Errno 2] No such file or directory: 'curl'。

本次 nymphrpc 0.1.1 适配中，CI 脚本 ci/conan/build_and_test.sh 的 pre-download 阶段用
subprocess.run(['curl', '-sL', ...])（裸名 curl），在 OHOS 上连续报错
[Errno 2] No such file or directory: 'curl'，pre-download 失效（后降级为 conan 自身下载兜底）。

## 根因

python3 3.12.9，sys.platform='ohos'。subprocess.py：
- L78: _IS_HARMONYOS = sys.platform.startswith(('ohos','harmonyos'))
- L723: _use_posix_spawn() 内 if _IS_HARMONYOS: return True
- L1849-1853: 分支条件 (os.path.dirname(executable) or _IS_HARMONYOS)，裸名命令
  （dirname 为空）在 OHOS 上被强制进入 os.posix_spawn() 分支

关键点：os.posix_spawn() 是 posix_spawn（不做 PATH 搜索），不是 posix_spawnp，
因此裸名命令无法解析，直接 Errno 2。已排除"PATH 缺失"假设：PATH 存在且
shutil.which('curl') 可解析到 /usr/bin/curl。

## 复现（设备只读探针）

- 裸名: python3 -c "import subprocess; subprocess.run(['curl','--version'])" → FileNotFoundError Errno 2
- 绝对路径: subprocess.run(['/usr/bin/curl','--version']) → rc=0
- shell=True: subprocess.run('curl --version', shell=True) → rc=0
- shutil.which: shutil.which('curl') → /usr/bin/curl

## 修复/规避（工具链与脚本集成）

1. 绝对路径：subprocess.run(['/usr/bin/curl', ...])
2. shell=True：走 /bin/sh -c，shell 自己做 PATH 搜索
3. 先解析：subprocess.run([shutil.which('curl'), ...])
4. 测试兼容场景沿用 E055 的 skip-test（检测 subprocess._USE_POSIX_SPAWN）

## 验证

- 设备探针三组全部符合预期：裸名 Errno 2 / 绝对路径 rc=0 / shell=True rc=0。
- 真实触发证据：run_root ci-round-2f.log L82-102 pre-download 连续 [fail] Errno 2 'curl'。

## 关联条目

- E055（扩展基础）：posix_spawn 与 fork+exec 行为差异（Python 3.12+），视角为 CPython
  测试套件兼容（skip-test）；本稿为其工具链集成视角扩展，最终编号与是否并入 E055 由主编确认。
- P013：平台限制必须降级而非绕过（posix_spawn 属平台级行为差异，用绝对路径/shell/which 降级）。
