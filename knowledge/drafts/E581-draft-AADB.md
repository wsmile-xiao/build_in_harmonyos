# E581: CMAKE_SKIP_RPATH=TRUE 防止 cmake.install() 用 patchelf 破坏 OHOS ELF

## 基本信息
- **严重度**: 2
- **类别**: cmake, conan, linking, runtime, ohos
- **来源**: libdrumstick 2.10.0 HarmonyOS PC 适配（conan-verify 第 15 轮）
- **草稿编号**: E581

## 错误特征
```
Error loading shared library libdrumstick-file.so.2: (needed by ./test_libdrumstick)
Error loading shared library libdrumstick-rt.so.2: (needed by ./test_libdrumstick)
Error relocating ./test_libdrumstick: _ZN9drumstick4File4QSmfC1EP7QObject: symbol not found
```

发生在 conan create 的 **test_package test() 运行阶段**：
- build() 阶段 configure/build/ctest 全部正常（build 树内库可加载）
- package() 安装后，test_package 链接 pkg 目录库时报 "Error loading shared library"

## 触发条件
- conan 2 配方使用 CMake + `cmake.install()` 打包共享库
- `CMAKE_SKIP_RPATH` 未设置（默认 FALSE）
- OHOS/HarmonyOS PC 目标，库被 test_package 或下游动态加载
- 库依赖其他 Conan 包动态库（Qt6、fluidsynth、libc++_shared.so 等）

## 根因分析
conan 配方的 build() 产出 build 树库可正常加载（CMake 构建期写入 RUNPATH
指向依赖库）。但 package() 阶段 `cmake.install()` 默认（`CMAKE_SKIP_RPATH=NO`）
会调用 patchelf 清理/重写安装后库的 RPATH/RUNPATH。

关键实验证据（libdrumstick 2.10.0）：
1. build 库（`b/build/Release/lib`）MD5=7109282d、有 RUNPATH → **可加载**
2. pkg 库（`p/lib`）MD5=09a92fe3、RUNPATH 已被 install 处理 → **不可加载**
3. 两个库 NEEDED/SONAME/未定义符号完全一致，但 `.rela.dyn`/`.rela.plt`
   段大小不同（00007d80 vs 00007df8）——patchelf 重排重定位段的痕迹
4. 对 build 库手动 `patchelf --remove-rpath` 后仍加载失败；恢复 RUNPATH 后
   仍失败——**patchelf 本身破坏 OHOS 加载器所需 ELF 结构**，非单纯 RPATH 缺失
5. 设 `CMAKE_SKIP_RPATH=TRUE` 后安装库与 build 产物一致，test_package 通过

即：`cmake.install()` 内部的 patchelf 重写是安装后库无法加载的根因，与
LD_LIBRARY_PATH 是否完整无关。

## 解决方案
**方法**: cmake-skip-rpath-true

在 conanfile.py `generate()` 的 CMakeToolchain 中：

```python
tc = CMakeToolchain(self)
tc.variables["CMAKE_SKIP_RPATH"] = "TRUE"
```

效果：`cmake.install()` 不再重写安装库 RPATH，安装库与 build 产物逐字节一致。
运行期共享库依赖由 `build()`/`test()` 中 `cmake -E env LD_LIBRARY_PATH=...`
显式注入（E520 方案）。

配套要求：
- `build()` 的 ctest 用 `cmake -E env LD_LIBRARY_PATH=<build/lib>:<dep libs>:<SDK libc++>`
- `test_package` 的 `test()` 用 `env LD_LIBRARY_PATH=<pkg/lib>:<dep libs>:<SDK libc++>`
  并注入 `DRUMSTICKRT=<pkg>/lib/drumstick2` 插件路径（BackendManager 场景）

## 验证证据
- 修复前（第 14 轮）：test_package test() 报 `Error loading shared library libdrumstick-file.so.2`
- 修复后（第 16 轮）：conan-verify G1/G0/G2/G3/G4 全部 PASS，W3 本地 CI 100%
- 复现命令：`conan create <recipe> -pr:h=ohos-aarch64 --build=missing`

## 适用边界
**适用**：
- OHOS/HarmonyOS PC 上所有 CMake + cmake.install() 的 Conan 共享库配方
- 库被 test_package/下游动态链接且依赖其他 Conan 包动态库的场景

**不适用**：
- 不需要运行期动态链接的纯静态库（无影响但设置无害）
- 需要保留安装后 RUNPATH 的 relocatable 包（此时可用
  `CMAKE_INSTALL_RPATH` 显式指定，但 OHOS 上可靠性存疑）

## 关联条目
- `caused_by: E537`（patchelf 重写 ELF 在 OHOS 被拒——E537 侧重 DT_NEEDED
  绝对路径 + 链接期 SONAME，E581 侧重 cmake.install() 安装期 RPATH 重写）
- `similar_to: E274`（安装后库无法加载的 SONAME 符号链接视角）
- `similar_to: E330`（CMake SONAME 符号链接创建被拒视角）

## 与 E537 的差异（重要）
E537 的根因是"KF6 依赖库无 SONAME → DT_NEEDED 记录绝对路径"，方案是
链接期 SONAME basename；E581 的根因是"库本身 SONAME 正常，但 cmake.install()
默认用 patchelf 重写 RPATH 破坏 OHOS ELF"，方案是 CMAKE_SKIP_RPATH=TRUE。
两者错误特征相似（Error loading shared library）但根因、修复方案、适用
边界不同，故保留为独立草稿并相互关联。

---
*草稿（draft），待主编 promote 为正式条目*
