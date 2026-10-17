# qbootctl 0.2.2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-13
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- sysroot: OHOS SDK 26.0.0.18 (native/sysroot)
- 状态: built

## 编译步骤（仓库外探针 + 正式交叉编译）

1. 下载官方 tag tarball 并校验 SHA256：
   ```bash
   curl -fsSL -o qbootctl-0.2.2.tar.gz https://github.com/linux-msm/qbootctl/archive/refs/tags/0.2.2.tar.gz
   sha256sum qbootctl-0.2.2.tar.gz
   # e66b361f86fac413f6a96974b4045a1fbc385f9eb6cee7fa8a26e0ca77c74a51
   ```
2. 仓库外 compile-only 探针（5/5 通过，无头文件缺失）：
   ```bash
   aarch64-unknown-linux-ohos-clang --target=aarch64-unknown-linux-ohos \
     --sysroot=$SYSROOT -std=gnu11 -I. -c qbootctl.c bootctrl_impl.c gpt-utils.c ufs-bsg.c crc32.c
   ```
3. Meson 交叉构建（exit 0）：
   ```bash
   meson setup build-ohos --cross-file cross3.ini \
     -Dc_args="--sysroot=$SYSROOT --target=aarch64-unknown-linux-ohos" \
     -Dc_link_args="--sysroot=$SYSROOT --target=aarch64-unknown-linux-ohos"
   meson compile -C build-ohos
   # 产物: build-ohos/qbootctl — ELF shared object, 64-bit LSB arm64
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 只读 (E002) | 鸿蒙环境 /tmp 为只读 | 使用 ~/tmp 或 $TMPDIR |
| 2 | Meson cross-file 解析失败 | cross-file 字符串需单引号 | 全部值使用单引号 |
| 3 | Ninja 权限拒绝 | ~/usr/local/bin/ninja 权限受限 | 使用 /data/service/hnp/bin/ninja (1.13.1) |
| 4 | 非 root 下任何命令被 euid 检查拦截 | 上游 main() 首先要求 root | 生产构建保持上游语义；测试专用构建（QBOOTCTL_TESTING）用 mock 后端无需 root |
| 5 | 无设备环境无法测试槽位逻辑 | 真实 backend 依赖 UFS/GPT 设备 | meson 增加独立测试目标 qbootctl-test（-DQBOOTCTL_TESTING），仅测试构建启用纯内存 mock |
| 6 | 上游 README 声称依赖 zlib-dev | 实际源码自实现 CRC32，不链接 zlib | 无 zlib 依赖（README 过时声明） |
| 7 | CI Meson configure: Unknown linker(s): [['llvm-ar']] | MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，CI PATH 无 llvm-ar 时按裸名探测失败 | conanfile.py generate() 新增 _inject_meson_archiver()：从 compiler_executables 取 ar、未提供时从 c 编译器同目录推导 llvm-ar/llvm-ranlib、isfile 校验、缺失抛 ConanException，经 tc.ar / tc.binaries["ranlib"] 在 tc.generate() 前注入绝对路径（参照 opus/dav1d 已验证模式） |

## 源码修改

补丁：`patches/0001-meson.build.patch` + `patches/0002-qbootctl.c.patch`
- `qbootctl.c`：mock backend 整体包入 `#ifdef QBOOTCTL_TESTING`；生产构建不定义宏，不含任何 mock 代码、无运行时开关（无 getenv），main() 与上游完全一致（geteuid 检查最先，-h/--help 非 root 同样被拒）。
- 测试专用构建（`-DQBOOTCTL_TESTING`）在 main() 中直接 `impl = &mock_bootctl`（编译期绑定，无环境变量开关），并跳过 root 检查；mock 状态跨进程镜像到当前目录普通文件 `.qbootctl-mock.state`（仅测试专用构建，生产二进制无此代码）。
- `meson.build`：新增独立可执行目标 `qbootctl-test`（c_args: `-DQBOOTCTL_TESTING`，`install: false`），生产目标 `qbootctl` 不定义宏、`install: true`。
- `conanfile.py`：`generate()` 用 `MesonToolchain` 并调用 `_inject_meson_archiver()`——从 `tools.build:compiler_executables` 取 ar/ranlib，未提供时从 c 编译器绝对路径同目录推导 `llvm-ar`/`llvm-ranlib`，`os.path.isfile` 校验缺失即抛 `ConanException`，经 `tc.ar`/`tc.binaries["ranlib"]` 在 `tc.generate()` 前注入绝对路径（解决 CI llvm-ar 探测失败）；`package()` 用 `meson.install()` 仅安装正式 `bin/qbootctl`；`qbootctl-test` 复制到包内测试专用目录 `test/`（不进入 bin/、不暴露于 `cpp_info.bindirs`），供 test_package 运行。

