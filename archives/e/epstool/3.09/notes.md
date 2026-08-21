# epstool 3.09 适配笔记

## 编译环境
- 构建系统: makefile (自定义makefile，无configure脚本)
- 编译日期: 2026-08-21
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built (待conan-verify确认published)

## 源码特性
epstool 是纯 makefile 项目，**没有 configure 脚本、没有 config.guess**。
- 顶层 makefile include src/unixcom.mak 和 src/common.mak
- unixcom.mak 硬编码: CC=gcc, CLINK=gcc, LINK=gcc, CCAUX=gcc
- CDEFS=-DX11 -DUNIX -DNONAG (X11只是预处理宏，不链接X11库)
- LIBPNGCFLAGS/GTKCFLAGS/XINCLUDE 默认空，无外部库依赖
- EPSTOOL_VERSION=3.09 在 common.mak 定义
- 编译产物: bin/epstool (命令行工具，非库)
- install 目标用 prefix 变量: EPSTOOL_BASE=$(prefix)$(EPSTOOL_ROOT)

## 编译步骤

```bash
source .build-context-epstool-3.09
cd $BUILD_SRC_DIR

# 覆盖gcc→clang，用CFLAGS=-fPIC -O2
make -f makefile CC=clang CLINK=clang LINK=clang CCAUX=clang \
     CFLAGS="-fPIC -O2" -j1

# 验证产物
file bin/epstool
bin/epstool --help 2>&1 | head -5

# staging安装 (prefix指向staging，EPSTOOL_ROOT置空)
make -f makefile install prefix=$TEST_PREFIX EPSTOOL_ROOT=
ls -la $TEST_PREFIX/bin/epstool
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build标记为autotools但实际是makefile | epstool无configure脚本 | conanfile.py改为makefile构建方式，build()直接调make |
| 2 | makefile硬编码CC=gcc | unixcom.mak中CC=gcc | 通过make变量覆盖: CC=clang CLINK=clang LINK=clang CCAUX=clang |
| 3 | install时DESTDIR不生效 | makefile用prefix+EPSTOOL_ROOT拼接路径，非DESTDIR | 传prefix=<pkgdir> EPSTOOL_ROOT=空字符串 |
| 4 | staging安装的bin/epstool无法执行 | OHOS安全策略(未签名ELF) | 这是预期行为(R7)，CI流水线sign.sh处理签名 |
| 5 | clang产生-Wconstant-logical-operand等警告 | 上游cimg.c用&&代替&(位运算) | 警告不影响编译，无需修复 |

## 源码修改

无源码修改。epstool编译通过无需补丁。

## 依赖版本

无外部依赖。epstool是自包含的命令行工具。

## 验证结果

```bash
$ file bin/epstool
bin/epstool: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ bin/epstool --help 2>&1 | head -5
epstool 3.09 2015-03-13
Copyright 1995-2015 Ghostgum Software Pty Ltd
Usage: epstool command [options] inputfile outputfile
```

## 上游测试用例

上游提供两类测试机制，均无法完整运行：

| 测试机制 | 源码位置 | 可执行性 | 原因 |
|----------|----------|----------|------|
| `make epstest` | `src/epstest.c`（common.mak:205引用） | ❌ 不可执行 | src/epstest.c 在 release tarball 中缺失，Debian打包也未补充 |
| `--test-eps` 命令 | `epstool.c:2237` epstool_test() | ⚠️ 受阻 | 依赖 Ghostscript（gs未安装），非epstool缺陷 |

### 可执行功能测试结果

用最小 EPS 测试文件对功能命令逐一验证（详见 reports/test-report.md）：

| 命令 | 结果 | 说明 |
|------|------|------|
| `--version` | ✅ PASS | 输出 "epstool 3.09 2015-03-13" |
| `--help` | ✅ PASS | 完整输出用法+命令列表 |
| `--dump` | ✅ PASS | DSC解析正确识别EPSF/BoundingBox/各结构段偏移 |
| `--copy` | ✅ PASS | 复制后文件内容完整保留 |
| `--extract-postscript` | ✅ PASS | 正确报告"not a DOS EPS file"（预期行为，纯文本EPS非DOS封装） |
| `--test-eps` | ⚠️ SKIP | 代码路径正确执行到调用gs，失败点在外部依赖缺失 |

### `--test-eps` 阻塞分析

epstool_test() 流程：临时PS文件创建 → 注入epswarn探针 → 调用gs解释 → 捕获EPSWARN输出 → 验证BoundingBox。
- 临时文件默认用 `/tmp`（app_temp_gfile，capp.c:618），设置 `TEMP` 环境变量可重定向
- 最终阻塞在 `exec_program("gs ...")` — gs 未安装（`gs --version` → not found）
- Ghostscript 归档为 built 状态但未发布到制品仓，属环境依赖限制

## 注意事项

- conanfile.py中build()通过self.conf.get()获取编译器路径(R33)，不裸用${CC}
- package_type="application"，无cpp_info.libs
- test_package使用test.sh运行epstool --help验证版本输出(R34)
- commands.json声明epstool命令行工具(R38)
- 上游epstest.c缺失，无法运行make epstest
- --test-eps依赖gs运行时，本环境gs未安装

---

**编译结束**: 2026-08-21 09:41
**上游测试**: 2026-08-21 运行6项功能测试，5项PASS/1项SKIP(缺gs)
**最终状态**: built
