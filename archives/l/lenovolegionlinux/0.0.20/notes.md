# lenovolegionlinux 0.0.20 适配笔记

## 交付物与边界（先看这段）

上游由两半组成，OHOS PC 侧的可交付性完全不同：

| 上游部件 | 内容 | OHOS PC 侧结论 |
|---|---|---|
| `kernel_module/` | Linux 内核模块（Kbuild `obj-m += legion-laptop.o` + DKMS），全部硬件功能的实现 | **不可构建、不可加载**：无内核构建树，16 个内核内部头缺 11 个；非特权用户态沙箱无 `insmod` |
| `python/` | 用户态 CLI/GUI（`legion_cli` / `legion_gui`），读写内核模块暴露的 sysfs 接口 | **可交付**：纯 Python，本次交付 site-packages + `bin/legion_cli` |

因此本包交付：**用户态层制品 + 上游源码快照（原目录布局）+ fail-closed 契约测试**，
并在 PR/manifest 中分层声明「用户态已适配」「内核态未执行」，不把源码契约当作内核态通过。

## 编译环境

- **构建系统**: custom（用户态 setuptools 源码 + Kbuild 源码快照；无 C 编译发生）
- **编译日期**: 2026-09-20
- **目标平台**: aarch64-unknown-linux-ohos（OpenHarmony PC）
- **状态**: built（配方验证通过；内核模块未构建，见上表）
- **补丁数量**: 2（0001 argcomplete 可选化、0002 shell 可移植性）

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/lenovolegionlinux/0.0.20 --build=missing \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. `source()`：`get()` 从官方 tag 归档下载并 `strip_root`（sha256 见 conandata.yml）。
2. `build()`：
   - `apply_conandata_patches()` 应用补丁 0001、0002；
   - `python -m compileall` 对交付的用户态模块做**全量字节码编译**（逐文件 `Compiling ...`
     日志即编译证据；语法错误在此直接失败）；
   - 契约自检：补丁必须真正生效（`legion_cli.py` 中 `argcomplete = None` 存在），
     否则构建失败 —— 避免「补丁没打上、CLI 在 OHOS 上根本起不来」的静默失败。
3. `package()`：site-packages（`.py` + logo）、`bin/legion_cli|legion_gui`、
   `share/{applications,pixmaps,polkit-1/actions}`、`licenses/`、
   `share/lenovolegionlinux/upstream/{kernel_module,tests,python,README.md,LICENSE}`。
   `__pycache__` 统一清理：交付 `.py` 源码，避免与目标解释器版本耦合。

## 补丁 0001：argcomplete 由硬依赖降级为可选

上游 `python/setup.cfg` 的 `install_requires` 有四项：`PyQT6`、`PyYAML`、`argcomplete`、
`darkdetect`。其中：

| 依赖 | 制品仓状态 | 处置 |
|---|---|---|
| `PyYAML` | 有 `pyyaml/6.0.2` | 作为 `requires` 声明（上游 setup.cfg 同源） |
| `argcomplete` | **无** | 补丁 0001 降级为可选导入（`try/except ImportError` + 调用点守卫） |
| `PyQT6` | 无 | GUI 不可交付；`legion_gui` 入口随包安装但在无 PyQt6 环境不可启动，已如实声明 |
| `darkdetect` | 无 | 上游本就为可选导入（GUI 用），无需处理 |

`argcomplete` 只提供 shell 补全，不是功能依赖；硬依赖会让 `legion_cli` 在 OHOS PC 上
**完全无法启动**。上游对 `darkdetect` 已使用同一写法（"As darkdetect is not a system package,
make it work if it is not installed"），本补丁与该风格一致，且**不含任何平台宏**（R8）。

## 上游测试（12 个）的真实执行情况

上游没有 `make check`/`ctest`/`pytest` 目标，测试是 `tests/` 下 12 个 shell 脚本
（`ls tests/*.sh | wc -l` = 12）。逐条状态与实测证据见
`reports/upstream-test-evidence.md`，摘要：

| 用例 | 状态 | 说明 |
|---|---|---|
| `test_python_cli.sh` | **执行并通过** | 上游原始脚本对包内上游源码快照逐字执行 |
| `test_python_cli_installed.sh` | **执行并通过** | 上游脚本逐字副本，经 conanrun PATH 执行包内 `bin/legion_cli` |
| `test_kernel_build.sh` / `test_kernel_checkpath.sh` / `test_kernel_dkms_install.sh` / `test_kernel_install.sh` / `test_kernel_reload.sh` | 阻塞 | 需内核构建树 + root（/DKMS/checkpatch） |
| `test_python.sh` | 阻塞 | 需 pylint（制品仓无） |
| `test_python_gui.sh` / `test_python_gui_installed.sh` / `test_python_installed.sh` / `test_python_run_gui_root.sh` | 阻塞 | 需 xvfb + PyQt6 / pkexec 提权 |

