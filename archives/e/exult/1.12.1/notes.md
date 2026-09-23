# exult 1.12.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-09
- 目标平台: HarmonyOS PC arm64 (`aarch64-linux-ohos`)
- 编译器: clang/clang++ 15
- 状态: built（本地 Conan create 与 test_package 通过，待 CI 发布）

## 源码与配置
- 官方源码 URL: `https://github.com/exult/exult/archive/refs/tags/v1.12.1.tar.gz`
- SHA256: `5e5113e31dd8010b8dfd00b6b08f76681dc1e88254d357c92f15c202f7ed7e1f`
- 配置选项:
  - `--disable-mt32emu`
  - `--disable-fluidsynth`
  - `--disable-android-apk`
  - `--build=aarch64-linux-ohos`
  - `--host=aarch64-linux-ohos`
- Exult 上游源码包不携带生成后的 `configure`；配方使用 Autoconf/Automake/Libtool 和 Autoconf Archive 宏在构建目录中执行 autoreconf。
- SDL2 使用 `<SDL.h>`，配方通过 Conan toolchain 增加 `include/SDL2` 搜索路径。

## 依赖
- sdl2/2.30.10
- libpng/1.6.58
- zlib/1.3.1.1
- libvorbis/1.3.7
- libogg/1.3.6
- 构建依赖: autoconf/2.72、automake/1.18、libtool/2.5.4、autoconf-archive/2024.10.16

## 测试用例对比

| 测试类别 | 用例 | 命令 | 结果 |
|---|---:|---|---|
| 上游测试 | 0 个注册测试用例 | 无 `tests/`、`TESTS` 或 `check_PROGRAMS`；仅执行并记录 `make check` 递归构建检查 | 不计入测试用例 |
| 上游构建检查 | 1 个递归检查目标 | `make check` | 通过 |
| 适配补充消费者测试 | 3 个可执行文件 smoke 检查 | `exult --version`、`expack --help`、`ipack --help` | 通过 |
| 消费者测试合计 | 3 个命令断言 | `sh test.sh` | 通过 |

上游 `Makefile.am` 未声明独立 `TESTS` 或 `check_PROGRAMS`；`make check` 仍按上游递归目标执行并成功完成。适配后新增的消费者测试实际调用并校验 `exult`、`expack`、`ipack` 三个安装产物。

## 验证结果

```text
Autotools configure: PASS
aarch64-linux-ohos 编译: PASS
上游 make check: PASS
Conan create: PASS
安装产物: exult, expack, ipack 及 Exult 数据/文档文件
消费者 test_package: PASS
消费者输出: consumer smoke test passed: exult, expack, and ipack respond
```

## 适配说明

1. 使用 Conan `AutotoolsDeps` 和 `PkgConfigDeps` 注入依赖。
2. 为 SDL2 增加 `-I<SDL2 package>/include/SDL2`，兼容 Exult 使用的 `<SDL.h>` 包含方式。
3. 显式声明 `libogg/1.3.6`，确保消费者运行时获得 Vorbis 的传递依赖。
4. `package_info()` 导出 `bin` 和依赖库目录，保证消费者测试可直接运行所有命令行工具。
5. 通过 `commands.json` 声明 `exult`、`expack`、`ipack`。
---

**编译结束**: 2026-09-09 23:42
**最终状态**: built
