# glib 2.88.0.1 HarmonyOS PC adaptation notes

Issue: #1790（glib 2.88.0 shared=True 修复版本）
Branch: fix/glib-2.88.0.1
Target path: archives/g/glib/2.88.0.1

## Summary

基于 `glib/2.88.0` 的修复版本（`2.88.0.1`），不是重新适配。上游源码仍为
glib 2.88.0，新增 shared=True 动态构建能力，同时保留 shared=False 静态构建。

`glib/2.88.0` 现有配方只正常发布 `shared=False`；`goffice` 需要 `shared=True`，
此前被两个平台问题阻塞，本版本逐一修复。

## 关键改动

1. **依赖升级**：`zlib/1.3.1` → `zlib/1.3.1.1.1.1`（PIC 静态库，`static + -fPIC`）。
   旧 `zlib/1.3.1` 是非 PIC 静态库，链接进共享库时报
   `relocation R_AARCH64_ADR_PREL_PG_HI21 ... z_errmsg` 错误。

2. **shared=True 构建期工具运行修复**（核心问题）：
   OHOS HMDFS 动态链接器无法通过符号链接 dlopen `.so`（报 `Permission denied`）。
   meson 生成「版本化 .so + 符号链接别名」（`libgio-2.0.so.0 -> .0.8800.0`），
   构建期工具（glib-compile-resources 等）通过符号链接加载共享库失败。
   修复：`build()` 在 shared+OHOS 下分阶段构建——先用 meson target 名构建主共享库
   （ffi/intl/glib-2.0/gobject-2.0/gmodule-2.0/gio-2.0），把 `.so` 符号链接替换为
   硬拷贝，再继续构建其余目标；完整构建后再替换测试插件等剩余符号链接。

3. **安装产物签名**：`meson install` 会改动 ELF（如 strip），使 `.codesign` 失效。
   `package()` 对安装后的 bin/ 与 lib/*.so 重新签名（先 `llvm-objcopy
   --remove-section .codesign`，再 `binary-sign-tool sign -selfSign 1`），跳过非 ELF
   文件（如 gdbus-codegen 实为 Python 脚本）。

4. **proxy-libintl SONAME 冲突修复**（替代 can_fail 方案）：
   proxy-libintl 默认以 SONAME `libintl.so.8` 构建，与系统 gettext 的
   `libintl.so.8` 同名冲突。shared 构建下测试 LD_LIBRARY_PATH 把 proxy-libintl
   置于首位，导致 Python 解释器加载 proxy-libintl（只导出 `g_libintl_*` 符号）而
   启动失败（exit 127）。`source()` 下载 proxy-libintl 后把其 `soversion` 从 8 提升
   为 9（SONAME 变为 `libintl.so.9`），与系统 gettext 彻底错开，三个 Python 工具
   测试因此恢复为真实 PASS/SKIP，无需 can_fail 标记。

## 构建配置

shared=True 与 shared=False 共用配方，通过 `-o glib/*:shared=True` 切换。其余选项
（wrap_mode=nodownload、libmount/selinux/nls/introspection 关闭、tests=true）与
2.88.0 一致。

## 验证结果

- `shared=False`：上游 meson 测试 301 Ok / 0 Fail / 6 Skip；test_package OK。
- `shared=True`：上游 meson 测试 304 Ok / 0 Fail / 6 Skip；test_package OK。
  - 三个 Python 工具测试真实结果（无 can_fail）：
    messages-low-memory.py = PASS、gobject-query.py = PASS、gdbus-tool.py = SKIP。
- `conan-verify`：G0-G4 + L2/L4/L5 全 PASS，可标记 published。

---

**编译结束**: 2026-08-19
**最终状态**: built（conan-verify 已 PASS，待制品发布流水线）
