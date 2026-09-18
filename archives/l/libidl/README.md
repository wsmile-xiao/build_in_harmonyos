# libidl

> CORBA IDL 解析库（GLib 基础，bison/flex 生成的语法分析器）。

## 简介

libIDL 把 CORBA IDL（含 XPIDL 扩展）解析成语法树，并提供：

- 解析入口：`IDL_parse_filename()`（默认经 C 预处理器）与
  `IDL_parse_filename_with_input()`（自带输入回调，**不经 cpp**）；
- 语法树操作：构造/遍历（`IDL_tree_walk_in_order`）、类型查询（`IDL_NODE_TYPE`）、释放；
- 命名空间与仓库 ID：`IDL_ns_*`；
- 反向序列化：`IDL_tree_to_IDL()` / `IDL_tree_to_IDL_string()`。

历史上用于 GNOME 的 IDL 编译器（ORBit）与 Mozilla 的 xpidl。

## OHOS 适配要点

- **构建期需要 bison/flex**：上游 tarball 只带 `parser.y`/`lexer.l`，没有生成的
  `parser.c`/`lexer.c`。本仓库用 `tool_requires("bison/3.8.2")` 与
  `tool_requires("flex/2.6.4.2")`（ohpcd 制品仓已发布）拉入，无需宿主机安装。
- **glib 依赖**：`configure` 用 `PKG_CHECK_MODULES(..., glib-2.0 >= 2.4.0)`，
  由 `PkgConfigDeps` 生成 `glib-2.0.pc`（Conan `glib/2.84.0`）。
- **E007**：上游 `config.sub` 过旧（不识别 aarch64/HarmonyOS）→
  `patches/0002-config-sub-ohos.patch` 加 17 行早退分支，并显式传 `--build`/`--host`，
  从而完全不执行 `config.guess`（它在 HMDFS 上会因无法创建临时文件而失败）。
- **E011**：autoconf 2.63 的 `umask 077` 临时目录在 HMDFS（setgid 挂载）下不可写 →
  补丁放宽为 `umask 022`。
- **预处理器路径**：API 提供两条入口——`IDL_parse_filename()` 会 fork C 预处理器
  （本仓库构建时 configure 探测到 SDK 的 `clang -E`，设备上按名字没有 `cpp`/`cc`），
  而 `IDL_parse_filename_with_input()` 用自带输入回调、**完全不依赖外部预处理器**。
  本仓库的消费者测试使用后者；上游 `tstidl` 演示用前者并在设备上实跑成功。
- 产物：`lib/libIDL-2.so.0`、`lib/libIDL-2.a`、`include/libIDL-2.0/libIDL/IDL.h`、
  `lib/pkgconfig/libIDL-2.0.pc`。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| glib | 2.84.0 | 运行时/公共头依赖（Conan `glib/2.84.0`） |
| bison | 3.8.2 | 构建期（`tool_requires`） |
| flex | 2.6.4 | 构建期（`tool_requires`） |

## 使用

```cmake
find_package(libIDL-2.0 CONFIG REQUIRED)
target_link_libraries(app PRIVATE libIDL::libIDL-2)
```

pkg-config：

```sh
pkg-config --cflags --libs libIDL-2.0
```

不经 cpp 解析一段 IDL（`IDL_parse_filename_with_input` + 自定义输入回调）：

```c
#include <libIDL/IDL.h>

/* input_cb: IDL_INPUT_REASON_INIT/FILL/ABORT/FINISH，FILL 时填充缓冲区 */
IDL_tree tree; IDL_ns ns;
int rc = IDL_parse_filename_with_input("string.idl", input_cb, &buf,
                                       NULL, &tree, &ns, 0, IDL_WARNING1);
if (rc == IDL_SUCCESS) {
    GString *text = IDL_tree_to_IDL_string(tree, ns, 0);
    IDL_ns_free(ns);
    IDL_tree_free(tree);
}
```

## 功能验证

```sh
conan create archives/l/libidl/0.8.14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 上游 tstidl 1/1 exit 0；消费者 14/14 断言通过
```
