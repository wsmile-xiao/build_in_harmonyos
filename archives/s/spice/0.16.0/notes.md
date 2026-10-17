# spice 0.16.0 适配笔记

SPICE（Simple Protocol for Independent Computing Environments）远程桌面协议的
**server 侧库**（libspice-server）——QEMU / 独立 server 进程经此向客户端提供
远程显示、键鼠与外设通道。上游 0.16 为 meson 构建的 C + C++ 混合工程，
tarball 内置 spice-common subproject 实体目录（无 .wrap、无网络子模块拉取）。

## 编译环境

- 构建系统: meson（MesonToolchain cross file）
- 上游版本: 0.16.0（LGPL-2.1）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 验证: `conan-verify` 8 门禁全 PASS（G0/G1/G2/G3/G4/L2/L4/L5，
  报告 `reports/conan-verify-report.md`，2026-10-03T12:28）

## 产物

| 项 | 值 |
|---|---|
| 共享库 | `lib/libspice-server.so`（单一无版本文件，SONAME 同名）|
| 头文件 | `include/spice-server/*.h` × 10 |
| pkg-config | `lib/pkgconfig/spice-server.pc` |
| DT_NEEDED（5）| libglib-2.0.so.0 / libpixman-1.so.0 / libjpeg.so.62 / libc++_shared.so / libc.so |
| 大小 | 6199872 B（自签后）|

## 关键适配决策

### 1. 消费者依赖传播：transitive_headers / transitive_libs（G2 实测）

**本平台 conan 的 `requires` 默认不向消费者传播**。第一轮 G2 在 test_package
编译期失败：

```
spice-core.h:33:10: fatal error: 'spice/qxl_dev.h' file not found
```

根因：`spice-core.h`（公开头）包含 spice-protocol 的 `<spice/qxl_dev.h>`，
但消费者侧 CMakeDeps 只生成了 **3 个依赖 target**（glib / pixman /
libjpeg-turbo——恰好全是共享库），静态依赖（openssl / zlib / lz4）与
header-only 依赖（spice-protocol）全部缺失。

修复：7 个 `requires` 全部显式声明 `transitive_headers=True,
transitive_libs=True`——这是平台惯例，全仓 **412 处**同款写法。
修复后消费者 target 恢复为全量 **8 个**（7 依赖 + spice-server 本体），
`spice-protocol::spice-protocol`、`ZLIB::ZLIB`、`openssl::openssl` 等
全部出现。此结论对一切"公开头链引用其它包"的配方通用。

### 2. 单一无版本共享库（补丁 0005）

hmdfs 家目录禁止符号链接（`ln -s` EPERM），meson 探测后打印
`Symlink creation does not work on this platform. Skipping all symlinking.`
并跳过全部 symlinking：versioned 目标只安装 `libspice-server.so.1.15.0`
本体，**缺 `.so` 开发链接**——消费者 CMakeDeps 精确名
`find_library(spice-server)` 配置期直接 `Library 'spice-server' not found`，
链接器 `-lspice-server` 同样失败。

平台规范即单一无版本文件（工具链 `no-versioned-soname.cmake` 文件头：
"Every published OHOS ecosystem library is a single unversioned file"，
如 libKF6Screen.so / libQt6ShaderTools.so）。修复 = 去掉
`server/meson.build` 中 `library('spice-server', version : ...)` 的
`version` 参数，产出单一 `libspice-server.so`（真机 readelf 实测
`SONAME libspice-server.so`）。cmake 侧等价物为先例 libwebp 的
`-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`。Linux 宿主上该参数仅影响
文件名与 SONAME，行为无差异。

### 3. AF_UNIX 的 OHOS 方言（补丁 0003 / 0004）

- **ENOPROTOOPT**：OHOS 对 AF_UNIX socket 设置 `IPPROTO_TCP` 的
  keepalive 选项返回 `ENOPROTOOPT(92)`，而上游 `red_socket_set_keepalive`
  容错集合仅覆盖 `ENOTSUP/EOPNOTSUPP` → accept unix 连接时打
  `g_warning`，测试框架把 Spice 警告视为致命（test-leaks 因此 Bail
  out）。同文件 `red_socket_set_no_delay`（TCP_NODELAY）已有完全相同
  写法的先例，照抄一行补 `errno != ENOPROTOOPT`。
