# dawgdic 0.4.5 适配笔记

## 编译环境

- 构建系统: autotools（预生成的 configure + Makefile.in，autoconf 2.68）
- 编译日期: 2026-09-11
- 编译器: clang/clang++
- 状态: built（待 HarmonyOS 真机预检确认）

## 上游信息

- 原始上游: http://code.google.com/p/dawgdic/（已归档）
- 镜像: https://github.com/stil/dawgdic（code.google 自动导出，只读归档）
- 源码包: dawgdic_0.4.5.orig.tar.gz（Debian/Ubuntu 归档，md5 e6c792dbb4ca0e2d49f149819292d746）
- 许可证: BSD-3-Clause
- 依赖: 无（纯 C++，仅需标准库）

## 产物形态

- 头文件库: 23 个头文件安装到 `include/dawgdic/`，无编译期 lib
- 工具: `dawgdic-build`、`dawgdic-find` 安装到 `bin/`
- 配方 `package_type` 取 header-library（头文件是主体，无编译期 lib，Conan 2 要求 library 必须声明 shared 选项；settings 保留保证按架构区分工具产物），`cpp_info.libs = []`，`bindirs = ["bin"]`

## 上游测试清点

`test/Makefile.am` 注册 4 个 Automake TESTS，`make check` 依次执行：

| # | 测试 | 内容 |
|---|------|------|
| 1 | dawg-builder-test.sh | 运行 dawg-builder-test 二进制（DawgBuilder 插入/Finish、Dictionary 构建与 Contains 断言） |
| 2 | dictionary-test.sh | dawgdic-build 建词典 + dawgdic-find 查询，与 dictionary-answer 比对 |
| 3 | completer-test.sh | `-g` 向导词典构建 + 补全输出，与 completer-answer 比对 |
| 4 | ranked-completer-test.sh | `-r` 排序词典构建 + 输出比对 + ranked-completer-test 随机键值测试 |

配方 `build()` 末尾完整执行 `make check`，不修改、不删减上游测试。

## test_package 设计

- `test_dawgdic.cpp`：消费者视角调用公开 API（DawgBuilder 插入/去重/Finish、DictionaryBuilder 构建、Contains/Find 含边界、GuideBuilder 构建、Follow 走前缀、Completer 枚举 "ap" 前缀），共 12 个 check。
- `test_tools.sh`：打包后的 dawgdic-build/dawgdic-find 普通 + `-g` 向导两条回环，与内嵌期望输出比对，共 2 个 check。
- 合计 14 个断言。

`test_tools.sh` 期望输出推导自 `src/dawgdic-find.cc` 的 `FindPrefixKeys`/`CompleteKeys` 打印格式（`line: key = value;` / `line: key = value ...`），与上游 `test/dictionary-answer`、`test/completer-answer` 同格式。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 本机无法直连 deb.debian.org（SSL EOF） | 本机出口网络限制 | 改用 curl 经镜像站下载同一 orig 包，md5 与 Ubuntu 页面一致，确认真实 sha256 |
| 2 | configure.ac 未使用 AC_CANONICAL_HOST | 老项目（2012），无需 host 三元组 | 无需 config.guess/config.sub 补丁，直接 configure |
| 3 | 真机 make check 1/4 失败：dawg-builder-test.sh 报 `.../b/test/dawg-builder-test: inaccessible or not found`，而二进制实际在 `.../b/build-release/test/` | 上游 dawg-builder-test.sh 用裸 `./dawg-builder-test`，异地构建时 cwd 落在源码测试目录则找不到二进制；另两组 shell 测试因走 TOP_BUILDDIR 未受影响 | 配方内程序化补测试脚本二进制查找（优先 ./，缺失则用 $TOP_BUILDDIR/test/），仅改查找路径、不改断言；同时 make check 改走尊重 TMPDIR 的 bash（SHELL=bash）以应对只读 /tmp |

| 4 | 真机预检 incomplete：conan 缓存命中（`Already installed!`）跳过 build()，`HMBS_UPSTREAM_TEST_RESULT` 缺失 | header-library 二进制跨 RREV 复用，配方只在 build() 输出上游证据；test_package 每次都跑却只输出 TEST_PACKAGE 标记 | build() 写 `upstream_test_result.json` 并打包到 `res/`；test_package 每次重发该文件，缺失（旧缓存）时从 conandata 同源下载源码做 in-source `make check` 实跑并解析 Automake 计数（含 fixture 非空证伪），不断言删减 |

## 验证结果

待 HMBS 真机预检（conan create + make check + test_package）回填。

## 注意事项

- `DawgBuilder::Insert` 要求按键排序插入，测试词典保持有序。
- `test_tools.sh` 使用 `mktemp -d` + trap 清理，不污染工作区。
