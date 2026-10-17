# DRAFT-adacgi-ada-source-library-conan-pattern - Ada 源码库在 HarmonyOS 的 Conan 适配模式

> **Contributor**: codex | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-17
> **Source event**: adacgi 1.6 HarmonyOS PC adaptation, upstream David A. Wheeler AdaCGI, shadow CI isolated job `adacgi-1.6-shadow-20260917-092524`

## 知识类型与提升边界

本条目是路径 B/B 类知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和评审决定。

## 适用场景

适用于同时满足以下条件的 Ada（或类似 GNAT 构建）库：

- 上游以 Ada 源码单元（`.ads`/`.adb`）分发，无预编译二进制、无 shared/static 之分；
- 构建工具链是 `gcc-ada`（GNAT），通过 `tool_requires` 引入；
- 消费者用 `gnatmake`/`gnatbind`/`gnatlink` 现场编译，而非链接一个现成 `.a`/`.so`；
- 目标是 OHOS aarch64 真机或隔离 shadow CI。

仓库知识库此前覆盖 C/C++/Rust/Go/Python/Perl 等，尚无 Ada 语言库的 Conan 配方模式。
adacgi 1.6 是第一个走通"源码分发 Ada 库 + gcc-ada 工具链 + 真机消费测试"闭环的实例。

## 问题模型

Ada 库的 Conan 化有三类容易误判的处理方式：

1. 套用 C/C++ 库的 `package_type="library"`，触发 Conan 2.x 的 `shared` 选项硬性要求；
2. 把 `.ads`/`.adb` 当成头文件塞进 `include/`，或伪造 `cpp_info.libs`，让下游以为存在预编译库；
3. 在 test_package 里用 `conanrun` 环境编译，却发现 `cannot locate file system.ads`。

## 推荐方法

### 1. 用 header-library 表达源码分发

`package_type = "header-library"` 最贴合"只有源文件、无编译产物"的语义，且不需要
`shared` 选项。`package_info()` 显式 `cpp_info.includedirs = ["adainclude"]`、
`cpp_info.libs = []`，把库单元暴露为搜索路径而非伪库。

### 2. GNAT 作为 tool_requires，而非 requires

`build_requirements()` 里 `self.tool_requires("gcc-ada/9.5.0")`。GNAT 是 build context
依赖，它的 `ADA_INCLUDE_PATH`/`ADA_OBJECTS_PATH`/`GCC_EXEC_PREFIX` 都进 `conanbuild`。

### 3. build() 编译库单元做源码验证

用 `gnatmake -q -gnat95 -c <unit>.adb` 只编译不链接，验证 `.ads`/`.adb` 语法语义；
`self.run(..., env=["conanbuild", "<binutils-env>"])`（见配套草稿
`DRAFT-gnat-consumer-ohos-hnp-binutils-path`）。

### 4. package() 打包未修改源单元 + 许可证

把 `.ads`/`.adb` 复制到 `adainclude/`，`COPYING`/`lesser.txt` 复制到 `licenses/`。不打包
构建目录、ALI、对象文件或临时产物。

### 5. test_package 用 conanbuild 编译消费者

gcc-ada 是 tool_requires，其 GNAT 环境在 `conanbuild` 而非 `conanrun`。test_package 的
`build()` 必须用 `env=["conanbuild", "<binutils-env>"]` 编译 `.adb`，再签名、运行确定性
断言；用 `self.dependencies["adacgi"].cpp_info.includedirs` 取 `-I<adainclude>`。

## 与已有知识的差异

- `DRAFT-gcc-ada-ohos-xpm-seed-loader` / `DRAFT-gcc-ada-ohos-link-only-libunwind` 覆盖
  **gcc-ada 工具链自身**的 bootstrap 与链接问题；本条目覆盖 gcc-ada 的**下游 Ada 库消费**模式。
- `E012`（鸿蒙 SDK 只提供 LLVM 工具链）陈述 binutils 缺失这一事实；本条目给出 Ada 源码库
  在 Conan 中的完整配方契约（header-library + tool_requires + adainclude + 消费测试）。
- `E450`（avr-gcc -B 搜索 unprefixed binutils）是交叉工具链**打包**场景；本条目是**源码分发库**
  现场编译场景，两者 build/run context 不同。

## 禁止做法

- 不要为 Ada 源码库声明 `package_type="library"` 却不定义 `shared` 选项。
- 不要伪造 `cpp_info.libs`（没有预编译 `.a`/`.so`），不要打包 `.ali`/`.o` 或 build 目录。
- 不要在 test_package 里用 `conanrun` 环境去拿 gcc-ada 的 `ADA_INCLUDE_PATH`。
- 不要把 gcc-ada 的 bootstrap/工具链问题混入下游库 PR。

## 已验证示例

adacgi 1.6 基于 Debian 权威镜像 `adacgi_1.6.orig.tar.gz`（SHA-256
`6a417f4936a362c1d3d85b8331c26be4ef381ce152cf03c39ac1d5c86fdb884c`），打包 `CGI` 与
`Ustrings` 两个未修改单元。OHOS aarch64 真机 shadow CI 隔离 job 全绿：L0/L1/L4 pass、
L2 skip（无 bin/）、L5 warn（header-library 无 `.a`/`.so`），消费测试
`ADACGI_LINKAGE=pass assertions=9`。

复现入口：

```sh
CI_PACKAGES="archives/a/adacgi/1.6" zsh ci/conan/build_and_test.sh
```

## 证据来源

- `archives/a/adacgi/1.6/conanfile.py`
- `archives/a/adacgi/1.6/test_package/conanfile.py`
- `archives/a/adacgi/1.6/test_package/test_adacgi.adb`
- `archives/a/adacgi/1.6/test_package/verify_adacgi.py`
- `archives/a/adacgi/1.6/notes.md`
