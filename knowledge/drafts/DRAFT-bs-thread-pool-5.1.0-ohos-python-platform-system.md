# DRAFT — OHOS 设备 Python 的 platform.system() 返回 "HarmonyOS"，上游按 OS 分支的 Python 自动检测脚本全部落空（bs-thread-pool 5.1.0）

**来源事件:** bshoshany-thread-pool 5.1.0 适配（执行端，2026-09-05）
**状态:** 草稿（待 promote 审核）
**对应 .kv:** `DRAFT-bs-thread-pool-5.1.0-ohos-python-platform-system.kv`

## 问题

在 OHOS 设备上原样运行上游自带 Python 构建/测试脚本 `scripts/compile_cpp.py`（bshoshany/thread-pool v5.1.0）时报：

```
Error: No compiler found!
```

设备上 `clang++` 明确在 PATH（`shutil.which("clang++")` 可命中）。定位到脚本编译器自动检测逻辑只处理
`platform.system()` 的三个返回值分支：`Windows`/`Linux`/`Darwin`（scripts/compile_cpp.py:342-365）。

实测 OHOS 设备全局 Python 3.12.8：

```python
>>> import platform
>>> platform.system()
'HarmonyOS'
```

返回值是 `"HarmonyOS"` 而非 `"Linux"`——任何按 `platform.system()` 分 Windows/Linux/Darwin
（或按 `sys.platform` 分 linux/darwin/win32）编写自动检测逻辑的上游 Python 构建、测试、安装脚本，
在 OHOS 设备单端构建场景都会落空到"无分支命中"路径：编译器探测、默认 flags、路径布局等全部不生效。

## 根因

OHOS 用户态虽是 musl/Linux 内核，但设备 Python 的 `platform.system()` 返回定制的
`"HarmonyOS"`（发行版定制），不等于任何上游脚本预期的标准值。上游脚本无法预知该平台，
自动检测静默失败，只报笼统错误（如 "No compiler found!"），第一眼容易误判为环境损坏。

## 方案（已验证）

优先用显式参数绕过自动检测，不改上游脚本：

```sh
python3 scripts/compile_cpp.py tests/BS_thread_pool_test.cpp --run -c clang++ -s c++17
```

`-c clang++` 直接指定编译器后脚本跳过 `platform.system()` 分支。同一模式适用于：
- `--compiler`/`-c` 类显式编译器参数；
- 上游脚本读取的环境变量开关（CC/CXX 等）；
- 都没有时才考虑最小补丁：在平台分支加入 `platform.system() in ("Linux", "HarmonyOS")` 判定
  （修改须以补丁形式进配方 patches/，记录依据）。

## 适用范围

所有在 OHOS 设备端运行、且按 OS 名做分支的上游 Python 脚本（构建助手、测试驱动、
代码生成器、打包脚本）。与 E211（musl 缺 pthread_*affinity_np，sched(0) 等价替换）
共同构成 OHOS 上跑 BS::thread_pool 类自带脚本项目的两个固定动作。

## 证据

- `python3 -c "import platform; print(platform.system())"` → `HarmonyOS`（OHOS PC aarch64，Python 3.12.8，/data/service/hnp/bin/python3）
- 失败命令与第一条错误：`python3 scripts/compile_cpp.py tests/BS_thread_pool_test.cpp --run --type=release --verbose` → `Error: No compiler found!`（无 -c 参数时）
- 成功命令：加 `-c clang++` 后 C++17/ C++20 header 路径全部编译运行（208/208 checks 通过）