## 依赖版本

- 运行时依赖：无外部库（自实现 CRC32；linux/bsg.h、scsi/scsi_bsg_ufs.h 由 OHOS sysroot 提供）
- 构建依赖：meson 1.11.1、ninja 1.13.1、clang 15.0.4

## 验证结果

```bash
# 生产二进制（无宏）：语义与上游一致，非 root 全拒绝
qbootctl                               # This program must be run as root! (exit 1)
qbootctl -h                            # 同上 (exit 1)
QBOOTCTL_BACKEND=mock qbootctl -c      # 环境变量被忽略 (exit 1, 无运行时开关)
strings qbootctl | grep QBOOTCTL_BACKEND   # 无输出（无 mock 开关字符串）

# 测试专用构建（QBOOTCTL_TESTING，纯内存 mock，无设备访问）
qbootctl-test -c      # Current slot: _a  (exit 0)
qbootctl-test -a      # Active slot: _a   (exit 0)
qbootctl-test -b a    # SLOT _a: is marked bootable (exit 0)
qbootctl-test -s b    # 内存写状态转换 (exit 0) → qbootctl-test -a 显示 _b
qbootctl-test -u a    # 内存写状态转换 (exit 0) → qbootctl-test -b a 显示 not marked bootable
qbootctl-test -m b    # 内存写状态转换 (exit 0) → qbootctl-test -n b 显示 marked successful
qbootctl-test -n c    # Expected slot not 'c' (exit 1) 非法槽位拒绝
qbootctl-test -h      # 帮助输出 (exit 0)
```

## 交付物（最终包内容）

| 路径 | 说明 |
|------|------|
| bin/qbootctl | arm64 CLI 可执行文件（生产，真实 backend，无 mock 代码、无运行时开关） |
| licenses/LICENSE | GPL-3.0 许可证 |
| test/qbootctl-test | 测试专用可执行文件（QBOOTCTL_TESTING，纯内存 mock，仅供 test_package，不进入 bin/、不暴露于 cpp_info.bindirs） |

**最终包 = bin/qbootctl + licenses/LICENSE + test/qbootctl-test（测试专用辅助产物，非正式安装程序）**

## 测试统计（2026-08-13 实跑）

- 上游测试用例: 0（无 tests/、无 meson test()、无 CI 脚本）
- test_package 测试用例: 1（单脚本入口 test_qbootctl.py）
- assertion_count: 30（实跑 passed=30 failed=0 total=30, exit 0）

## 注意事项

- 生产语义：bin/qbootctl 与上游完全一致（无 mock 代码、无运行时开关、非 root 全拒绝）。
- 危险操作（`-s/-m/-u/-i`）只允许在测试专用构建 qbootctl-test 上以内存 mock 状态执行（不触碰任何设备），生产 qbootctl 上禁止执行。
- 测试仅使用内存 mock + 当前目录普通文件 `.qbootctl-mock.state` + 临时目录；不访问 /dev、/proc、/sys、真实块设备。
- 上游无自动化测试（无 tests/、无 meson test()、无 CI 脚本），上游测试数 = 0。
---

**编译结束**: 2026-08-13 13:42
**最终状态**: built
