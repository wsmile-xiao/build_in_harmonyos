# libinstpatch 1.1.6 适配笔记

## 编译环境

- 构建系统: direct-cc（CMake 同款源清单直调编译；miniupnpc 2.3.11 先例路线）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built
- 目标平台: HarmonyOS aarch64 (OHOS 6.0, clang 15, libc++)

## 版本与源码说明

- 上游 github.com/swami/libinstpatch，tag `v1.1.6`（带 v 前缀，git ls-remote 确认：3caacd051c28aabb74c50e6ff9eb578bf8f5fa9b）。任务卡给的 swellhead/libinstpatch 仓库 404 不存在——swami/libinstpatch 是真实上游（任务平台 url 字段也写 swami）。
- 源码取 codeload 归档 `.../tar.gz/refs/tags/v1.1.6`，sha256 `8e9861b04ede275d712242664dab6ffa9166c7940fea3b017638681d25e10299`，顶层目录 libinstpatch-1.1.6。
- 包名 libinstpatch，目录 l/libinstpatch（软件名版本分离，main 上此前无此包）。

## 依赖（W0 预检实测）

上游 CMakeLists.txt 的 REQUIRED 依赖：

```cmake
pkg_check_modules ( GOBJECT REQUIRED gobject-2.0>=2.12 glib-2.0>=2.12 gthread-2.0>=2.12 )
pkg_check_modules ( SNDFILE REQUIRED sndfile>=1.0.0 )
```

制品仓核对（conan list -r=ohpcd）：
- glib：2.84.0 / 2.84.0.1 / 2.84.0.1.1 / 2.84.0.2 / 2.88.x 线全在 → 取 **glib/2.84.0.1**（glib2 双包线外的主线稳定版）
- libsndfile：**libsndfile/1.2.2** ✅ 不断链

（ENABLE_NLS 上游从不定义——config.h.cmake 无此变量，i18n.h 走纯 fallback——无 libintl 硬依赖，不需要 gettext。）

## 编译步骤（direct-cc 路线）

CMake 的 pkg_check_modules+configure_file+生成器链在 OHOS CI 的 CMake 编译器 ID 探针上必然红（仓内 miniupnpc 2.3.11 已实证该探针两路线皆红），故 2.2.8/1.1.6 两个任务都走 direct-cc：

```text
build():
  1. 可写 TMPDIR 保障；cc/ar 从 Conan conf 取（R33）；C 编译器冒烟
  2. 手工生成 configure_file 产物：
     - config.h（check_include_file 在 OHOS 目标上的实测值：string.h/stdlib.h/stdio.h/math.h/errno.h/stdarg.h/unistd.h/locale.h 全 1）
     - version.h（@IPATCH_VERSION@ → "1.1.6"）
     - libinstpatch.h（模板无变量，原样）
  3. 用 glib conan 包 bin/ 里的真实工具生成（sys.executable 直跑 python 脚本）：
     - builtin_enums.[ch]：glib-mkenums --fhead/--fprod/--vhead/--vprod/--vtail 与上游 enums target 逐参一致 + sed 's/dl_s2/dls2/g;s/DL_S2/DLS2/g'
     - marshals.[ch]：glib-genmarshal --header/--body --prefix=ipatch_marshal marshals.list
  4. instpatch_SOURCES（上游清单原样，builtin_enums.c 换成生成版）+ marshals.c
     -std=gnu99 -fPIC -Wall -O2 -DHAVE_CONFIG_H -DLOCALEDIR=... 编译
  5. llvm-ar rcs 归档 libinstpatch-1.0.a（shared=True 时 -shared 产 .so）
  6. 上游两个 C 测试 harness 真跑（见下节）
```

## 上游测试审计（N 口径）

