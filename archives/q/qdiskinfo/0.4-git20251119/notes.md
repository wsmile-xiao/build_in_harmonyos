# qdiskinfo 0.4-git20251119 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt + Qt6 AUTOMOC/AUTOUIC/AUTORCC）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built（W3 本地 CI 通过后由 finish 写入，待 CI 发布后转 published）

## 源码身份
- 上游: https://github.com/edisionnano/QDiskInfo
- 版本语义: tag `0.4`（2025-05-29）+ main 分支快照
- commit: `c4b0ba8da96c90caaa4e8471fcc5ab49416f221c`（最后一次推送 2025-11-19T23:16:10Z）
- tarball: https://github.com/edisionnano/QDiskInfo/archive/c4b0ba8da96c90caaa4e8471fcc5ab49416f221c.tar.gz
- sha256: `bce362a54ad3a5de161e7ebce73e6cbe47fc87bbbb45e13505b91a41d6e7acd2`

## 编译步骤

```bash
# 1) 依赖预检（制品仓）
conan list "qtbase/6.11.1.3:*" -r=ohpcd          # 命中
conan list "smartmontools/7.4:*" -r=ohpcd        # 命中（OHOS 预编译二进制，提供 smartctl）

# 2) 本地闭环
conan create archives/q/qdiskinfo/0.4-git20251119 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方要点：

| 项 | 取值 | 原因 |
|----|------|------|
| `QT_VERSION_MAJOR` | `6` | qtbase 6.11.1.3 |
| `ENABLE_TRANSLATIONS` | `OFF` | qtbase 包不含 Qt6LinguistTools（OHOS 无 lupdate/lrelease）；上游官方 AppImage 构建同样未开启 |
| `CMAKE_PREFIX_PATH` | qtbase 包目录（`Environment` → build 作用域脚本） | qtbase 以 `cmake_find_mode=none` 导出，CMakeDeps 不生成 Qt6 target |
| `requires("smartmontools/7.4")` | 运行期依赖 | 上游 AppImage 把 smartctl 随应用分发；声明后 smartctl 进入运行环境 PATH，`getSmartctlPath()` 直接命中 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机启动后设备列表为空，无任何报错 | 上游在 4 处特权路径固定 `QProcess::start("pkexec", args)`；HarmonyOS PC 无 polkit/pkexec，进程启动失败且 `exitCode()==0`/`isOpen()==false`，`getSmartctlOutput()` 只返回空字符串 → 静默失败 | 补丁 0001/0004：`findExecutable()` + `getPrivilegeElevator()` + `Utils.startProcess()`；pkexec 存在则保持上游提权语义，不存在则直接执行；smartctl 缺失时给出明确错误对话框 |
| 2 | 上游无 `--version`/`--help`，CI L2 冒烟无命令可跑 | 上游只实现 `--ascii-view` | 补丁 0002：在构造 `QApplication` 之前新增两个无 GUI 早期退出分支（不依赖显示服务器）。先例：acorn-fdisk、abx |
| 2b | CI L2 仍报 `--version/--help failed`（非阻塞 warn，与 ksnakeduel 等同为 Qt 应用） | CI 直接执行 `bin/QDiskInfo`，未注入 Conan 运行环境；安装期 RPATH 已被 `cmake --install` 去除，动态链接器找不到 `libQt6Widgets.so.6` → 退出码 127 | 属 CI 采样子集（L2 仅用裸环境）的预期现象：test_package 在 `conanrun` 环境下断言 `--version`/`--help` 返回 0 并通过；不向制品烘入发布机绝对 RPATH（红线） |
| 3 | `cmake create` 通过但真机执行 package 内二进制报 `Operation not permitted`（rc=126），而构建树内同一二进制可直接执行 | `cmake --install` 为去掉构建期 RPATH 而**重写** ELF（"Set non-toolchain portion of runtime path ... to ''"），使链接器写入的 `.codesign` 段失效；OHOS 内核只加载带有效签名段的 ELF | 在 `package()` 的 `cmake.install()` 之后按 E077 四步重新自签名：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → 恢复 `+x` 位 |
| 4 | test_package 提权回退场景断言失败（桩 smartctl 日志为空） | `conan.tools.files.chmod` 在 Conan ≥2.15 的签名变为 `chmod(self, path, read/write/execute)`；旧式 `chmod(self, stub, 0o755)` 把 `0o755` 当作 `read` 参数，桩脚本没有执行位 → `findExecutable()` 跳过它、改用 PATH 后面的真 smartctl | 改用 `chmod(self, stub, execute=True)` |
| 5 | offscreen GUI 测试报 `Fontconfig error: Cannot load default config file` | 容器/最小环境无 fontconfig 配置 | 非致命告警，Qt 继续使用内置回退字体；断言只要求进程不崩溃 |
| 6 | `make: jobserver mkfifo: ... Operation not permitted` | HMDFS 上无法创建 FIFO（toybox/内核限制） | 非致命告警，Make 退化为串行/无 jobserver 模式，编译正常完成 |
| 7 | G0 干净构建验证 `configure 失败 (exit 127)`（非阻塞） | `clean_verify` 的 G0 只支持 autotools 流程，固定执行 `bash ./configure`；CMake 工程没有该脚本 | 属工具链已知限制（非阻塞），真实构建由 G2 `conan create` 与 W3 本地 CI 全量覆盖并通过 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | `include/utils.h` | 增加 `#include <QProcess>` 与 4 个声明：`findExecutable` / `getSmartctlPath` / `getPrivilegeElevator` / `startProcess` |
| 0002 | `src/main.cpp` | 新增 `--version`、`--help`/`-h` 早期退出分支（在 `QApplication` 构造之前） |
| 0003 | `src/mainwindow.cpp` | `--ascii-view` 改走 `Utils.startProcess()`；关于对话框平台描述由 "for Linux" 改为通用表述 |
| 0004 | `src/utils.cpp` | 提权器运行时探测与降级执行；smartctl 缺失时提前返回并报错；`initiateSelfTest`/`cancelSelfTest` 改用 `startProcess()` |

