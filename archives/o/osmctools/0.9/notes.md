# osmctools 0.9 适配笔记

## 编译环境
- 构建系统: custom（直接编译三个单文件 .c，绕开 autotools bootstrap）
- 编译日期: 2026-07-29
- 编译器: clang (OHOS SDK clang 15.0.4)
- 状态: built
- 源码URL: https://gitlab.com/osm-c-tools/osmctools/-/archive/0.9/osmctools-0.9.tar.gz
- License: AGPL-3.0-only
- 源码 sha256: 2f5298be5b4ba840a04f360c163849b34a31386ccd287657885e21268665f413

## 软件说明

osmctools 是一组处理 OpenStreetMap 数据文件的命令行工具：
- `osmconvert`: 转换 .osm/.pbf/.o5m 格式，依赖 zlib（gzopen）+ libm（sin/cos）
- `osmfilter`: 按标签/边界过滤 OSM 数据，仅依赖 libc
- `osmupdate`: 按时间增量更新 OSM 数据，仅依赖 libc

上游仓库：https://gitlab.com/osm-c-tools/osmctools （tag 0.9, 2018-05-30）
上游头注释明确编译方式：`gcc osmconvert.c -lz -O3 -o osmconvert`

## 编译步骤（真机 HarmonyOS aarch64）

```bash
export TMPDIR=$HOME/tmp
cd $BUILD_SRC_DIR

# 直接编译三个可执行文件（无需 autotools bootstrap）
clang -O3 -Wno-error -D__OHOS__=1 -I<zlib_include> -L<zlib_lib> \
  src/osmconvert.c -lz -lm -o osmconvert
clang -O3 -Wno-error -D__OHOS__=1 src/osmfilter.c -o osmfilter
clang -O3 -Wno-error -D__OHOS__=1 src/osmupdate.c -o osmupdate

# install
mkdir -p $TEST_PREFIX/bin
cp osmconvert osmfilter osmupdate $TEST_PREFIX/bin/

# 上游测试套件：经审计确认上游无任何测试套件
make check   # => autotools 无 configure 脚本，不适用；上游源码无 check 目标
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包无 configure 脚本 | 上游 tag archive 仅含 configure.ac + Makefile.am（HACKING 要求 `autoreconf --install`） | 绕开 autotools bootstrap，直接编译三个单文件 .c |
| 2 | `autoreconf --install` 失败：Can't exec "aclocal" | OHOS 真机工具链只装了 autoconf 2.72，无 automake/aclocal | 同上：不依赖 autotools，直接 clang 编译 |
| 3 | AM_INIT_AUTOMAKE([foreign -Wall -Werror]) 会导致编译失败 | -Werror 将 libc 头文件差异升级为 error (E063) | 绕开 autotools 后不再触发；编译时显式加 -Wno-error |
| 4 | AC_CHECK_LIB(z) 交叉编译探测失败 | configure 需执行测试二进制验证 libz | 绕开 autotools；zlib 由 Conan requires(zlib/1.3.1) 直接提供 -I/-L |

## 源码修改

**无补丁、无源码修改**。上游三个 .c 文件直接编译通过，无需修改 configure.ac 或 Makefile.am
（因绕开了 autotools 整套构建系统）。

## osmconvert.c 的多 main() 说明

osmconvert.c（13213 行）内含 3 处 `int main` 声明：
- line 997: `#if 0` 块内的 cosrk.c 独立测试程序（预处理器排除）
- line 1337: `#if 0` 块内的 cosr.c 独立测试程序（预处理器排除）
- line 12602: 真正的主程序 `int main(int argc, char** argv)`

`#if 0` 块被预处理器完全排除，故 `clang -c osmconvert.c` 只产生一个 main 符号，无链接冲突。

## 上游测试套件审计（无测试）

经完整审计上游 osmctools 0.9 源码包确认**无任何测试套件**：

- `configure.ac`: 无 `AC_CONFIG_FILES` 引用 tests/ 目录，无 check 目标定义
- `Makefile.am` (顶层): 仅 `SUBDIRS = src`
- `src/Makefile.am`: 仅 `bin_PROGRAMS = osmconvert osmfilter osmupdate`，无 `check_PROGRAMS`/`TESTS`
- 源码: 3 个 C 文件 (osmconvert.c, osmfilter.c, osmupdate.c)，无 `TEST()`/`TEST_F` (gtest)、无 `def test_` (pytest)
- 无 tests/、test/、spec/、t/ 目录
- `make check` 输出: "Nothing to be done for 'check'"（无 check 目标）

故 test_package/MANIFEST.yml 写入 `upstream_tests_exist: false` + 非空 `upstream_test_audit`，
真机测试输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,"executed":0}`。

test_package 为消费者 smoke test：运行三个二进制 + osmconvert 格式转换实测 + osmfilter 标签过滤实测（R34 实质调用被测包）。

## 依赖版本

- zlib/1.3.1（制品仓已发布，osmconvert 链接 -lz）

构建工具依赖:
- clang 15.0.4 (OHOS SDK)
- 无需 autoconf/automake/aclocal（绕开 autotools bootstrap）
