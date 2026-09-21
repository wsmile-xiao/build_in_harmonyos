# libabw 0.1.3 适配笔记

## 编译环境

- 构建系统: autotools（上游 configure 2.71 生成；设备 autoconf 2.73 / automake 1.18.1 / pkg-config 0.29.2 / CMake 4.1.2）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin）
- 状态: published（conan-verify G0-G4 + L2/L4/L5 全过）

## 编译步骤

conan create（ohos-aarch64 profile）：

1. generate(): AutotoolsToolchain 显式 `--host=aarch64-unknown-linux-musl --build=aarch64-unknown-linux-gnu`
   （E007 变体：上游 config.guess/sub 过老，显式三元组跳过 guess；host≠build 进入交叉
   模式，跳过 "cannot run C compiled programs" 试跑）；AutotoolsDeps 聚合依赖 include；
   PKG_CONFIG_PATH 指向依赖 pc 目录 + REVENGE/LIBXML/ZLIB 显式 CFLAGS/LIBS 双保险；
   `--disable-tools --disable-fuzzers --disable-docs --disable-werror`（tools/fuzzers 会
   额外硬要求 librevenge-generators/stream）
2. build(): configure（CONFIG_SHELL 命令级路由 /bin/sh）+ make -j1
3. test_package: 消费者测试 3 项断言真机执行（见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 working directory cannot be determined | profile buildenv 的 CONFIG_SHELL/SHELL 指向 hnp bash，HMDFS 目录下 getcwd 必挂（E386/经验汇总 12.38①）；Environment 与 os.environ 声明均被 profile buildenv 压制，仅命令级路由有效 | build() 内包装 self.run，为 configure 前缀 `env -u CONFIG_SHELL -u SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh` |
| 2 | configure 报 cannot guess build type | 上游 tarball 的 config.guess/sub 为 2021 版，config.sub 不识别 ohos 三元组 | 显式传 config.sub 认可的 musl/gnu 三元组；libabw configure.ac 对 host 无分支逻辑（仅 AC_CANONICAL_HOST 记录） |
| 3 | config.status 报 can't create ./confXXXXXX/subs1.awk: Permission denied | configure 内 `(umask 077 && mktemp/mkdir)` 在 HMDFS 产出不可写目录（E011/经验汇总 §5.3） | 补丁 0001-configure-umask-hmdfs.patch 移除 2 处 umask 077 前缀（受控方案，保留真实临时目录创建） |
| 4 | make 链接报 '//lib/librevenge-0.0.la' is not a valid libtool archive | librevenge 制品包内 .la 的 libdir='//lib' 已损坏；AutotoolsDeps 注入的 -lrevenge-* 在 libtool 解析 .la 依赖链时失败 | build() 内删除 librevenge 本地缓存副本中的坏 .la；REVENGE/ZLIB 以静态库绝对路径链接（libtool 按普通文件输入，绕开 .la 解析） |
| 5 | 消费者测试编译报 librevenge/librevenge.h file not found | librevenge 制品包（旧配方发布）cpp_info 缺 includedirs，消费者 CMake target 接口不完整（CMakeDeps 生成的 librevenge_INCLUDE_DIRS_RELEASE 为空） | test_package CMakeLists 用 CMakeDeps 数据变量（librevenge_PACKAGE_FOLDER_RELEASE 等）显式补 include/link 路径 |

## 源码修改

无源码修改。补丁 1 个（配置脚本层）：

- patches/0001-configure-umask-hmdfs.patch：configure 内 2 处 `(umask 077 && mktemp/mkdir)`
  移除 umask 077 前缀（E011 受控方案，见经验汇总 §5.3）

## 依赖版本

- librevenge/0.0.5（静态库；包内 .la 损坏与 cpp_info 缺 includedirs 见问题 #4/#5）
- libxml2/2.15.3（共享库）
- zlib/1.3.1（静态）
- boost/1.90.0.3（header-only：algorithm/string、optional、spirit/qi；与 librevenge 依赖一致，1.91.0 为精简版缺头文件）

## 上游测试清点（R51）

- 上游无任何测试：源码树 src/ 仅 lib/conv/fuzz；Makefile.am 无 check_PROGRAMS/TESTS，
  无 enable_testing/add_test。N_static = 0。

## 验证结果

- conan create + conan-verify：PASS（G0/G1/G2/G3/G4 + L2/L4/L5）
- 消费者测试（真机）：test_libabw 3 项断言 3/3 通过——
  isFileFormatSupported(.abw XML) == true；parse(.abw XML) == true；提取文本含载荷串
  "Hello HarmonyOS libabw"（checks=3 failures=0）

## 路径 B 判断（GLM-58，2026-09-19）

判断：不走路径 B，按纯路径 A 交付。依据：①五个坑的修复均为既有经验条目（E386/
12.38①、E007 变体、E011/§5.3）在单库内的直接应用；"制品包 .la 损坏 / cpp_info 缺
includedirs"属上游制品质量问题而非可跨仓库复用的适配知识，已在登记表与汇报中留痕；
②消费者测试刻画的是上游公开 API 的常规语义，非 OHOS 平台特有问题；③无查重后的新
知识增量。
---

**编译结束**: 2026-09-19 03:44
**最终状态**: built
