# dex 1.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，非 autotools)
- 编译日期: 2026-06-29
- 编译器: clang 15 (/data/service/hnp/bin/clang)
- 目标架构: aarch64 (armv8)
- 状态: built

## 编译步骤

dex v1.0 是纯 Makefile 项目，无 configure 脚本。编译步骤如下：

```bash
# 设置环境变量
export CPATH=/storage/Users/currentUser/usr/local/include
export LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib

# 编译
cd $BUILD_SRC_DIR
make prefix=/usr/local CC=clang HOST_CC=clang -j2

# 安装到测试目录
make install prefix=/usr/local DESTDIR=$TEST_PREFIX CC=clang HOST_CC=clang

# 执行测试
make test CC=clang HOST_CC=clang
```

完整命令输出见: `reports/build-test-report.md`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cc` command not found | 系统只有 clang，无 cc/gcc 符号链接 | make 时传 CC=clang HOST_CC=clang |
| 2 | ncurses 头文件找不到 | ncurses 安装在非标准路径 | 设置 CPATH=/storage/Users/currentUser/usr/local/include |
| 3 | -lncurses 链接失败 | 有 libncursesw.a 但链接器找 libcurses.a | 创建符号链接: libcurses.a → libncursesw.a |
| 4 | Conan save_script("conanbuild") 导致 SIGSEGV | Conan 2.x 自带 conanbuild.sh，名称冲突致无限递归 | 改名为 "dex_build_env" |
| 5 | Conan build() 在错误目录运行 | Conan 2.x 分离 build_folder 和 source_folder | build() 中 cd self.source_folder |
| 6 | G4 产物检查失败 | prefix=/usr/local 导致 bin 在 usr/local/bin/ 下 | package() 改用 prefix=/ 使 bin/ 在包根目录 |
| 7 | test_package Conan 2.x API 不兼容 | Conan 2.x 改变了 test_package API | 重写为直接定位二进制并验证 ELF |
| 8 | L2 smoke test 失败 | dex 是全屏终端编辑器需 TTY，无 --version/--help | 预期行为，终端应用无法在非交互环境运行 |
| 9 | Conan 源码下载超时 | github.com 网络不通 | 使用本地 file:// URL 下载预存 tar.gz |

## 源码修改

无源码修改。所有编译参数通过 make 命令行变量传递。

## 依赖版本

- ncurses (libncursesw.a，系统预装静态库)
- clang 15 (/data/service/hnp/bin/clang)
- libc (系统库，动态链接)

## 验证结果

### 手动编译测试

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 编译 | make prefix=/usr/local CC=clang HOST_CC=clang -j2 | 0 | ✅ 成功 |
| 安装 | make install prefix=/usr/local DESTDIR=$TEST_PREFIX | 0 | ✅ 成功 |
| 测试 | make test CC=clang HOST_CC=clang | 0 | ✅ 成功 |

完整输出见: `reports/build-test-report.md` 第2-5节

### Conan 构建测试

| 步骤 | 结果 |
|------|------|
| conan create | ✅ 成功 (exit 0) |
| test_package | ✅ 通过 ("test dex 1.0: OK") |

完整输出见: `reports/conan-create.log`

### conan-verify 8道门禁

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ✅ PASS | 预构建风险评估通过 |
| G1 | ✅ PASS | 配方完整性检查通过 |
| G2 | ✅ PASS | conan create 成功 |
| G3 | ✅ PASS | 静态链接验证通过 (仅依赖 libc.so) |
| G4 | ✅ PASS | 产物完整性检查通过 (bin/ 有1个文件) |
| L2 | ❌ FAIL | dex 需 TTY，--version/--help 不支持 (预期行为) |
| L4 | ✅ PASS | 安全扫描通过 (PIE=enabled, RELRO=full) |
| L5 | ✅ PASS | 产物基线对比通过 (35个文件) |

完整输出见: `reports/conan-verify-output.log` 和 `reports/conan-verify-report.md`

## 交付物

| 路径 | 说明 |
|------|------|
| bin/dex | 主可执行文件 (867K, ELF 64-bit arm64) |
| share/dex/binding/default | 按键绑定配置 |
| share/dex/color/darkgray | 颜色方案 |
| share/dex/color/light | 颜色方案 |
| share/dex/color/light256 | 颜色方案 |
| share/dex/compiler/gcc | 编译器集成 |
| share/dex/compiler/go | 编译器集成 |
| share/dex/syntax/* | 语法高亮 (20+种语言) |
| share/dex/filetype | 文件类型配置 |
| share/dex/rc | 默认配置 |
| share/man/man1/dex.1 | man 手册页 |
| share/man/man7/dex-syntax.7 | 语法手册页 |

共 35 个文件。二进制仅动态依赖 libc.so，ncurses 已静态链接。

## 注意事项

- dex 是终端全屏文本编辑器，L2 smoke test 因需 TTY 而失败，属预期行为
- 构建系统为纯 Makefile（conan-init 误检测为 autotools，已手动修正）
- 需创建 libcurses.a → libncursesw.a 符号链接（在 LIBRARY_PATH 路径中）
- PKGDATADIR 在编译时通过 -D 标志固化到二进制中
- 网络环境无法访问 github.com，Conan source() 使用本地 file:// URL
- conanfile.py 中 generate() 使用 save_script("dex_build_env") 避免与 Conan 2.x 内置 conanbuild.sh 冲突
---

**编译结束**: 2026-06-29 17:10
**最终状态**: built
