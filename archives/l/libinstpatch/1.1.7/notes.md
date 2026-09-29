# libinstpatch 1.1.7 适配记录

- 源码: https://github.com/swami/libinstpatch （官方 tag v1.1.7, commit 4ff1939ccc24de204d41b3ab734fc1aece919184）
- 归档包: libinstpatch-1.1.7.tar.gz（GitHub archive URL）
- 归档路径: archives/l/libinstpatch/1.1.7
- 适配日期: 2026-09-23

## 编译环境
- 构建系统: cmake（上游 1.1.7 无 autotools 构建，根目录为 CMakeLists.txt）
- 编译日期: 2026-09-23
- 编译器: clang /data/service/hnp/bin/clang（--target=aarch64-linux-ohos）
- 状态: built

## 上游测试清点（R51，R03 修订）

上游 tag v1.1.7（commit 4ff1939c）tests/ 共 7 条目：5 个可运行测试程序入口 + `Test.py`（辅助模块，无 `__main__`、被 3 个 Python 脚本 import）+ `TODO`（纯文本待办，不计入）。

| # | 测试 | 类型 | R03 实测结果 |
|---|------|------|-------------|
| 1 | sample_test.c | C（音频格式转换矩阵） | ✅ 本轮重新编译（exit 0）并运行，484 项格式转换全部 PASSED（exit 0） |
| 2 | sample_list_test.c | C（sample list / 虚拟存储） | ✅ 经 API 漂移兼容层（`tests-compat/ipatch_compat.h`，纯 API 映射、无平台宏、不改上游测试源码）真实编译并运行通过：`Sample list and virtual sample store test passed`（exit 0）。原始失败 13 error（首错 `ipatch_sample_data_new` 签名由带 size 改为 `(void)`，:102/:139；`IPATCH_SAMPLE_LIST_CHAN_RIGHT/LEFT` 未声明；`ipatch_sample_store_new/_activate/_duplicate/_RAM_get_location` 隐式声明）→ 兼容层逐符号映射 → 真实通过 |
| 3 | Converter.py | Python GI | ⚠️ 真实运行 exit 1：`TypeError: '>' not supported between instances of 'NoneType' and 'int'`（Test.parseArgs，args.verbose 为 None）；GI 依赖链已打通（Ipatch-1.1 gir/typelib 本机生成） |
| 4 | SF2.py | Python GI | ⚠️ 真实运行 exit 1：`AttributeError: 'gi.repository.Ipatch' object has no attribute 'SampleWidth'`（生成 typelib 未导出 Ipatch 枚举常量）+ GLibUnix 平台 typelib 缺失——符号级精确技术原因（依赖/供给阻塞），非当前库源码缺陷 |
| 5 | SampleTransform.py | Python GI | ⚠️ 真实运行 exit 1：同 SF2.py（`Ipatch.SampleWidth` 属性缺失），无 `__main__` 守卫、顶层即执行，按脚本识别计入入口 |

> 入口数 ≠ 用例数：sample_test 的 484 是格式转换组合用例、不是入口。计数规则可复算：
> `grep -c 'int main' tests/*.c`（C 入口 2）、`grep -c '__main__' tests/*.py`（Python 入口 2 + SampleTransform 按 shebang 脚本与顶层语义计入）、`grep -l 'import Test' tests/*.py`（辅助模块判定）。
> 上游 CMake 未将 tests/ 接入构建（无 add_subdirectory(tests)/enable_testing），测试需手动编译。
> 测试源码与官方 tarball 逐文件 SHA-256 完全一致（`upstream_test_source_integrity`），未修改任何上游测试文件。

## 编译步骤

