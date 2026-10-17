# DRAFT-letter-shell-3.1.2-linker-section-fragment：段注册型嵌入式 C 库的消费者链接最小链接片段

> Contributor: pc4-17 | Status: Draft | Updated: 2026-09-22
> Source: letter-shell 3.1.2 适配（Path B 知识库扩展）；触发场景：`conan-verify`
> G2 conan create 前的消费者原型链接
> 对应：`knowledge/drafts/DRAFT-letter-shell-3.1.2-linker-section-fragment.kv`

## 现象

消费者原型链接静态库 `libletter-shell.a` 时失败：

```text
ld.lld: error: undefined symbol: shellStrToInt          （原型误用非公开 API，已修）
ld.lld: error: undefined symbol: _shell_command_start
>>> referenced by shell.c
ld.lld: error: undefined symbol: _shell_command_end
>>> referenced by shell.c
clang-15: error: linker command failed with exit code 1
```

随后改用正确签名（SHELL_TYPE_CMD_MAIN, argc/argv）后，`shellRun("add 3 4")`
输出 `7`、`add 10 32` 输出 `42`，运行通过。

## 根因

1. letter-shell 的 `SHELL_EXPORT_CMD` 把命令表放入自定义 `shellCommand` 链接段
   （`__attribute__((section("shellCommand")))`）；`shellInit` 在 `__GNUC__` 下取
   `&_shell_command_start` / `&_shell_command_end` 边界符号，该符号只由链接脚本
   （上游 demo 的 `shell.lds`, `KEEP(*shellCommand)`）提供。Conan 静态库消费者
   未携带该脚本 → 链接失败。
2. 命令执行按 `attr.type` 分派：`SHELL_TYPE_CMD_FUNC` 以解析后的 int 参数
   （`shellExtParsePara`/`SHELL_PARAM_FLOAT`）调用；`SHELL_TYPE_CMD_MAIN` 以
   `(argc, argv)` 调用。消费者导出命令若用错类型，运行时按错误参数解释 → 段错误。

## 方案

1. 配方目录提供最小链接片段 `shellcmds.lds`：

   ```ld
   SECTIONS
   {
     .shellCommand : { _shell_command_start = .; KEEP(*(shellCommand)) _shell_command_end = .; }
   } INSERT AFTER .data;
   ```

   `INSERT AFTER .data` 复用默认链接脚本，避免整段重写（比直接搬上游完整
   `shell.lds` 更可移植——后者含平台特定 `OUTPUT_ARCH`/`SEARCH_DIR`）。
2. conanfile.py：`exports = "shellcmds.lds"`；`export_sources()` 中 copy 到
   `export_sources_folder`（注意：不能用 `self.source_folder`，导出阶段为 None，
   会抛 `TypeError: expected str...not NoneType`）；`package()` 复制到 `lib/`。
3. 消费者 / test_package 以 `-Wl,-T,<lib>/shellcmds.lds` 链接。
4. 消费者导出命令用 main 型签名：

   ```c
   static int cmdAdd(int argc, char *argv[]) { ... }
   SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0)|SHELL_CMD_TYPE(SHELL_TYPE_CMD_MAIN)|
                    SHELL_CMD_PARAM_NUM(2), add, cmdAdd, add two ints);
   ```

5. 命令输出通过 `shell.write` 捕获回调断言（`strstr(outBuf, "7")`）。

## 验证

- 消费者原型：`add 3 4`→`7`、`add 10 32`→`42`（输出断言通过，exit 0）。
- OHOS 专项：`mul 6 7`→`42`，`__aarch64__` 与 `SHELL_VERSION=3.1.2` 断言通过。
- conan-verify G2 conan create 通过；test_package 两个可执行用例均 PASS。

## 适用边界与反例

- **适用**：使用「自定义链接段 + 段边界符号」注册机制的嵌入式 C 库
  （letter-shell 及同类段注册库）在 Conan/静态库打包下的消费者链接。
- **边界**：`INSERT AFTER` 需要 ld.lld/GNU ld 支持；极老链接器可能不支持，需退化为
  完整脚本。命令分派约定（CMD_FUNC vs CMD_MAIN）为 letter-shell 特有，换库需
  重新核对。
- **反例**：以 strip 段/移除 SHELL_EXPORT_CMD 规避链接错误；把段边界符号伪造成
  常量 0（命令表扫描读非法地址崩溃）；把 CMD_FUNC（int 参数）签名误用为 main 型。

## 关系

- similar_to: E307（test_package 缺 CMake 用 profile 编译器直编——同为 test_package
  直编，但解决编译对象而非链接段符号）
- caused_by: （无）
- prerequisite_of: 无
- conflicts_with: 无