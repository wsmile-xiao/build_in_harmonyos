# pixelmatch-cpp 0.10.0 适配笔记

## 编译环境
- 构建系统: gyp (生成 makefile，header-only 库)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. `init-build`：官方 tag `v0.10.0` 源码下载（GitHub 官方 URL，SHA-256=f93365a21f4d25813621cab993116212ee74ee078871a5c7db3a6ae8a9f28d28），解压到
   `$TMPDIR/builds/pixelmatch-cpp-0.10.0.work`。
2. 上游 `make test` 生成 build 依赖 gyp（Python 2 语法，环境仅 Python 3），改为按 pixelmatch.gyp 的
   等价编译参数直接编译上游测试：
   `clang++ -std=c++11 -Wall -Wextra -Wshadow -fno-rtti -fexceptions -g -O0 -I include test/test.cpp -o build_test`
3. 运行 `./build_test`：4 个 diffTest 用例全部通过（exit 0）。
4. conan-init 生成 header-library 配方 + conan-verify 门禁验证；finish W3 conan create 干净构建。

## 上游测试枚举台账（source_declared_total=4，全部运行通过）

| 入口 | 分类 | 是否独立上游用例 | 是否运行 | 结果/原因 |
|------|------|-----------------|---------|-----------|
| test/test.cpp 中 main() 内 4 个 diffTest(...) 调用（1a/1b、2a/2b、3a/3b、4a/4b） | 用户测试源中的独立用例（各自独立 fixture 对 + 期望 mismatch 数：143/12439/212/36089） | ✅ 是（4 个独立用例） | ✅ 全部运行 | 全部通过，exit 0（assert 全部成立） |
| test/convert_tests.js | fixture 转换脚本（PNG→RGBA，node+pngjs） | ❌ 否（数据预处理脚本，非测试用例） | 不需要 | 归档自带 .rgba 数据，无需转换 |
| test/fixtures/*.png / *.rgba | 测试数据（4 组图片对 + 期望 diff） | ❌ 否（数据） | — | 全部随源码归档 |
| deps/gyp/ | 上游构建工具（Python 2 时代 gyp） | ❌ 否（构建工具） | — | 环境无 Python 2，已按等价编译参数直接编译 |
| pixelmatch.gyp | 构建配置 | ❌ 否（配置） | — | — |
| Makefile / .travis.yml | 构建/CI 配置 | ❌ 否（配置） | — | — |

- 统计口径：全目录枚举，用户测试源 = test/test.cpp。
- 全量通过率：4/4 = 100%（无未运行/不可运行/硬阻塞项）。
- 独立用例判定：test.cpp 中每个 diffTest 调用是独立的图片对比用例（不同 fixture、不同预期 mismatch），
  共 4 个；无 SECTION/宏前缀/框架内部宏；无 gtest/catch 框架，使用 assert + main() 直接驱动。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make test` 失败 `env: exec python: No such file or directory` | deps/run_gyp shebang 用 `python`，环境仅 python3 | PATH 前缀提供 `python` → python3 符号链接 |
| 2 | gyp `SyntaxError: Missing parentheses in call to 'print'` | 上游 gyp 为 Python 2 时代代码，环境 Python 3.12 | 不依赖 gyp 生成器，按 pixelmatch.gyp 等价编译参数直接编译测试 |
| 3 | GitHub 直连 TCP 超时 | 网络到 github.com 直连不可达 | 经环境可用镜像通道下载官方 tag tarball，SHA-256 核验一致；配方 URL 保持官方 HTTPS |

## 源码修改

无（header-only 库，测试原样编译运行通过；配方构建期无补丁）。

## 依赖版本

- 无运行时依赖（header-only，C++11 标准库即可）
- 测试构建：clang 15.0.4（gyp cflags_cc 等价参数）

## 验证结果

```bash
# 上游测试（等价编译参数，与 pixelmatch.gyp cflags_cc 一致）
clang++ -std=c++11 -Wall -Wextra -Wshadow -fno-rtti -fexceptions -g -O0 -I include test/test.cpp -o build_test
./build_test   # 输出 4 行 comparing...，exit 0
```

- 上游用例通过率：4/4 (100%)
- 构建产物：header-only（include/mapbox/pixelmatch.hpp），无二进制库；不产出 CLI 可执行文件 → 不需要 commands.json（R38 库类型）

## 注意事项

- 库为 header-only，conanfile.py 用 package_type=header-library；test_package 用真实 API 调用验证。
- 禁止把上游 gyp 工具链问题当作平台阻塞：测试已按等价参数编译运行通过。
---

**编译结束**: 2026-09-21 00:25
**最终状态**: built
