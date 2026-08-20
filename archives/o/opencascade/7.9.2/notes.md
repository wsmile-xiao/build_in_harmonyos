# opencascade 7.9.2 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libTKernel.so 等 **47 个** TK* 库，供链接与 dlopen。
- 模块开关沿用 7.9.3 已评审方案：FoundationClasses / ModelingData / ModelingAlgorithms /
  ApplicationFramework / DataExchange = ON；Visualization / Draw / DETools = OFF；
  OpenGL/GLES/XLib/VTK/TK/TCL/D3D/OpenVR/FreeImage/FFmpeg/FreeType/Draco/TBB/RapidJSON/Eigen 全 OFF。

## 关键适配
- `settings.os == "OHOS"` 时 CMakeToolchain 显式设 `cmake_system_name=OHOS` + `cmake_system_processor=aarch64`：
  conan 默认把 CMAKE_SYSTEM_NAME 填成 "HarmonyOS"，而 cmake 平台的平台文件叫 OHOS.cmake（没有 HarmonyOS.cmake），
  名字对不上 → `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 空 → 产物无 DT_SONAME、无版本软链 → 传染下游消费方
  DT_NEEDED 变成绝对路径。必须带 os 守卫（沿用 7.9.3 经验，R32）。
- `CMAKE_INSTALL_LIBDIR=lib`（避免装到 lib64 导致 cpp_info.libdirs 与 test_package 找不到）。
- `BUILD_SHARED_LIBS` 跟随 `options.shared`（不能写死 True，否则 shared=False 消费方静默失效）。
- `package()` 显式重签 ELF：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`，
  对 lib/ 全部 .so* 与 bin/ 真实 ELF。链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，
  dlopen 报 Permission denied。签名守卫在方法内（settings.os != OHOS 直接 return），避免非 OHOS profile 崩（沿用 7.9.3 经验）。

## ⭐ 与 7.9.3 的差异（本版要点）
- **cpp_info.libs 如实列出 47 个实际产物**，其中比 7.9.3 多声明了 **TKService、TKV3d**：
  7.9.2 中即使 `BUILD_MODULE_Visualization=OFF`，一旦启用 DataExchange/ApplicationFramework，
  其内部可视化格式工具（TKDEGLTF/TKDEOBJ/TKDEPLY/TKDEVRML/TKRWMesh、TKVCAF/TKXCAF/TKBinXCAF）
  的 EXTERNLIB 强依赖会把 Visualization 基础设施库 TKV3d/TKService 作为 full-deps 一并编出。
  产物已生成就必须如实声明，否则成为链接不到的孤儿 .so；消费方用到这些库时也会缺 -lTKV3d/-lTKService。
- TKG2d/TKG3d 几何内核库在 7.9.3 与 7.9.2 的 cpp_info 中均有声明（7.9.3 真正漏的是 TKV3d/TKService 这 2 个）。
- 结论：7.9.2 实际比 7.9.3 多编出 2 个可视化依赖库（TKService、TKV3d），它们是被 DataExchange/
  ApplicationFramework 的工具库强依赖拉进来的，非主动开启 Visualization。不开 OpenGL/GLES 因此
  纯几何内核路径仍可正常消费。

## 其他
- 本包无外部依赖（W0 预检通过），制品仓中无 opencascade/7.9.2 记录（唯一发布为 7.9.3），版本号直接用 7.9.2（R37）。
- 库类型（无命令行工具产物）→ 不需要 commands.json（R38）。
- conandata.yml URL 指向官方 GitHub 源 + sha256（R39）。

## 状态
built（真机 conan create + test_package 通过；conan-verify 8 门禁 PASS；W3 本地 CI 模拟 Pass 100%）

---

**编译结束**: 2026-08-20
**最终状态**: built（conan 制品仓已存在 7.9.3，本 7.9.2 首次适配、版本号直接使用，待 CI/发布流程 upload）

### 对话 #1
- 编译 opencascade 7.9.2，沿用 7.9.3 成熟配方（cmake OHOS + ELF 重签）。
- conan-verify 8 道门禁（G0-G4/L2/L4/L5）全部 PASS；conan create 完整编译 47 个 .so 并签名。
- test_package 17 断言全部通过（版本 7.9.2 / 长方体体积 6000 / 布尔差集 5875·面数6→9 / STEP 往返 25356 字节 TKDESTEP 已接入）。
- W3 本地 CI 模拟（build_and_test.sh）：L0/L1/L1e/L4/L5 全 PASS，Pass rate 100%。
- 实际产出含 TKV3d/TKService（DataExchange/ApplicationFramework 工具库强依赖拉入），已如实声明进 cpp_info.libs。
