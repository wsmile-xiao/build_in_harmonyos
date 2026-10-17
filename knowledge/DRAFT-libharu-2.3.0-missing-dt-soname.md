# libhpdf.so 缺少 DT_SONAME — HarmonyOS 无 CMake 平台模块导致 SONAME 链接标志为空

- **草稿 ID**: DRAFT-libharu-2.3.0-missing-dt-soname
- **来源**: libharu/2.3.0 R03 SONAME 修复本地验证
- **分类**: cmake / shared-library / soname / ohos-platform
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）

## 问题 / 错误签名

- W3 本地 CI 日志（finish W3）：`[fail] L5a: libhpdf.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址`，`L5_RESULT=fail: soname_gate_failed`。
- 产物检查：`readelf -d libhpdf.so` 的 dynamic 段**没有** `SONAME` 条目（`grep -c SONAME` 返回 0）。
- 复现命令：`readelf -d <conan-cache>/p/<...>/p/lib/libhpdf.so` 看不到 `0x000000000000000e (SONAME)`。

## 根因

1. 上游 libharu 2.3.0 的 `src/CMakeLists.txt` 对共享目标 `${LIBHPDF_NAME}` 未设置 `VERSION`/`SOVERSION`。
2. 更深层：HarmonyOS/OHOS 目标在 CMake 中**没有** `Platform/HarmonyOS.cmake` 平台模块。Linux 平台模块（`Platform/Linux.cmake`）会设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"`；无 HarmonyOS 等价模块时该变量为空。CMake 链接模板 `<SONAME_FLAG><TARGET_SONAME>` 中 `SONAME_FLAG` 为空，链接器收不到 `-Wl,-soname`，即使项目设置了 `SOVERSION`，产物 .so 的 ELF dynamic 段仍无 SONAME。

## 最小修复方案

在 `archives/l/libharu/2.3.0/**` 范围内：

1. **上游补丁** `patches/0001-src-CMakeLists.txt.patch`：在共享目标上设置
   `set_target_properties(${LIBHPDF_NAME} PROPERTIES VERSION ${LIBHPDF_VERSION} SOVERSION ${LIBHPDF_MAJOR})`。
2. **配方** `conanfile.py` `generate()`（os==OHOS 分支）：
   - `tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"`
   - `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`
   - `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"`
   使 CMake 产出**未版本化、带可重定位 SONAME** 的 `libhpdf.so`（无版本化符号链接，HMDFS 友好）。
3. **test_package**（E298）：消费者运行需 `VirtualRunEnv` 生成器 + `self.run(..., env="conanrun")` 显式运行，否则运行时找不到 libhpdf.so；配方默认 `shared=True`（R26 非系统同名库默认动态），使 VirtualRunEnv 将包 lib 目录加入 LD_LIBRARY_PATH。
4. `conandata.yml` 声明补丁；`manifest.yaml` 记录 `patches_applied` 与 knowledge。

## 实际验证结果

- `conan-verify`（含 conan create）：G0-G4/L2/L4/L5 全部 PASS，exit=0。
- 修复后产物：`readelf -d libhpdf.so` 显示 `0x000000000000000e (SONAME) Library soname: [libhpdf.so]`。
- test_package 消费者：`libharu 2.3.0 consumer test OK: test_libharu.pdf 633 bytes`（真实 API 调用 + 产物校验）。
- W3 本地 CI（finish，goaccess 基线按 R02 方式精确临时隔离并恢复后）：`Junk Files: 0`，`L5_RESULT=pass`，Build Summary `Success 1 / Failed 0 / Pass rate 100%`，`.ci-result.json exit_code 0`。

## 适用范围

- 在 HarmonyOS PC 上构建、产出共享库并被 W3 L5 SONAME 门禁检查的 CMake 类 C/C++ 三方库。
- 上游 CMake 未设置 SOVERSION 或设置了但无 SONAME 链接标志的库。

## 非适用边界

- 不需要 SONAME 的静态库（`libhpdfs.a`）不在范围。
- 已有完整版本化 SONAME 且通过 L5 门禁的库无需本方案。
- 不在当前库范围外的库、共享框架或基线文件，不适用（不得改动）。

## 查重差异

- 与 `DRAFT-expat-cmake-soname-1912` / `E322-draft-F2BA` 主题相似（HarmonyOS 无 CMake 平台模块导致 SONAME 标志为空），本条目以 libharu/2.3.0 为具体载体，补充了“上游未设 SOVERSION + 平台标志为空”双根因、未版本化 SONAME 方案与完整验证证据；不重复已有条目结论，无伪造编号/链接/审核。

## 关联交付

- 本草稿与 `archives/l/libharu/2.3.0/**` 属于同一 LibHaru 交付范围（同 PR 关联，按知识库扩展路径 B 规定）。
- 本轮仅生成本地草稿；未创建/更新 Issue/PR，未触发远端 CI，未写 Conan 远端（`remote_actions: none`）。