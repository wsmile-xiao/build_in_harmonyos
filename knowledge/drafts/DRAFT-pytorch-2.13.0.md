# DRAFT-pytorch-2.13.0 适配知识草稿说明

配套文件: `DRAFT-pytorch-2.13.0.kv`

## 关键经验

1. **子模块下载**：pytorch 2.13.0 源码 tarball 不含 37 个 third_party 子模块；
   本环境 codeload.github.com 被阻断，ghfast.top 对 cutlass 等大 repo 限速。
   采用多镜像兜底：`gh-proxy.com → gh.ddlc.top → ghfast.top → codeload`，_download 支持多 URL + 3 次重试。

2. **SONAME**：`CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 不生成 SONAME（NEEDED 记相对路径 `../lib/xxx`，musl 无法解析）；
   改 `OHOS` 且不设 SOVERSION → 生成**纯名 SONAME**（libtorch_cpu.so），可被 musl 加载。

3. **HMDFS mmap 限制**：`cmake --install` 写入的 .so 无法被 musl mmap(PROT_EXEC)（Permission denied）；
   `package()` 需从 build 目录用 `shutil.copy2` 复制 .so 覆盖。

4. **编译器**：pytorch 硬要求 Clang>=16，SDK 仅 clang 15；用 `tool_requires clang/22.1.8`，
   保留 SDK libc++15（__n1 ABI）+ `-D__MUSL__`。

## 待推广为 E-entry
- 建议评估是否推广为通用经验（镜像源多源兜底、OHOS 纯名 SONAME、HMDFS install 产物 mmap 兼容）。

（覆盖上游他人分支后重新提交）
