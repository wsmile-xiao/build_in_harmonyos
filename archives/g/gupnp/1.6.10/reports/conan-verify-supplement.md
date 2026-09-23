# conan-verify supplement — gupnp 1.6.10

> 工具 conan-verify 的 G4/L2/L4/L5 在 `--user=ohpcd --channel=stable` ref 形态下
> 静默跳过（报告原文："无法找到程序包 ID" / "跳过（无 cache 路径）"，见
> `conan-verify-report.md`）。按 workflow 7.2 本文件为人工补测记录，全部证据
> 来自清缓存采信轮（conan create 干净重建，日志 `conan-create.log`）的真实产物。

采信轮信息：
- ref: `gupnp/1.6.10@ohpcd/stable`
- package_id: 见 `p/b/gupnp246d758781529`（conaninfo: os=OHOS, arch=armv8,
  compiler clang 15, libcxx libc++, cppstd 17, Release, shared=True）
- package folder: `/storage/Users/currentUser/.conan2/p/b/gupnp246d758781529/p`
- HEAD: `86955451322c66caaef5f83560d0c14c0ce1bb5e`（分支 feat/gupnp-1.6.10）
- 采信轮缓存自检：清缓存（`conan remove gupnp/* -c` + `p/` 下 gupnp 分片目录
  手工清除）后 conan create 实跑，日志含 `RUN: ninja` 等价构建行与
  `meson test` 测试计数（见下）。

## G4: 产物完整性（人工核对）

package folder 清单（`find p/ -type f`）：

- `lib/libgupnp-1.6.so.0.106.10`（含 `libgupnp-1.6.so.0` / `libgupnp-1.6.so`
  符号链接）
- `lib/pkgconfig/gupnp-1.6.pc`
- `include/gupnp-1.6/libgupnp/`：gupnp.h 等 21 个公共头（含 meson 生成的
  gupnp-enums.h）
- `bin/gupnp-binding-tool-1.6`（上游安装的 Python 3 脚本）

与 `package_info()` 声明一致：libs=["gupnp-1.6"]、
includedirs=["include/gupnp-1.6"]、pc 名 gupnp-1.6。G4 实质 PASS。

## L2: 消费者实测（人工补测）

1. **test_package 真实消费者**（CMakeDeps 链 `gupnp-1.6::gupnp-1.6`，运行
   `test_gupnp`）：创建 context manager（unix 回退实现）、`127.0.0.1` 上
   `gupnp_context_new_for_address`、端口/主机 IP 断言、控制点 ssdp:all
   启停（真实回环 SSDP 流量）、根设备描述发布与 UDN 断言。
   `conan create` 内 `RUN: ... ; ./test_gupnp` 退出码 0（采信轮日志）。
   本机直跑同二进制再次 PASS（rc=0）。
2. **dlopen**：`dlopen(libgupnp-1.6.so.0.106.10, RTLD_NOW)` 成功，
   `dlsym(gupnp_context_manager_create)` 非空（对采信轮产物实测，rc=0）。
   说明 .codesign 内嵌哈希完整、musl 加载器校验通过。
3. **命令行产物**：`python3 bin/gupnp-binding-tool-1.6 -p test -m client
   <scpd.xml>` 对采信轮产物实测，成功生成 C 绑定代码（rc=0）。
4. **上游测试**（同轮包内原生执行，meson test --timeout-multiplier=16）：
   7 个测试程序 56 个 TAP 子用例，Ok: 7 / Fail: 0，`^ok ` 计数 56、
   `^not ok ` 0、SKIP 0。

## L4: 安全属性（人工 checksec，readelf 实测）

libgupnp-1.6.so.0.106.10：
- `GNU_STACK RW`（栈不可执行，NX）
- `GNU_RELRO` + `FLAGS BIND_NOW` / `FLAGS_1 NOW`（Full RELRO）
- `Type: DYN`（共享对象，PIC）

test_gupnp（消费者可执行文件）：
- `GNU_STACK RW`（NX）
- `GNU_RELRO` + `BIND_NOW`/`NOW PIE`（Full RELRO + PIE）
- `Type: DYN (Position-Independent Executable file)`（PIE）

## L5: 产物基线（人工 sha256）

- 采信轮打包产物与构建树链接产物**逐字节一致**
  （`cmp` 通过，两者 sha256 相同）：
  `1fdd4d1431d16bb502d5d2df9c3b543c8e5238b47b840a1061a5e62e25aa5384
  lib/libgupnp-1.6.so.0.106.10`
- 定义符号画像：257 个定义 dynsym（gupnp_* API 210 个；g_* 仅 8 个 =
  guuid.c.o/gzlibcompressor.c.o 最小补链成员自身；无 g_type_*/g_object_*
  重复定义，GObject 单副本成立）
- NEEDED：libsoup-3.0.so.0、libgssdp-1.6.so.0、libxml2.so.16、libc.so
- .codesign 段存在（readelf -S 计数 1）

## G0 知识命中说明

G0 命中 E090（meson host_system 'harmonyos' vs 'linux'）为检索错配：gupnp
1.6.10 的 meson.build 无 `host_machine.system() == 'linux'` 条件（仅
`!= 'windows'` 与 netlink 探测），其 unix context manager 路径不依赖
host_system=='linux' 判定；G2 干净构建与全部测试通过为实证。按 workflow
7.2（知识建议与实际错误类别无关时忽略）处理。
