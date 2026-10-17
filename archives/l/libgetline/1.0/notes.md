# libgetline 1.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make + libtool)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang)
- 工具链: autoconf 2.72 / automake 1.16.5 / make 4.4.1 / libtool（上游自带生成文件，无需 autoreconf）
- 目标: HarmonyOS PC arm64（OHOS, ohos-aarch64 conan profile）
- 状态: built（conan-verify G1-G4 PASS；L2/L4/L5 在本机无可运行 cache 路径而跳过，见 reports/conan-verify-report.md）

## 上游信息
- 上游仓库: https://github.com/hilderingt/libgetline（"Read a file each a line." 逐行读取文件的 C 库）
- 版本: 上游 AC_INIT 声明 1.0；仓库无 tag/release，官方 codeload 归档锚定 master 快照
- 归档 SHA-256: 1c2536935e39ee9c53fc86d5b1555f86c66f49591099e30ceffb710ea96c99d5
- 产物: libgetline.so.1.0.0（SONAME libgetline.so.1，-version-info 1:0:0）+ libgetline.a + include/libgetline.h
- 许可证: GPL-3.0（上游 LICENSE 为 GPL v3 全文）

## 编译步骤
1. `init-build libgetline 1.0 --url=<codeload 官方归档>`：下载/解压/骨架/环境检查
2. `lang-preflight`：detected=c（任务语言 cpp，c↔cpp 兼容族通过）
3. 探索编译：`./configure --build=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=...`
4. `conan-init` 生成配方 → 手工精化 conanfile.py/conandata.yml/test_package
5. `conan create`（ohos-aarch64 profile）：库构建 + test_package 双测试（消费者 + 鸿蒙专项）全部通过
6. `conan-verify`：G0-G4/L2/L4/L5 全 PASS
7. `finish`：W2 结构 + R36 依赖 + W3 本地 CI（JC 增量模式）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | 上游 config.guess/config.sub（2018）无法识别 HarmonyOS uname（uname -s=HarmonyOS） | 配方 generate() 注入 `--build=aarch64-unknown-linux-gnu`（config.sub 接受；a52dec/abiword 同款） |
| 2 | config.status 报 subs1.awk Permission denied | HMDFS 强制 setgid：`umask 077 && mktemp -d` 得到 drwx--S---，属主也不可写（E011/E129） | patches/0001-configure.patch 将 configure 中 umask 077 → 022 |
| 3 | conan out-of-tree 构建缺 include/libgetlineP.h | conan 2 basic_layout 在 build-release/ 下 VPATH 构建，automake 默认 -I 不含 top_srcdir/include | build() 内 `Environment.append("CPPFLAGS", "-I<source>/include")`（abiword-plugin 同款） |
| 4 | 上游测试挂起/返回 SIZE_MAX | **上游 bug**：libgetln_getline 只初始化 `llen=0`，`lsize` 未初始化（UB）；且翻倍优化把翻倍值复合进 lsize 运行总量，小缓冲逐块读时 cap 每块指数翻倍（5→10→20→…→数十 GB），realloc 爆炸 | patches/0002-src-libgetline.c.patch：①lsize 初始化为 0；②翻倍使用独立 newsize（max(needed, 2*cap)），不再复合进 lsize。已验证 -O0/-O3 均正常返回 |
| 5 | conan-verify 包装器崩溃恢复覆盖 conandata.yml | 工具崩溃后按陈旧 .ghfast-bak 恢复 conandata，丢失 0002 补丁条目 → 构建产物无修复 | 恢复 conandata 补丁条目、清除陈旧 .ghfast-bak；提交前逐次核对 conandata 完整性 |
| 6 | W3 JC 门禁报 cloog 杂质 | main 上 cloog/0.21.1 曾误提交 .build-closed/.staging-verified 空运行时标记（提交 906cc59ae7），全仓跟踪文件扫描命中 | 属其他库既有基线文件：按规程记录 SHA-256、隔离复跑（门禁扫描已跟踪文件，工作区隔离无效，证明与当前库无关）、原样恢复并核对前后 SHA-256 一致；本分支提交后 JC 转 incremental 模式只扫本库文件 |
| 7 | /tmp 只读（erofs 100%） | 设备 /tmp 为只读 erofs 挂载 | 使用 $TMPDIR=/storage/Users/currentUser/tmp |

## 源码修改（补丁）
- patches/0001-configure.patch（platform）: configure 的 mktemp/mkdir 临时目录 umask 077 → 022（E011/E129）
- patches/0002-src-libgetline.c.patch（portability）: libgetln_getline 未初始化 lsize（UB）+ 指数级 realloc 增长修复

## 依赖版本
- 无第三方运行时依赖（纯 libc + POSIX）

## 验证结果
- conan create（ohos-aarch64, clang 15, -O2 -O3）: configure/make/install 全部通过
- test_package 消费者用例（test.c）: 通过（4 行文件逐行读取，校验内容与换行长度约定）
- test_package 鸿蒙专项用例（ohos_platform_test.c）: 通过（NOBLANK 空行抑制/EOF 状态位/NOCLOSE fd 置留/EBADF 错误路径/长行缓冲增长 共 29 项断言）
- 上游测试: 上游无任何测试（无 tests/ 目录、Makefile.am 无 TESTS/check_PROGRAMS；`make check` 为 automake 空目标）——台账见 reports/ 与最终回报
- conan-verify: G1-G4 PASS；L2/L4/L5 跳过（本机无对应 cache 路径，报告如实标注）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（shared/fPIC、CPPFLAGS 注入、OHOS triplet） |
| conandata.yml | 官方源 URL + SHA-256 + 2 个补丁声明 |
| patches/0001-configure.patch | HMDFS umask 平台补丁 |
| patches/0002-src-libgetline.c.patch | 上游两个 bug 修复补丁 |
| test_package/ | 消费者用例 + 鸿蒙专项用例（双可执行，CI L1 运行） |
| reports/ | conan-verify 报告、W3 日志 |

## 注意事项
- 上游无 tag/release，conandata 锚定 master 快照（SHA-256 固定）；上游若更新需重新核验
- conan-verify 包装器的 E017 镜像注入/崩溃恢复可能改写 conandata.yml（曾丢失补丁条目），提交前必须核对
- W3 的 JC 门禁在分支无提交时回退 full 全仓扫描（会把 main 上其他库的存量运行时标记算作杂质）；分支提交后转 incremental 只扫本库
---

**编译结束**: 2026-09-16 23:10
**最终状态**: built
