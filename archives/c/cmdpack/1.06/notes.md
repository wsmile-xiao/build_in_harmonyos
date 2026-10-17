# cmdpack 1.06 适配笔记

## 上游与依赖

- 上游：`https://github.com/chungy/cmdpack`
- 正式版本：GitHub release/tag `1.06`，提交 `6bad3c7`
- 源码 SHA256：`6ce7029c0f2b0fbc6a1e26fb3ad8003ed18836aa3ef35f148ec51cde0b703307`
- 构建系统：原生 Makefile
- 第三方依赖：无；仅使用 libc/POSIX 文件接口和 C 编译器

## 上游测试清点（R51）

- 源码包共 13 个 `.c` 文件、1 个 Makefile。
- 不存在 `tests/`、`test/`、CTest、pytest 或自定义测试运行器。
- Makefile 只有 `all`、`clean`、`install` 目标，没有 `check` 或 `test` 目标。
- 因此上游自动化测试总数为 0，不能在 `build()` 中执行不存在的测试目标。

## 适配与构建

源码不依赖 Linux/glibc 专有 API，标准构建即可：

```bash
make clean
make CC=clang VERSION=v1.06 -j1
```

上游 `install` 目标依赖 AsciiDoc `a2x` 生成 man page，并为 `ecm2bin` 创建符号链接。
配方直接打包 13 个已编译程序和文本手册，另外复制 `bin2ecm` 为 `ecm2bin`，避免引入非必要构建依赖及 HMDFS 符号链接问题。

## 本机探索结果

- Apple clang 17：13/13 个上游程序编译成功。
- 功能冒烟：ECM 编解码往返、IPS 补丁创建/应用、字节拆分/重组均成功。
- 本机结果仅用于配方开发，不替代 HarmonyOS PC 的 W3/CI 结果。

## 补丁

无需源码补丁。

## 已知限制

上游没有自动化测试套件；本适配通过 `test_package` 增加 14 个命令入口检查和 7 个功能断言。

## HarmonyOS 验证

- 仓库 L0、知识库、杂项文件、版本占用和 `commands.json` 门禁均通过。
- 远端 HarmonyOS CI #9022 已通过 OHOS/armv8 编译及 `test_package`。
- 测试总数 21：20 个通用集成测试，1 个 HarmonyOS/HMDFS 特有测试。
- 鸿蒙特有测试验证 `ecm2bin` 是实体可执行入口而非符号链接，并完成 2352 字节 CD sector 的 ECM 编解码往返。
- 本地 macOS 无 `/data/service/hnp/bin/clang`，因此本地 W3 仍不能作为目标平台证据；最终构建结论以远端 CI #9022 为准。

---

**编译结束**: 2026-09-08 22:33
**最终状态**: built
