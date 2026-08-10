# pika 1.14.0 适配笔记

## 编译环境
- 构建系统: cmake（根级 CMakeLists.txt 由补丁 0001 补充，上游 release 无根级 CMakeLists）
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 初始化（下载/解压/骨架）
python3 scripts/ohc-run.py init-build pika 1.14.0 \
  --url=https://github.com/pikasTech/PikaPython/archive/refs/tags/v1.14.0.tar.gz

# 2. 生成 Conan 配方
python3 scripts/ohc-run.py conan-init pika 1.14.0

# 3. 验证配方（8 道门禁，G2 conan create 使用 ohos-aarch64 profile）
python3 scripts/ohc-run.py conan-verify pika 1.14.0

# 4. 收尾（W2 结构 + R36 依赖 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish pika 1.14.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 v1.14.0 tarball 无根级 CMakeLists.txt，CMake 配置失败 | 上游仅提供 src/CMakeLists.txt（依赖 pikaCompiler 预生成绑定），无根构建文件 | 补丁 0001 新增根 CMakeLists.txt：编译 src/*.c 为静态库 pika-core，头文件安装到 include/pika |
| 2 | PikaVM.c 编译错误 `expected expression`（9 处） | clang 不允许 C 标签后直接跟声明（GCC 允许），`__unpack:` 标签后是 `Stack stack_tmp = {0};` | 补丁 0002 在标签后插入空语句 `;` |
| 3 | test_package 链接缺 PikaStdLib 符号（New_builtins_object 等 17 个） | 标准库绑定由上游 pikaCompiler（Rust 预编译器）从 .pyi 生成，release tarball 不含生成产物 | test_package 增加 stubs.c 仅满足静态链接；数据层 API 测试不触碰 VM/builtins 路径 |
| 4 | test_package 运行 SIGABRT | 早期 test.c 对 `Args*` 误用 `arg_deinit()`（类型不匹配 UB） | 改用 `strsDeinit()`；stdout 无缓冲便于定位 |
| 5 | conan-verify G2 失败 `/bin/sh: syntax error: unexpected '('` | 副本目录名含 `(13)` 括号，verify 脚本经 `/bin/sh -c` 执行未加引号的绝对路径 | 本地用 `OHC_PROJECT_DIR` 指向无括号符号链接副本运行脚本（环境问题，非配方问题） |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-add-root-cmakelists.patch | 新增根 CMakeLists.txt（+13 行） |
| patches/0002-fix-clang-label-decl.patch | PikaVM.c `__unpack:` 标签后插入空语句（+1 行） |

## 依赖版本

零外部依赖（PikaPython 纯内核，无第三方库依赖）。

## 验证结果

```bash
# 主机侧数据层 API 测试（host x86_64，含 stubs）
# 33/33 通过（100%），见 reports/host-test-log.txt

# test_package 交叉侧测试（ohos-aarch64, conan create 内执行）
# 11/11 通过（100%）
```

## 注意事项

- PikaPython 的完整 VM 运行需要 pikaCompiler 生成的标准库绑定（New_builtins_object 等），本配方交付 pika-core 静态库 + 数据层 API 测试；如需完整脚本执行能力，需另行打包 PikaStdLib 绑定。
- 系统同名库隔离（R26）：pika 无系统同名库，无需静态强制。
- R38：构建产物仅为静态库 libpika-core.a，无可执行文件，无需 commands.json。

---

**编译结束**: 2026-08-08 17:35
**最终状态**: built
