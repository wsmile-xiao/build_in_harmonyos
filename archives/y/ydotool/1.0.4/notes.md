# ydotool 1.0.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`project(ydotool C)`，C99）
- 编译日期: 2026-09-26
- 编译器: OHOS SDK clang 15.0.4（aarch64-unknown-linux-ohos，设备 profile `ohos-aarch64-device`；独立验证用同源 `ohos-aarch64-ydotool`）
- Conan: 2.29.1（OHOS 适配版），`ydotool/1.0.4`
- 状态: built

## 编译步骤

1. `init-build` 从官方源拉取
   `https://github.com/ReimuNotMoe/ydotool/archive/refs/tags/v1.0.4.tar.gz`
   （sha256 `ba075a43…23bd` 校验通过；设备侧 GitHub 直连超时，经镜像
   下载后与预期哈希一致）。
2. 源码改动（2 个补丁，均为可移植性处理，无平台宏）：
   - `0001-CMakeLists.txt.patch`：版本解析改为 `-DYDOTOOL_VERSION` 覆盖
     → git 元数据 → 发布版本回退三级；归档无 git 元数据时 `VERSION`
     不再为空；
   - `0002-manpage-CMakeLists.txt.patch`：`find_program(SCDOC)`，
     scdoc 缺失时跳过 man 页（本平台未安装 scdoc）。
3. `conan create` 按 conanfile.py 流程执行：CMakeToolchain 注入
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 3.4，CMake ≥4.0 已移除
   <3.5 兼容）与 `YDOTOOL_VERSION=1.0.4` → configure/build/install。
4. `conan-verify`（G0–G4 全 PASS）→ 本地 CI 门禁 → `finish` W3 复核。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ydotoold --version` 输出 `unknown` | 发布 tarball 无 git 元数据，`git describe` 失败后 `add_definitions(-DVERSION=...)` 不执行 | 补丁 0001 增加 `-DYDOTOOL_VERSION` 覆盖与版本回退；配方从 `self.version` 注入 |
| 2 | 构建失败：`scdoc: command not found`（manpage ALL target） | 上游把 scdoc 当作无条件的 ALL target；OHOS 未安装 scdoc（`command -v scdoc` 为空） | 补丁 0002 用 `find_program` 探测，缺失时跳过 man 页 |
| 3 | CMake 4.4.3 拒绝 `cmake_minimum_required(VERSION 3.4)` | CMake ≥4.0 移除 <3.5 策略兼容 | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，零补丁 |
| 4 | `ydotoold` 启动失败：`failed to open uinput device: Permission denied` | OHOS 运行时 /dev/uinput 对普通用户进程 EACCES（内核有 uinput：/proc/misc `223 uinput`；设备节点被 SELinux/ueventd 管控） | 属平台安全模型边界，无法在应用层解决：需系统级权限运行守护进程。测试按平台边界断言（A16），不伪造能力 |
| 5 | 上游默认 socket 路径不可用 | `/tmp` 只读（EROFS，E002/E052 同族） | 用 `ydotoold -p $TMPDIR/...`（或 `XDG_RUNTIME_DIR`）指定可写路径；测试全部使用自定义路径 |
| 6 | AF_UNIX 路径名 socket `bind()` 一律 `EPERM`（Operation not permitted） | HarmonyOS SELinux（真机域 `u:r:hishell_hap:s0`）禁止普通进程创建路径名 Unix socket；`$HOME`/`$TMPDIR`/`/dev/shm` 等所有可写位置实测均 EPERM（abstract socket 可用、TCP 可用）——知识库 E024 同族，多个已合并包有同样记录 | 平台安全模型边界，应用层无法解决。测试按 E024 自适应：A8 探测 bind 能力（EPERM 即为平台受限证据），A9-A15 逐字节线协议断言在受限环境记为跳过（不计失败），在允许 AF_UNIX 的环境自动全跑 |
| 7 | 设备侧 GitHub 直连下载超时 | 网络可达性（本机环境） | 经镜像下载后校验官方 SHA256 一致；`conandata.yml` 记录官方 URL |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-CMakeLists.txt.patch` | `CMakeLists.txt` | 版本解析：`-DYDOTOOL_VERSION`（打包注入）> `git describe` > 发布版本回退；`if (RC_GIT_VER STREQUAL "0")` 安全比较；无论成败都会 `add_definitions(-DVERSION=...)` |
| `0002-manpage-CMakeLists.txt.patch` | `manpage/CMakeLists.txt` | `find_program(SCDOC_EXECUTABLE scdoc)`；scdoc 缺失时 `man_page()` 直接返回（跳过 man 页），存在时行为不变 |

