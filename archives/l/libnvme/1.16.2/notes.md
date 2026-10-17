# libnvme 1.16.2 — 适配笔记

## 基本信息

- **上游**: https://github.com/linux-nvme/libnvme （tag v1.16.2 tarball，LGPL-2.1-or-later）
- **适配状态**: built（本机 conan create RC=0，CI 待验）
- **构建系统**: Meson（meson >= 0.62，仓库 OHOS 适配版 conan 2.29.1 的 MesonToolchain 原生支持 OHOS→harmonyos 映射）
- **包类型**: library（libnvme.so + libnvme-mi.so，动态）
- **账号/分支**: j669539 / feat/libnvme-1.16.2（任务卡 #15014）

## 依赖

| 依赖 | 版本 | 用途 | 链接形态 |
|---|---|---|---|
| json-c | 0.18（制品仓已发布） | JSON 配置文件/树序列化（CONFIG_JSONC） | 动态（DT_NEEDED libjson-c.so.5） |
| openssl | 3.5.7（制品仓已发布） | DH-HMAC-CHAP / NVMe-TLS PSK 派生（CONFIG_OPENSSL） | 静态 PIC（不传播给消费者） |

禁用的可选依赖：keyutils（OHOS 无 keyctl syscall）、libdbus（默认禁）、liburing（默认禁）、python 绑定（需 swig）。

**内核头（核心关注点）**：libnvme 自带 Linux UAPI 兜底——`nvme/ioctl.h` 内嵌完整 NVMe ioctl 定义（`_UAPI_LINUX_NVME_IOCTL_H` 守卫），`linux/mctp.h` 缺失时 `HAVE_LINUX_MCTP_H` 探测失败自动 fallback 到 `src/nvme/mi-mctp-compat.h`。OHOS sysroot 提供 `linux/types.h` 即满足最小需求，**无需内核头包**。

## 构建命令

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
```

meson 配置要点（generate() 注入）：`-Dpython=disabled -Dopenssl=enabled -Dkeyutils=disabled -Dlibdbus=disabled -Dliburing=disabled -Ddocs=false -Ddocs-build=false -Dexamples=false -Dtests=true`，`wrap_mode=nofallback`。

## OHOS 平台适配点（4 个补丁）

### 补丁 1: `0001-test-utils-honor-TMPDIR-for-test-log-tmpfile.patch`
- **症状**: `test-mi: can't create temporary file for log buf: Permission denied`（mi/mi-mctp 测试 exit 1）
- **根因**: OHOS /tmp 只读（EROFS）；musl `tmpfile()` 硬编码 /tmp 且实测**不遵循 TMPDIR**（TMPDIR=$HOME/tmp 下重跑仍 EACCES）
- **修复**: `test_setup_log()` 改用 `mkstemp("$TMPDIR/libnvme-test-log-XXXXXX")` + 立即 unlink + `fdopen(w+)` 保持 tmpfile() 语义
- **注意**: 本机 meson test 的 TMPDIR 已由配方 `_build_env()` 注入 build_folder/tmp（可写）

### 补丁 2: `0002-scripts-portable-interpreter-for-kdoc-check.patch`
- **症状**: `meson test` 整体崩溃 `FileNotFoundError: .../scripts/kernel-doc-check`（mtest 未捕获异常）
- **根因**: OHOS 无 `/bin/bash`，`#!/bin/bash` shebang 直接 ENOENT
- **修复**: `#!/usr/bin/env bash`（PATH 上 /data/service/hnp/bin/bash 可被发现）

### 补丁 3/4: `000{3,4}-test-{sysfs,config}-portable-interpreter-and-tolerant-tar.patch`
- **症状A**: `env: exec bash -e: No such file or directory`（tree/config 系测试 exit 127）
- **根因A**: toybox `/usr/bin/env` 不支持带参数的 shebang（`bash -e` 被当作单一程序名）
- **修复A**: `#!/usr/bin/env bash` + 体内 `set -e`
- **症状B**: `tar: can't link 'X' -> 'X': No such file or directory`（sysfs tarball 解包失败）
- **根因B**: 测试 tarball 含 138 个**自引用硬链接**（X link to X），toybox tar 先 unlink 目标再 link，自引用时源已被删
- **修复B**: `tar -xk` 容错提取（普通文件先落盘保留，自引用硬链接条目报 File exists 被忽略），`sys/` 目录存在即视为成功

## json-c pkg-config 修正（配方内处理，非补丁）

json-c Conan 包头文件在 `include/json-c/` 子目录，而 libnvme 源码 `#include <json.h>`；PkgConfigDeps 生成的 json-c.pc Cflags 只有 `-I${includedir}` → meson `dependency('json-c')` 编译报 `fatal error: 'json.h' file not found`。配方 `_fix_jsonc_pc_include_subdir()` 在 Cflags 追加 `-I${includedir}/json-c`。

## C++ 测试（cpp-dump/cpp-misc）

meson 的 C++ 编译器 sanity check 运行探测二进制时需加载 `libc++_shared.so`，LD_LIBRARY_PATH 不含 SDK llvm/lib 时 C++ 语言探测静默降级（`cxx_available=false`），cpp-dump/cpp-misc 两个测试不注册。配方 `_build_env()` 已前置 SDK llvm/lib 与 aarch64-linux-ohos 两个目录 + /system/lib64，38 个测试全注册。

## 测试结论

上游 meson test 套件（build() 内真机执行，本机 = OHOS aarch64）：

| 指标 | 值 |
|---|---|
| 注册测试 | 38 |
| OK | 36 |
| EXPECTEDFAIL | 2（NBFT-bad-oldspec / NBFT-random-noise，上游标记 should_fail 的损坏表解析） |
| FAIL | 0 |

覆盖：mi(332断言)/mi-mctp/uuid/uriparser/tree/util/psk(48组向量)/ana/discovery/features/identify/logs/zns/misc/cpp-dump/cpp-misc + ioctl mock×7 + NBFT 表×14 + sysfs dump×2 + config JSON×5 + kdoc(kernel-doc 注释规范)。

test_package：CMake 消费者冒烟 10 断言（版本=1.16.2/根对象/控制器分配/JSON配置读取/UUID转换/TLS密钥导出导入回环/TLS身份派生/MI根对象）。

## 验证命令（复现）

```bash
# 探索期（源码树直配，验证平台适配）
meson setup build --prefix=$HOME/usr/local -Dpython=disabled -Dopenssl=enabled \
  -Dkeyutils=disabled -Dlibdbus=disabled -Dliburing=disabled \
  -Ddocs=false -Ddocs-build=false -Dtests=true -Dexamples=false
ninja -C build && (cd build && TMPDIR=$HOME/tmp meson test)
# → Ok: 36, Expected Fail: 2, Fail: 0

# 正式配方
conan create archives/l/libnvme/1.16.2 -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

## 已知限制

- keyutils/keyctl 相关 API（nvme_insert_tls_key 落 keyring 等）在 OHOS 不可用（无 syscall），编译期禁用不影响库核心功能
- examples/python 绑定/doc 构建未启用（非库本体交付物）
- CI worker 若无 meson，配方内 `_ensure_meson_available()` 会 pip install --user meson 兜底（babl 先例）
