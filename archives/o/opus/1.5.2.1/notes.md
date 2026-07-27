# opus 1.5.2.1 编译笔记（HarmonyOS PC）

## 本版改了什么

**仅一处**：`package_info()` 补 `cpp_info.includedirs = ["include/opus", "include"]`。
配方其余部分与 1.5.2 完全一致（同一 CMake 构建路径、同一源码 sha256）。

## 为什么需要这个修复

opus 的公开头装在 `include/opus/`（`CMakeLists.txt:608` 的
`PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/opus`），而上游 `opus.pc` 写的是
`Cflags: -I${includedir}/opus`。因此**所有消费方按 `#include <opus.h>` /
`<opus_multistream.h>` 来写，不带 `opus/` 前缀**。

1.5.2 未设 `includedirs`，conan 生成的 `opus.pc` 只给 `-I<pkg>/include`，消费方编译期找不到头。

实证（FFmpeg 7.1.5 接入 libopus 时）：configure 报

```
ERROR: opus not found using pkg-config
```

这条报错**具误导性**——pkg-config 其实找得到 opus（`--exists` rc=0、`--modversion` 返回 1.5.2），
真正失败的是紧随其后的 `check_func_headers opus_multistream.h ...` 编译探测。

修复前 FFmpeg 侧必须自行 remap 补 `-I<opus>/include/opus`；本版修好后消费方无需任何绕行。

> 参照：同仓 `freetype/2.14.3` 已正确设置 `includedirs = ["include/freetype2", "include"]`。

## 版本号

按 R37：`1.5.2` 已发布到制品仓，改配方须递增后缀 → `1.5.2.1`。