未打补丁但已核实：`src/asciiview.cpp` 的 `#include <scsi/sg.h>` + `SG_IO` ioctl 在 OHOS SDK
自带（`native/sysroot/usr/include/scsi/sg.h`，含 `sg_io_hdr_t`、`SG_IO 0x2285`），无需适配。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| qtbase | 6.11.1.3 | 编译依赖 | Qt6 Core/Gui/Widgets + platforms 插件 |
| smartmontools | 7.4 | 运行依赖 | 提供 `smartctl`（制品仓 OHOS 预编译二进制） |

## 验证结果

```bash
$ conan create archives/q/qdiskinfo/0.4-git20251119 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
[PASS] 打包二进制存在: .../p/bin/QDiskInfo
[PASS] 打包二进制可执行
[PASS] --version 退出码 0 且输出版本号 (rc=0, out=QDiskInfo 0.4)
[PASS] --help 退出码 0 且输出用法 (rc=0)
[PASS] 非 root: --ascii-view 以 'requires root privileges' 退出 (rc=1)
[PASS] offscreen QPA 下进程成功启动（Qt 平台插件加载）
[PASS] offscreen 主窗口构造后未崩溃 (timeout=1 rc=9)
RESULT: 7/7 checks passed
qdiskinfo/0.4-git20251119 (test package): 桩 smartctl 调用记录:
--scan --json
-x --json=o /dev/qdiskinfo-test
qdiskinfo/0.4-git20251119 (test package): 提权回退场景通过：--scan 与 -x 调用均被直接执行
```

真机事实核验（本机即 HarmonyOS PC，aarch64）：

```text
$ command -v pkexec          # 无输出 → 确认无 polkit/pkexec（补丁 0004 的必要性）
$ smartctl --scan            # /dev/nvme0 -d nvme
$ smartctl -x --json=o /dev/nvme0   # 返回合法 JSON（rc=2），非 root（uid 20020084）可读
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/QDiskInfo` | 391872 B | Qt6 GUI 主程序（已 OHOS 自签名） |
| `share/applications/QDiskInfo.desktop` | — | 桌面入口 |
| `share/icons/hicolor/scalable/apps/QDiskInfo.svg` | — | 应用图标 |

## 注意事项

- `package()` 中的签名步骤必须在 `cmake.install()` **之后**执行：任何后续 ELF 改写（RPATH、strip）都会使签名失效。
- 无 polkit/pkexec 时读取 S.M.A.R.T. 依赖调用方权限（或设备节点本身可读，例如本机 NVMe 非 root 可读）；这是平台限制，补丁只保证不再静默失败，并给出明确错误。
- 界面翻译资源未编译进包（见上文 `ENABLE_TRANSLATIONS`），界面为英文。
---

**编译结束**: 2026-09-29 22:09
**最终状态**: built