**执行 2 / 阻塞 10，无失败（未执行的用例不声明通过）。**

## 已知限制

- 内核模块 `.ko` 不在交付范围内：OHOS aarch64 sysroot 无 `/lib/modules/*/build`、`usr/src`、
  `include/config`、`include/generated`，且 `legion-laptop.c` 的 16 个内核内部头仅 5 个存在
  （4 个是 `_UAPI_` 桩），缺 11 个（`linux/acpi.h`、`linux/hwmon.h`、`linux/platform_profile.h` 等）。
  源码快照随包交付，平台将来提供 OHOS 内核构建树/内核头制品时可直接复用。
- 硬件功能（风扇曲线、电源模式、电池养护、键盘灯、hybrid mode 等）需真实 Legion 机型
  （`DMI_SYS_VENDOR == "LENOVO"`）与已加载的内核模块，CI 中不可验证。
- GUI 需 PyQt6 与 X 服务器，两者在 OHOS 侧均不存在。

## CI 修复记录：测试阶段没有 bash（构建 #53594）

### 现象

CI 构建 #53594（worker CI-017）在 `test_package` 第一项失败：

```
lenovolegionlinux/0.0.20 (test package): RUN: "/data/service/hnp/bin/python3" ".../test_package/test_legion_api.py" "..."
[Errno 2] No such file or directory: 'bash'
Traceback (most recent call last):
  File ".../test_legion_api.py", line 97, in <module>
  File ".../test_legion_api.py", line 70, in main
ERROR: lenovolegionlinux/0.0.20 (test package): Error in test() method, line 68
        ConanException: Error 1 while executing
L1_RESULT=fail: conan create failed
```

### 根因（两层，都落在「测试环境里调不到 shell」这一点上）

1. **被测包侧**：上游 `legion.py` 用 `bash -c` 执行 dmesg / systemd 服务状态等可选探测，
   而 `CommandFeature._exec_cmd` 捕获异常后 **重新抛出**（`raise err`）。于是「bash 不存在」
   这一平台事实直接打断 `LegionModelFacade(expect_hwmon=False)` 的构造链
   （`PowerProfilesDeamonService` → `_does_service_exists` → `_exec_cmd`），
   CLI **崩溃而不是降级** —— 与本包「内核模块缺失时优雅降级」的声明相矛盾。
2. **测试环境侧**：OHOS worker 测试阶段的基础 PATH 不含平台工具目录
   （`/data/service/hnp/bin`；profile 的 `[buildenv]` 只在构建阶段注入），
   而本 `test_package` 用 `bash "…"` 调起上游快照脚本（`test_python_cli.sh` 依赖
   `BASH_SOURCE`），同样依赖 bash。

### 修复

| # | 位置 | 内容 |
|---|---|---|
| 1 | `patches/0002-legion-shell-portability.patch` | `legion.py` 增加 `SHELL = shutil.which('bash') or shutil.which('sh') or 'sh'`，两处 `Popen(['bash', '-c', cmd])` 改用 `SHELL`：交付给 OHOS PC 的 CLI 不再硬依赖 bash，探测退化为「特性不存在」。不含平台宏（R8） |
| 2 | `test_package/conanfile.py` | 启用 `VirtualBuildEnv`，`_test_env()` 把 `conanbuild` 与 `conanrun` 一并交给子进程 —— 测试环境与构建环境一致，bash 由 profile `[buildenv]` 提供 |
| 3 | `test_package/test_ohos_platform.sh` | 新增补丁 0002 的回归守卫（禁止再出现硬编码 bash；必须存在可移植 SHELL 选择） |

### 本地验证证据

- `conan create`（OHOS 交叉 profile + 模拟 profile `[buildenv]`）：**exit 0**，五组测试全绿
  （含新增守卫 `[ohos][ ok ] shell selection portable, no hard bash dependency`）；
- 同一份 `legion.py` 在「PATH 无 bash」环境（只提供 POSIX `sh`）下对照：
  - 未打补丁 → `FileNotFoundError: [Errno 2] No such file or directory: 'bash'`（与 CI #53594 一致，exit 1）；
  - 打补丁后 → exit 0，`OK: legion_linux consumer API checks passed (...)`；
- `VirtualBuildEnv` 生效证据：`test_package/conanbuildenv-release-armv8.sh` 导出
  `PATH="<profile [buildenv] 工具目录>:$PATH"` 与 `SHELL`/`CONFIG_SHELL`。