- **抽象命名空间**：hmdfs 上路径式 unix socket 的 `bind()` 一律 EPERM
  （`/tmp` 只读挂载）。test-listen 的 `connect_unix` 先在 cwd 做 bind
  探测，失败则回退 `@` 抽象命名空间——服务端 `reds_init_socket` 原生
  支持该形式，客户端按其相同的 `SUN_LEN` 约定连接。常规 Linux 上探测
  成功，行为与上游一致。

### 4. shebang 脚本不可直接 execve（补丁 0001）

OHOS 内核/沙箱禁止 shebang 脚本直接执行（脚本可执行位齐全仍 EACCES，
rc=126）。顶层 meson.build 两处构建期 `run_command`（`git-version-gen`
取版本、`check-spice-common` 子模块检查）改为显式 `sh` 调用；同理
`glib-mkenums`（meson gnome 模块，生成 spice-server-enums.c/h）在
machine file `[binaries]` 注入 `[python3, <脚本>]` 命令数组（先例 glib）。

### 5. 构建形态与注入

| # | 问题 | 处理 |
|---|------|------|
| 1 | MesonToolchain 不写 ar/ranlib；cross 侧缺 pkg-config | `_inject_meson_binaries()` 从编译器同目录推导 llvm-ar/llvm-ranlib 注入 meson ini（先例 glib/pixman）|
| 2 | `dependency('liblz4')` 但 Conan lz4 只生成 lz4.pc | `_alias_lz4_pc()` 复制为 liblz4.pc（先例 glib _alias_pcre2_pc）|
| 3 | codegen（Marshallers/parser）需要 pyparsing，缺模块 `exit(1)` | conandata 第二源固定 pyparsing 2.4.7 纯 python sdist（MIT）+ `PYTHONPATH` 前置（先例 glib proxy-libintl）|
| 4 | `SPICE_USE_SAFER_CONTAINEROF` 走 GNU 语句表达式 + `typeof` | 显式固定 `gnu++17`（覆盖 profile 映射出的 strict c++17）|
| 5 | 桌面相关功能 | gstreamer/sasl/opus/smartcard/manual/instrumentation 全关；保留 lz4 与上游测试（tests=true）|
| 6 | 重签名 | `package()` 后对 lib/**/*.so* 走 binary-sign-tool 自签（先例 glib）|

### 6. 上游测试在 build() 内真实执行

native OHOS 上 `meson test -v --timeout-multiplier=16 --no-rebuild`
（先例 glib）；cross 跳过执行。**实测 Ok: 23 / Fail: 0**
（server 18 + spice-common 5，无跳过）。test-ssl-verify 需要补丁 0002：
该测试以符号插入方式故意重定义 `X509_NAME_add_entry_by_txt`，静态
libcrypto.a 下归档成员因其余 X509 符号被拉入导致双强定义冲突 → 测试
目标加 `-Wl,--allow-multiple-definition`（先定义者胜=测试桩，等价共享库
插入语义；shared openssl 场景下为空操作）。

## test_package（消费者视角，22 断言全过）

| 用例 | 结果 | 覆盖 |
|---|---|---|
| test_spice_server_api | 8/8 | 链接 `spice-server::spice-server` 真实调用公开 API：`SPICE_SERVER_VERSION=0x001000` 宏可见；new；set_port(5912) 通过 / (70000) 越界拒绝；set_name；set_ticket（含 NULL passwd）；destroy |
| test_ohos_platform | 9/9 | 包内 libspice-server.so 平台 ABI 实测：ELF64/EM_AARCH64/PT_DYNAMIC；DT_NEEDED 5 项含 `libc.so`、无 `libc.so.6`、含 `libc++_shared.so`；OHOS loader `dlopen(RTLD_NOW)` |
| test_ohos_runtime | 5/5 | 运行时闭包实测：包内每个真实共享库 dlopen（1 found / 1 loaded）；闭包驻留后重加载；5 个契约符号 dlsym；loader 路径完整 API 调用 new→set_port/set_name/set_ticket→destroy |

## 补丁清单

| 补丁 | 内容 |
|---|---|
| 0001 | meson run_command 显式 sh 调用（shebang EACCES）|
| 0002 | test-ssl-verify 静态 openssl 桩冲突（--allow-multiple-definition）|
| 0003 | keepalive 容错补 ENOPROTOOPT（照 no_delay 先例）|
| 0004 | test-listen 回退抽象命名空间 unix socket |
| 0005 | server/meson.build 去 version 参数 → 单一无版本 libspice-server.so |
