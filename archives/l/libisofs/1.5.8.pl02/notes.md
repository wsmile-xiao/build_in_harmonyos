# libisofs 1.5.8.pl02 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，libtool -version-info）
- 编译日期: 2026-09-17
- 编译器: clang（OHOS 交叉工具链 aarch64-unknown-linux-ohos，经 Conan conf 提供）
- 状态: built（static/shared 双变体 conan create RC=0，test_package 22/22 真实执行通过，见 notes.md 验证结果）

## 上游信息

- 上游仓库: https://dev.lovelyhq.com/libburnia/libisofs
- 上游版本: 1.5.8.pl02（当前 release，tarball `libisofs-1.5.8.pl02.tar.gz`）
- 源码包: `https://files.libburnia-project.org/releases/libisofs-1.5.8.pl02.tar.gz`
- sha256: `10bd584d8f00d8091e814902b9f0a3e209f16e938f510fc23ba05f3fa469db5a`（2026-09-17 下载 tarball 实测）
- 许可证: GPL-2.0-or-later（COPYING 为 GPLv2 全文，COPYRIGHT 注明 libburnia 例外条款措辞）
- 依赖: 无必需第三方依赖。zlib（zisofs/gzip 过滤器）、libacl/xattr（AAIP 系统适配器）、libjte（Jigdo 模板提取）、lfa-flags、projid 均为 configure 探测、缺失自动降级；THREAD_LIBS=-lpthread 为系统库。

## 上游测试审计（结论：无活跃自动化测试套件）

- 顶层 `Makefile.am`：唯一 `noinst_PROGRAMS = demo/demo`（API 演示，无断言）；`check_PROGRAMS` unit-test 段（原依赖 -lcunit 的 test/test.c、test_node.c、test_image.c、test_tree.c、test_util.c、test_rockridge.c、test_stream.c、mocked_fsrc.c）**整段被上游注释**，注释原文（ts A90428, ticket 147）："The test code does not use the API and is totally outdated in its creation of mocked objects. A volunteer is needed to rewrite it using the API."
- tarball 无 `test/` 目录、无 gtest（`TEST(`/`TEST_F`）、无 ctest、无 pytest 痕迹。
- `demo/` 其余程序（tree/find/iso/isoread/isocat/isomodify/isoms 等）均在 Makefile.am 中被注释，不随 tarball 构建，为演示代码非测试。
- 因此 `test_package/MANIFEST.yml` 记 `upstream_tests_exist: false`，上游正式自动化测试数量为 0，本包以 test_package 真实往返测试作为可执行质量门禁。

## 编译步骤

```bash
# Conan 2, AutotoolsToolchain:
conan create . --build=missing -pr <ohos-aarch64 profile> -o shared=False
conan create . --build=missing -pr <ohos-aarch64 profile> -o shared=True
# 内部执行:
#   patch (config.sub + configure umask)
#   configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
#              （a52dec 范式：显式 GNU triplet，绕过 config.guess 不识 HarmonyOS）
#   make -j1 && make install (DESTDIR=package_folder)
#   删除 libtool *.la 包装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无显式 triplet 时 configure 报 "cannot guess build type"（E160）；带 OHOS triple 时 config.sub 拒绝 `aarch64-unknown-linux-ohos`（E007） | OHOS 构建机 uname 输出 HarmonyOS/linux-ohos，上游 2013 年版 config.guess/config.sub 均不认识 | 双保险：conanfile 显式 `--build/--host=aarch64-unknown-linux-gnu` 绕过 config.guess（a52dec 范式，E160 推荐路径）；补丁 `0001-config.sub.patch` 放行 linux-ohos triple（同 1.5.6 做法，防 sub-configure 场景） |
| 2 | configure 生成的 `conftest.dSYM`/config.status 临时目录以 umask 077 创建，重跑 configure 或 HMDFS setgid 构建目录下失败 | configure 内建 umask 077 与 HMDFS setgid 目录语义冲突 | 补丁 `0002-configure.patch`：umask 077→002（复用知识库 E011/E129 根因） |
| 3 | `struct burn_source` 在 libisofs.h 中仅前向声明，直接 include 无法使用 `burn_src->read_xt` | 完整定义在 `#ifdef LIBISOFS_WITHOUT_LIBBURN` 块内（应用不链接 libburn 时需自行定义该宏） | test.c 在 include 前定义 `LIBISOFS_WITHOUT_LIBBURN`（上游 demo/demo.c 同款做法） |
| 4 | `iso_memory_stream_new` 传静态数组会在流销毁时对静态内存调 free() | API 契约：流接管 buf 所有权并 free() | 传 malloc() 副本（test.c 中 `owned` 缓冲） |
| 5 | `burn_source_free` 未在 libisofs.ver 导出表内 | 上游导出表仅导出 iso_* 符号，burn_source 属应用侧结构 | 释放用 `burn_src->free_data(burn_src); free(burn_src);`（demo.c 同款），测试不调用 burn_source_free |
| 6 | import 后 `iso_node_get_attrs` 返回 0 条 xattr，AAIP 往返断言失败 | **API 陷阱**：`iso_read_opts_new()` 默认 `noaaip=1`（读端默认不加载 AAIP），写端 `iso_write_opts_set_aaip(1)` 只影响写入 | import 前显式 `iso_read_opts_set_no_aaip(ropts, 0)`（fs_image.c:7363 实证默认值；测试已含此调用并真实往返验证） |

## 源码修改

两处补丁（`conandata.yml` 登记，a/ b/ 路径头、无时间戳）：

1. `0001-config.sub.patch` — config.sub 接受 linux-ohos triple（portability，E007）
2. `0002-configure.patch` — configure config.status 临时目录 umask 077→002（portability，E011/E129）

