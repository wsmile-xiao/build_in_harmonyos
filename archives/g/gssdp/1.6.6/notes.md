# gssdp 1.6.6 适配笔记

## 编译环境
- 构建系统: meson (>= 0.54.0)
- 编译日期: 2026-09-02
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链）
- 状态: built
- 积分归类: 【积分赛】路径 A 正常适配（1 分）

## 背景

gssdp 是 GUPnP 协议栈的底层 SSDP（简单服务发现协议）库，是 gupnp 适配的前置
缺失依赖。直接依赖 glib2（glib-2.0 / gobject-2.0 / gio-2.0）与 libsoup3
（libsoup-3.0），不直接依赖 libxml2（那是 gupnp 的依赖）。构建系统为 meson，
与 libsoup3 3.6.5-r1 同栈（GLib meson），交叉编译处理复用 libsoup3 的已验证方案。

## 编译步骤

```bash
# 源码（官方 GNOME 源，NJU 镜像 200 作 fallback，USTC 404 已排除）
# https://download.gnome.org/sources/gssdp/1.6/gssdp-1.6.6.tar.xz
# sha256: 767d2275254ce0efeaeac64419ff9f4f0ad470d134ef672f5c556b2abb786bcb

# conan create（host/build 同 ohos-aarch64 profile）
# ⚠️ 设备 shell 默认 LD_LIBRARY_PATH 含空格（chipset-pub-sdk:   <空格>/system/lib64），
# musl 动态链接器解析失败 → ninja 加载 libc++_shared.so 报 rc=127（本地铁证），
# meson 因此报 "Could not detect Ninja v1.8.2 or newer"。需重设为无空格路径。
export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64"
conan create archives/g/gssdp/1.6.6 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson "Could not detect Ninja v1.8.2 or newer" | 平台默认 LD_LIBRARY_PATH 含空格，musl loader 解析失败，ninja 启动 rc=127（加载 libc++_shared.so 失败），meson 探测误报为无 ninja | export 无空格的 LD_LIBRARY_PATH（含 /system/lib64，libc++_shared.so 所在地） |
| 2 | libgssdp 编译 `linux/socket.h: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 linux/netlink.h 与 sys/socket.h 双重定义 sockaddr_storage；鸿蒙不开放 netlink | 补丁 0001：`#if defined(__linux__) && !defined(__OHOS__)` 排除 netlink（mac_lookup 回退返回 IP 本身，与 darwin/win 分支同语义） |
| 3 | glib2 shared 重建链 zlib 失败 R_AARCH64 relocation | 已发布 zlib/1.3.1 非 PIC | 配方根级 `requires("zlib/1.3.1.1", override=True)`（PIC 变体）；详见问题 6 的折叠副作用说明 |
| 4 | 上游 meson test 双双 SIGABRT：`g_type_register_static: assertion failed: (static_quark_type_flags)` | ohpcd 只发布 static glib2；libsoup-3.0.so、libgssdp.so（旧配方）、测试 exe 各自内嵌一份 gobject → 进程内多副本，GType 注册在未初始化副本上撕裂 | 见问题 5+7 的组合修复 |
| 5 | `--exclude-libs,ALL` 修法失败（SIGSEGV / G_TYPE_IS_INITABLE false） | exclude-libs 只隐藏动态符号表，.so 内部对静态库符号的引用在链接时已绑定本地副本（未 init）→ 类型表跨副本不可见 | 弃用 exclude-libs；改为"去源头"——.pc Libs 置空让静态 glib 完全不进入链接 |
| 6 | 根级 zlib override 折叠 libsoup3 的 zlib 直接依赖 → libsoup3（glib2/*:shared 触发重建）时 PkgConfigDeps 不生成 zlib.pc → meson 解析 gio-2.0 的 Requires.private: zlib 失败 | conan 2.29 override 语义：上游 override 折叠下游声明的同包 override require（已用最小复现实验证实） | 不设 `glib2/*:shared=True`（用已发布的 static-glib 传播版 libsoup3 包），只保留 root zlib override |
| 7 | test exe 静态链入全量 glib（4108 个 g_* 定义） | PkgConfigDeps 生成的 generators/glib-2.0.pc（排在 pkg_config_path 首位）Libs 带全量静态链接列表；libsoup-3.0.pc 的 Requires: glib-2.0 展开命中它 | generate() 里同时置空 glib2-pc-fix/*.pc 与 generators/glib-2.0.pc 的 Libs 行 → g_* 全部 UND，运行时统一解析到 libsoup-3.0.so 导出的唯一 gobject 副本（其内部调用走 PLT 可被解析） |
| 8 | test_package 空壳版同样 GObject 崩溃 | CMakeDeps 把 glib2::glib2 等静态库链进测试 exe（cpp_info.libs 并入了 glib 全家） | cpp_info.libs 只声明 gssdp-1.6 本体；CMakeLists 只链 gssdp-1.6::gssdp-1.6；include 路径仍暴露 glib2 头文件目录保证编译 |
| 9 | AR=llvm-ar 等环境变量坏 | PATH 无 llvm-ar | generate() 里 os.environ.pop + shutil.which 定位真实 GNU 工具（复刻 glib2/libsoup3） |
| 10 | 共享库 strip 破坏 .codesign 哈希 | OHOS loader 校验哈希 | tc.strip=None；meson install 清理 DT_RUNPATH 后用 build 产物覆盖 |

## GObject 单副本方案（本适配核心创新，R40 级）

```
消费者 (exe/test)
   │ UND g_* / gssdp_*
   ▼
libgssdp-1.6.so.0        ← 只含 gssdp 代码，0 个 g_* 定义
   │ NEEDED
   ▼
libsoup-3.0.so.0         ← 导出完整 glib/gobject 符号表（唯一副本）
   │ NEEDED
   ▼
libpsl / libnghttp2 / libc
```

- 上游 .pc（glib2-pc-fix 复制件）与 conan 生成 .pc 的 Libs 全部置空，静态 glib
  不进入任何链接命令；
- libgssdp.so 与测试产物对 g_* 的引用全部是 UND，运行时统一解析到
  libsoup-3.0.so 的导出符号，全进程单 GObject 域；
- 上游测试 test-functional / test-regression 与 test_package 全部跑通。

## 源码修改

- patches/0001-libgssdp-gssdp-net-posix.c.patch：OHOS 排除 netlink
  （`#if defined(__linux__) && !defined(__OHOS__)`，两处：include 守卫 +
  gssdp_net_mac_lookup 的 netlink 实现守卫；OHOS 下回退返回 IP 字符串，
  与上游非 linux 分支同语义）。
- R8 说明（补丁使用平台宏的理由）：OHOS sysroot 的 linux/socket.h 与
  sys/socket.h 对 sockaddr_storage 双重定义是编译期硬冲突（两个均为系统头，
  无法用 POSIX feature detection 规避）；鸿蒙不开放 netlink。glib2 2.88.0 的
  0002-disable-netlink-for-harmonyos.patch 是同款 __OHOS__ 判定先例。

## 依赖版本

- glib2/2.88.0（静态 .a，经 .pc 修复 + 符号统一方案使用）
- libsoup3/3.6.5-r1（共享 .so，gobject 唯一提供者）
- zlib/1.3.1.1（root override，PIC 变体，传递依赖）

## 验证结果

```bash
# conan create 成功（完整日志 .ci_logs / $HOME/tmp/gssdp-conan-create-11.log）
# 上游 meson test（OHOS 设备原生执行）:
#   1/2 gssdp:Functional test     OK  20.71s  (TAP 子用例 7/7:
#       /functional/creation, /functional/resource-group/discovery/{ssdp:all,
#       upnp:rootdevice,uuid,versioned/matching,versioned/backwards-compatible,
#       versioned/ignore-older})
#   2/2 gssdp:Bug regression test OK   0.04s  (TAP 子用例 2/2:
#       /bugs/ggo/7, /bugs/ggo/22)
#   Ok: 2  Fail: 0   （子用例合计 9/9 通过，通过率 100%）
# test_package L1: 编译链接运行全过（真实 API: gssdp_client_new_for_address
#   + gssdp_client_get_active + gssdp_resource_group_add_resource_simple）
# gssdp/1.6.6: Package '0800d078e334ea104805c49c53173dc49f8c57eb' created
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（glib .pc Libs 置空单副本方案 + 交叉编译 + gnome 模块） |
| conandata.yml | 官方源 + NJU 镜像 + sha256 + 补丁声明 |
| test_package/ | CMake L1 测试（真实 GSSDP API，单副本链接） |
| patches/0001-libgssdp-gssdp-net-posix.c.patch | OHOS netlink 排除 |
| manifest.yaml / notes.md / MANIFEST.yml | 元数据 |

## 注意事项

- PR 标题前缀用【积分赛】（路径 A 正常适配，1 分），不用【依赖项】。
- gssdp 的 `tests/` 目录无条件编译（无 tests 选项），build() 在 OHOS 设备原生
  执行 `meson test`（glib2 recipe 同款 `--timeout-multiplier=16`）。
- 下游 gupnp 适配时建议沿用本配方"GLib .pc Libs 置空 + libsoup.so 单 gobject
  副本"方案，避免重蹈 GObject 多副本 SIGABRT。
- 设备并行任务多，ninja -j20 时 functional test 实测 20.7s（含 localhost SSDP
  收发），timeout-multiplier=16 足够。
---

**编译结束**: 2026-09-02 15:05
**最终状态**: built

## R8 合规修复（2026-09-02 审查意见闭环）

AI Review 阻塞项：patch 0001 原用 `!defined(__OHOS__)` 平台宏，违反 R8（补丁不得引入平台条件编译宏）。已改为**配方层注入特性宏**方案：

- 补丁改为 `#if defined(__linux__) && !defined(GSSDP_NO_NETLINK)`（两处 hunk）
- conanfile.py `generate()` 注入 `tc.c_args/cpp_args = ["-DGSSDP_NO_NETLINK"]`——裁剪由配方控制而非工具链平台宏
- 裁剪原因：OHOS sysroot 的 linux/socket.h 与 sys/socket.h 对 sockaddr_storage 双重定义，linux/netlink.h 根本无法 include（编译期错误，无法用 meson feature detection 规避——检测代码本身 include 头文件就炸）；鸿蒙不开放 netlink socket。裁剪后 mac_lookup 走与上游 darwin/win 相同的回退分支（返回 IP 字符串）
- 同类先例参考：glib2 2.88.0 的 0002-disable-netlink-for-harmonyos.patch（该 PR 走的是 R8 豁免；本 PR 采用特性宏方案，完全无平台宏）