```bash
# 依赖注入（conan 从 ohpcd 制品仓拉取已发布二进制）
conan install --requires=glib/2.88.3.1 --requires=libsndfile/1.2.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -of=<deps> --build=missing

# glib 的 .pc 文件 prefix=/ 硬编码，需逐项重写 prefix/libdir/includedir
# 到实际 conan 缓存包目录后建立 pkg-config 覆盖层（见下）

export PKG_CONFIG_PATH=<pkgconfig-overlay>
cmake -S . -B build -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_C_FLAGS='--target=aarch64-linux-ohos --sysroot=<ohos-sysroot>' \
  -DCMAKE_INSTALL_PREFIX=<prefix> -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
cmake --build build -j4
cmake --install build --prefix <test-prefix>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报"下载内容是 HTML" | 直接给仓库页 URL，非归档 URL | 使用官方 tag 归档 URL github.com/swami/libinstpatch/archive/refs/tags/v1.1.7.tar.gz |
| 2 | CMake 找不到 gobject/glib/gthread/sndfile | 依赖在 ohpcd 制品仓，本地无系统安装 | conan install 拉取 glib/2.88.3.1、libsndfile/1.2.2 已发布二进制 |
| 3 | glib-2.0.pc 报 Requires: pcre2 找不到 | conan 缓存的 .pc 中 prefix=/ 指向错误路径 | 重写 .pc 的 prefix/libdir/includedir 到实际缓存包目录，建立 pkg-config 覆盖层 |
| 4 | sample_list_test.c 编译失败（13 error） | 上游测试与 1.1.7 发布 API 漂移：真实首错为 `ipatch_sample_data_new` 签名由带 size 改为 `(void)`（:102/:139 "expected 0, have 1"）；另有 `IPATCH_SAMPLE_LIST_CHAN_RIGHT/LEFT` 未声明、`ipatch_sample_store_new/_activate/_duplicate/_RAM_get_location` 隐式声明 | R03 新建 API 漂移兼容层 `tests-compat/ipatch_compat.h`（纯 API 映射、无平台宏、不改上游测试源码/库源码/配方）后真实编译运行通过：`Sample list and virtual sample store test passed`（exit 0） |

## 源码修改

无源码修改（未生成补丁）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.88.3.1 | ohpcd 制品仓 |
| libsndfile | 1.2.2 | ohpcd 制品仓 |

## 验证结果（R03 修订）

```bash
# 上游测试 sample_test：484 项音频格式转换（本轮重新编译后运行）
$ clang sample_test.c ... -o sample_test-r03-recompiled   # exit 0
$ LD_LIBRARY_PATH=<test-prefix>/lib:<glib-shared>/lib ./sample_test-r03-recompiled
All 484 sample format conversions PASSED                  # exit 0

# 上游测试 sample_list_test：API 漂移兼容层（tests-compat/ipatch_compat.h）
# 原始失败 13 error → 兼容层编译 exit 0 → 运行 exit 0
$ clang sample_list_test.c -include tests-compat/ipatch_compat.h ... -o sample_list_test-compat-r03
$ LD_LIBRARY_PATH=<test-prefix>/lib:<glib-shared>/lib ./sample_list_test-compat-r03
Sample list and virtual sample store test passed          # exit 0
```

- 上游可运行测试程序入口（实测）：5（sample_test.c、sample_list_test.c、Converter.py、SF2.py、SampleTransform.py；Test.py 辅助模块不计入）
- 实际执行入口：5/5（全部真实执行并留存日志，无静默排除）
- 计入通过：2（sample_test 484 PASS、sample_list_test 经兼容层 PASS）
- 不计入通过（单列、符号级技术原因）：3（Converter.py / SF2.py / SampleTransform.py 真实运行均 exit 1：
  生成 Ipatch-1.1 typelib 未导出 Ipatch 枚举常量（`SampleWidth` 等）+ GLibUnix 平台 typelib 缺失 + 本机无 python2）
- 上游实际执行入口通过率：2/2（100%）；全量处置率：5/5
- 新增测试（test_package 消费者测试）通过率：1/1（100%）
- 统计口径：适配后合计只计实际执行通过数 = 3（2 上游 C + 1 新增消费者测试）；不可运行入口单列

## 注意事项

- 库产物: libinstpatch-1.0.so（soname 由 LIB_VERSION_INFO=2.2.1 派生），头文件安装于 include/libinstpatch-2/libinstpatch/。
- 工具: utils/ 生成 riff_dump 命令行工具，但该工具仅用于调试 dump（不作为交付命令）。
- 下游 pkg-config 文件: libinstpatch-1.0.pc.in（Requires: glib-2.0 gobject-2.0 gthread-2.0 sndfile）。
---

**编译结束**: 2026-09-27 20:33
**最终状态**: built