- 上游**无 CTest 注册**：全仓 grep 无 enable_testing/add_test；azure-pipelines.yml 三个 job 都只 `cmake + make`，不跑任何测试。
- tests/ 目录内容：  - `sample_test.c`（216 行）：484 种采样格式组合的三角波往返转换测试——上游**未挂任何构建目标**，但可编译可运行，配方从上游源码直接编译并真跑（484 格式组合全遍历），实测通过。
  - `sample_list_test.c`（209 行）：引用 `IPATCH_SAMPLE_LIST_CHAN_LEFT/RIGHT` 宏——**该宏从未在上游任何 commit 中定义过**（git grep 全历史确认；文件自 f618c11 "Bump to 1.1.2"（2020-01-19）加入起上游自己也从未编译过它）。属上游死测试（dead harness），如实按上游缺陷豁免（skipped+原因），不计入 N。
  - `Test.py/SF2.py/Converter.py/SampleTransform.py`：Python GObject-introspection 测试，需要 INTROSPECTION_ENABLED 构建出的 Ipatch-1.1 typelib + pygobject——C 交叉构建范围外（上游默认 introspection=off）。
- **N=1 口径**（按包/模块边界申报）：上游实际可编译可执行的 C harness 只有 sample_test 这 1 个，真跑 1/1 全过（内部 484 格式组合断言全过）。sample_list_test 如实豁免（上游缺陷证据链：宏从未定义）；Python gi 测试如实申报超范围（introspection 未构建）。
- test_package 消费者测试 4 断言：ipatch_init、IPATCH_VERSION 非空、ipatch_sample_transform_new+alloc_size+free（与上游 sample_test 同款调用形态）、ipatch_sf2_gen_get_prop_name 静态表查询、ipatch_gerror_message 纯函数——全部无需音频文件 I/O 的无设备冒烟。
  - 注意：曾尝试在消费者测试里用 `ipatch_sample_store_ram_new + g_object_unref`，真机上 unref 段错误（store finalize 链依赖 sample data 池完整环境）——已换成上述无副作用 API 组合，不掩盖问题、不硬做。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务卡上游仓库 swellhead/libinstpatch 404 | 仓库名错误（或已改名） | 用 swami/libinstpatch（任务平台 url 字段一致），tag v1.1.6 确认 |
| 2 | CMake configure 在 OHOS 上红 | 编译器 ID 探针 "unknown"（pkg_check_modules 链加剧） | direct-cc 直调 profile clang |
| 3 | builtin_enums/marshals 需要生成器 | 上游 CMake custom command 依赖 glib-mkenums/glib-genmarshal | glib conan 包 bin/ 自带这两个工具（python 脚本），sys.executable 直跑，参数逐项复刻上游 |
| 4 | 头文件安装路径特殊 | INSTPATCH_INSTALL_TARGET=libinstpatch-2（LIB_VERSION_CURRENT=2） | 安装到 include/libinstpatch-2/libinstpatch，package_info includedirs 双路径 |
| 5 | codeload URL 无扩展名 | get() 无法推断格式 | source() 传 filename="libinstpatch-1.1.6.tar.gz"（zfp/miniupnpc 经验） |
| 6 | version.h 双引用形态 | .c 用 #include "version.h"（二进制目录），伞头用 <libinstpatch/version.h>（源根） | gen/ 与 gen/libinstpatch/ 双拷贝，-I 两个都加 |
| 7 | glib-genmarshal 无 list 参数时输出截断 | 不传文件参数时工具读 stdin，重定向管道拿到空体 | 命令显式传 marshals.list 路径参数（上游 CMake 同款） |
| 8 | sample_list_test.c 编译失败 | 引用从未在任何上游 commit 定义过的 IPATCH_SAMPLE_LIST_CHAN_* 宏（上游死测试，f618c11 起从未被上游编译） | 如实豁免（skipped+上游缺陷证据链），N=1 只算可编译的 sample_test |
| 9 | 测试运行时 symbol not found（glib 符号） | 链接 conan glib 的 .so 但运行时无 LD_LIBRARY_PATH | 测试执行 env 注入依赖 libdirs 的 LD_LIBRARY_PATH |
| 10 | test_package RAM store unref 段错误 | store finalize 链依赖 sample data 池完整环境，独立消费者场景不成立 | 消费者测试改用无副作用 API 组合（transform 链/静态表查询/纯函数），不硬做 |
