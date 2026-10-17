# zmk 0.5.1 适配笔记

## 编译环境

- 构建系统: GNU Make
- 适配日期: 2026-09-24
- 平台: OpenHarmony / aarch64
- 上游主页: <https://github.com/zyga/zmk>

## 源码与产物

- 源码使用 Debian 官方的 `zmk_0.5.1.orig.tar.gz`，SHA256 已固定在 `conandata.yml`。
- `z.mk` 安装到 `include/z.mk`，各模块安装到 `include/zmk/`。
- 手册页和示例安装到 `share/man/man5/` 与 `share/doc/zmk/`。

## 上游测试

- 上游提供 `make check`。测试入口由 19 个 `tests/**/Test.mk` 组成。
- 实测：`make check` 在真机上驱动全部 19 个 `Test.mk` 套件，输出 969 条 `GREP` 规则断言，全部通过，0 失败。
- 日志中出现的 3 条 `GREP: failed to match` 来自 `tests/Tarball.Src` 中的否定断言 `! GREP -qFx ...`，正是该断言通过时的输出路径，不是失败。
- recipe 的 `build()` 中直接执行上游 `make all` 与 `make check`，不删除或改写上游测试。

## 上游测试的环境隔离

- 上游 `make check` 的 19 个套件都是基于 `make --dry-run` 的规则级断言：把 z.mk 实际展开出的命令行与上游写死的
  规范文本（`CC=cc`，且不带额外编译/链接选项）逐字比较。
- Conan 在 `build()` 中会导出 `CC`、`CFLAGS`、`CPPFLAGS`、`LDFLAGS` 等构建环境变量，GNU Make 把它们当作环境变量
  导入并覆盖 zmk 的内建默认值，使 dry-run 输出变成 `clang -fPIC -O2 -I... -MMD -c -o ...`，与上游期望文本不一致，
  表现为 `GREP: failed to match` 与 `GNUmakefile:111: check-examples-hello-c Error 2`。
- 处理方式：`make all` 仍使用 Conan 注入的交叉工具链；`make check` 则在同一个 shell 内先 `unset` 这些工具链变量，
  让上游断言看到中立的宿主机默认值（`cc`/`c++`，无额外选项）。
- 该处理仅改变测试执行环境，未修改任何上游测试文件、断言或通过条件。

## 消费者测试

- 安装后的 `conan test` 创建一个独立的小型 C 项目。
- 项目通过 `include $(ZMK.Path)/z.mk` 引入已安装库，使用 `ZMK.Expand,Program` 构建并运行 `hello`。

## 源码修改

### `0001-ohos-elf-kernel.patch`

- 修改文件: `zmk/OS.mk`。
- 原因: 鸿蒙真机的 `uname -s` 返回 `HarmonyOS`，上游只把 Linux 等内核识别为 ELF，导致安装后的 Makefile 库在消费者项目中直接报 `unsupported operating system kernel HarmonyOS`。
- 修改内容: 将 `HarmonyOS` 加入 ELF 内核列表；鸿蒙用户态使用 ELF 可执行文件，编译器探测结果与 Linux 一致。未修改任何上游测试文件或断言。

### `0003-ohos-make-default-cxx.patch`

- 修改文件: `zmk/Toolchain.mk`、`zmk/toolchain.GCC.mk`。
- 原因: 鸿蒙镜像内置的 GNU Make 4.4.1 将 `CXX` 默认值编译成了构建机路径 `/home/runner/work/ohos-make/.../clang++`，设备上不存在该路径；同时上游工具链测试要求在 `origin CXX=default` 时启用交叉编译器调试逻辑。
- 修改内容: 仅在检测到该内置坏路径时，把 `CXX` 规范化为设备提供的 `c++`，并保留来源标记；交叉编译器判断把该标记视作默认工具链。未修改任何上游测试文件或断言。

## 注意事项

- 本包是可复用的 Makefile 构建脚本库，不生成运行库或可执行文件。
- 消费者需在 Makefile 中提供 `ZMK.Path`，或把包的 `include` 目录加入 `-I`。