## 依赖版本

- zlib/1.3.1.1：configure 默认 `--enable-zlib` 探测，OHOS sysroot 提供 zlib.h+libz，探测成功后 zisofs/gzip 过滤器编入库（构建日志确证 `-DLibisofs_with_zliB`，zisofs.o+aaip_0_2.o 在库成员中，动态库 NEEDED 含 libz.so），为真实链接依赖。
- 可选依赖探测结果分两类：zlib（上条，真实链接依赖）；xattr/lfa-flags/projid（系统头文件探测启用，无额外库）；libacl/libjte 未探测到，对应功能降级，不影响核心 ISO 9660/Rock Ridge/AAIP 功能。
- 构建仅需 CC/AR（OHOS clang 工具链，经 Conan conf 提供）+ GNU make；THREAD_LIBS=-lpthread 为系统库。
- 实际探测结果（构建 Makefile 实证）：`ZLIB_DEF`、`XATTR_DEF`（-DLibisofs_with_aaip_xattR -DLibisofs_with_sys_xattR）、`LFA_DEF`、`PROJID_DEF` 均启用；ACL_DEF、JTE_DEF 未设置（sysroot 无 libacl/libjte，对应功能降级不影响核心 ISO 9660/Rock Ridge/AAIP）。

## 验证结果

2026-09-17 实测（ohos-aarch64 profile，本机即 HarmonyOS aarch64 构建机，测试真实执行）：

```text
conan create . -o shared=False  → RC=0，test_package: 22/22 CHECK 全 PASS
conan create . -o shared=True   → RC=0，test_package: 22/22 CHECK 全 PASS
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"checks":22,"passed":22}
```

ELF 专项（readelf 实测）：

- shared：`libisofs.so.6.94.0` ELF64 AArch64 DYN，SONAME=libisofs.so.6，NEEDED 仅 libz.so/libc.so（全目标侧），无 RPATH/RUNPATH
- static：`libisofs.a` 36 个成员均 AArch64 ELF64 REL，含 zisofs.o/aaip_0_2.o（zlib/AAIP 功能实证编入）

test_package 覆盖（`test.c`，22 个 CHECK，全部经真实 libisofs API）：

1. `iso_lib_version` 运行时版本为 1.5.x
2. `iso_lib_is_compatible(1,5,0)` 返回 1
3. 镜像生成返回块数 >0（`iso_init`/`iso_image_new`/`iso_tree_add_new_dir`/`iso_memory_stream_new`/`iso_tree_add_new_file`/`iso_tree_add_new_symlink`/`iso_tree_add_new_special`/`iso_node_set_attrs`/`iso_image_create_burn_source`/`read_xt` 写盘全链路；含写端 `iso_write_opts_set_aaip(1)`）
4. 读回镜像块数与写入一致（`iso_read_image_features_get_size`；读端显式 `iso_read_opts_set_no_aaip(ropts, 0)` 解除默认 noaaip=1）
5. 卷 ID 往返一致（`iso_image_get_volume_id`）
6. `/data/hello.txt` 路径解析成功（`iso_tree_path_to_node`）
7. 节点类型为 LIBISO_FILE
8. 文件大小往返一致（8192 字节，`iso_file_get_size`）
9. mtime 往返一致（RRIP TF，`iso_node_get_mtime`）
10. 权限往返一致（0644，RRIP PX，`iso_node_get_permissions`）
11. `iso_file_get_stream` 返回流
12. `iso_stream_open` 成功
13. 流读取满 8192 字节
14. 文件内容逐字节一致（`iso_stream_read` 往返）
15. AAIP xattr 存在（`iso_node_get_attrs`，HarmonyOS 专项：aaip-os-linux.c 路径）
16. AAIP xattr 名+值往返一致（user.hmbs_test=ohos-aarch64）
17. `/readme` 符号链接解析成功且类型/目标正确（`iso_symlink_get_dest`）
18. `/event-pipe` special 节点解析成功且保持 S_IFIFO 类型（`iso_node_get_mode`）

其中 #15/#16 为 HarmonyOS 专项覆盖：AAIP xattr 系统适配器在 OHOS 上经 `__linux__` 宏选用 `aaip-os-linux.c`（Linux xattr 语义），断言其在真实镜像生成/读回往返中行为正确；#9/#10 覆盖时间/权限字段在 musl 时间处理路径（tm_gmtoff/timezone）下的往返；#18 覆盖设备节点元数据（Rock Ridge 特殊文件条目，不写数据块）。

## 交付物

| 文件 | 说明 |
|------|------|
| include/libisofs/libisofs.h | 唯一公开头文件（libinclude_HEADERS） |
| lib/libisofs.a（默认）/ libisofs.so.6.94.0 + libisofs.so.6 + libisofs.so（shared） | 静态 / 共享库（链接名 `-lisofs`，libtool -version-info → SONAME libisofs.so.6，实测 ELF64 AArch64 DYN） |
| lib/pkgconfig/libisofs-1.pc | pkg-config 文件（LIBBURNIA_PKGCONFDIR） |

## 注意事项

- 链接名是 `-lisofs` 而非 `-llibisofs`；`package_info()` 已设 `cpp_info.libs=["isofs"]`，test_package 经 `find_package(libisofs)` / `libisofs::libisofs` 消费。
- 本库非系统同名库（R26 不适用），默认 static（`shared=False`）。
- OHOS 上该库只做镜像生成/解析（用户态文件打包），不触碰实际设备节点；上游 mknod 路径仅在"恢复模式导入含设备文件的镜像"时走，且走 RRIP 元数据恢复（`iso_special_get_dev` 语义），无 root 需求。
- 本轮严禁 commit/push；以上验证结论待真机 evidence 轮实测后回填，不得作为已验证引用。
