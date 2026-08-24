# Flow Control — OpenHarmony 编译档案

## 软件简介
Flow Control（neurocyte/flow）是一款使用 Zig 编写的程序员文本编辑器，支持 70+ 语言的 tree-sitter 语法高亮、LSP、multi-cursor、clipboard history 等特性，TUI 帧时延 ≤6ms。

## 功能概述
- 基于 tree-sitter 的语法高亮（70+ 语言，零配置）
- LSP 预配置
- multi-cursor 编辑、clipboard history
- 可配置 keybinding（Flow/Emacs/Vim/Helix 模式）
- rope/piece-table 混合 buffer，大文件与千级光标支持
- 无限 undo、完整 unicode、kitty 文本尺寸协议

## OHOS 适配要点
- 声明 `minimum_zig_version = "0.15.2"`，与 Zig 0.16.x 不兼容，使用 `zig/0.15.2` tool_requires
- 构建命令 `zig build -Doptimize=ReleaseSafe`（上游默认生产模式），21/21 steps
- OHOS 上 Zig 探测宿主 libc 会注入 OHOS SDK sysroot 头，其 `stdint.h` 依赖 `bits/alltypes.h` 但 Zig 无法解析；`build()` 中清理 `CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS/CPATH/CPLUS_INCLUDE_PATH/C_INCLUDE_PATH` 使 Zig 回落自带 musl 头
- Zig 生成的宿主可执行产物（build runner、ts_bin_query_gen、uucode_build_tables）与最终 `zig-out/bin/flow` 需签名；前者由 `zig/0.15.2` wrapper 自动签名，后者在 `package()` 中通过 `binary-sign-tool`/`llvm-objcopy` 自签名（`_is_ohos()` 生效）
- 产物为静态 ELF `bin/flow`，`package_type = "application"`，`cpp_info.libs = []`
- Zig cache 隔离：`ZIG_GLOBAL_CACHE_DIR` / `ZIG_LOCAL_CACHE_DIR` 指向 `build_folder`，`ZIG_OHOS_SIGN_ROOTS` 覆盖三处缓存与输出目录
- `validate()` 仅接受 `Linux/OHOS`（R32）

## 依赖关系
- 构建依赖：`zig/0.15.2`（tool_requires）
- 运行时：无（静态 ELF）

## 参考资料
- [neurocyte/flow GitHub](https://github.com/neurocyte/flow)
- [flow-control.dev](https://flow-control.dev)
- 源码 tarball: https://github.com/neurocyte/flow/archive/refs/tags/v0.7.2.tar.gz

## Conan 使用
```bash
conan create archives/f/flow-control/0.7.2 --version 0.7.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