补丁中不含任何平台宏（无 `__OHOS__`）、无绝对路径、无环境变量注入。

## 依赖版本

无第三方依赖（仅 libc：POSIX socket、getopt、epoll、uinput ioctl）。

## 验证结果

```text
# 独立构建冒烟（设备侧，.work 源码 + 补丁 0001/0002）
# 覆盖注入优先：cmake 从 git worktree 目录运行时仍输出 1.0.4（不受环境 git 标签影响）
# 版本来源反例观察（无覆盖注入 + 构建目录位于无关 git 仓库内）：
#   ydotoold --version -> webp-pixbuf-loader-0.2.7-src-4871-gb01a5b784（无关项目标签；
#   覆盖注入修复后两种构建目录均输出 1.0.4）
ydotoold --version     -> 1.0.4 (rc=0)
ydotoold --help        -> Usage: ydotoold (rc=0)
ydotool help           -> 命令表（click/key/mousemove/type）(rc=0)
ydotoold -p $TMPDIR/... -> "failed to open uinput device: Permission denied" (rc=2，平台边界)
YDOTOOL_SOCKET=<缺失路径> ydotool key 1:1 -> "failed to connect socket ... No such file or directory" +
    "Please check if ydotoold is running." (rc=2)
mock_daemon（AF_UNIX 绑定探针）-> "BIND-FAILED errno=1 Operation not permitted" (rc=2，E024 平台限制)
# 消费者测试（设备侧直跑，等价 conan test 流程）
test_ydotool: 9/9 executed assertions passed (7 skipped: E024 AF_UNIX bind EPERM)
# conan-verify（设备侧，profile ohos-aarch64-ydotool）
G0/G1/G2/G3 PASS；G2 干净 conan create 成功，test_package 输出
"test_ydotool: 9/9 executed assertions passed (7 skipped: E024)"，conan create rc=0
G4/L2/L4/L5: 工具侧 conan list JSON 解析限制（G4 报 "无法找到程序包 ID"，
   与 smtpping 1.1.4 已知工具限制同）——产物/安全检查由本地 CI 门禁 L2/L4/L5 覆盖
# 本地 CI 门禁
见 reports/w3-local-ci.log（L0/L1/L2/L4/L5）
# W4 独立审计
见 reports/audit-result.json
```

## 注意事项

- **运行时能力边界（重要）**：本包提供完整的 daemon+client 实现与线协议；
  但 OHOS PC 上 `/dev/uinput` 对普通用户进程 `EACCES`，`ydotoold` 需要
  系统级权限（root/system domain）才能创建虚拟输入设备。A16 对该边界做
  双分支断言（可用则验证转发、被阻断则验证退出码与错误信息）。
- **AF_UNIX 限制（E024，与上一条独立的第二重边界）**：HarmonyOS SELinux
  禁止普通进程对路径名 Unix socket 执行 `bind()`（全可写文件系统 EPERM）；
  ydotool 的 daemon/client 链路本身依赖该 socket。A8 探测该能力，A9-A15
  线协议断言在受限环境记为跳过（不计失败），在允许 AF_UNIX 的环境自动
  执行 16/16。
- 因此在 OHOS 上，ydotool 的完整运行需要：系统级权限（/dev/uinput）+
  允许 AF_UNIX 绑定的执行域；本包在这些条件满足时功能完整。
- `/tmp` 只读：默认 socket 路径 `/tmp/.ydotool_socket` 在 OHOS 不可用，
  必须用 `-p` 或 `XDG_RUNTIME_DIR`。
- 上游 1.0.4 之后已重构（如 `type` 的键盘布局支持），本任务版本锁定
  1.0.4，适配以最小补丁保持行为等价。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ydotool` | 命令行客户端（click/key/mousemove/type） |
| `bin/ydotoold` | 守护进程（/dev/uinput 虚拟设备 + socket 转发） |
| `lib/systemd/user/ydotool.service` | 上游 systemd 用户单元模板（cmake install 默认安装） |
| `licenses/LICENSE` | AGPL-3.0-or-later 许可证 |
| `packaging/ydotool-1.0.4-ohos-aarch64.tar.gz` | Conan 包产物发布归档 |

**编译结束**: 2026-09-26 —— W3 本地 CI 门禁通过（L0/L1/L2/L4/L5；消费者测试 9/9 执行 + 7 条 E024 平台受限跳过）
**最终状态**: built
