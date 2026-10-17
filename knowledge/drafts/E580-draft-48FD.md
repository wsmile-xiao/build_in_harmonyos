# E580: CMAKE_SYSTEM_NAME=OHOS 直接解决 CMake 平台识别+SONAME+插件DT_NEEDED

## 基本信息
- **严重度**: 2
- **类别**: cmake, platform, detection, linking, ohos
- **来源**: libdrumstick 2.10.0 HarmonyOS PC 适配（conan-verify 第 7 轮）
- **草稿编号**: E580

## 错误特征
```
System is unknown to cmake, create: Platform/HarmonyOS to use this system,
please post your config file on discourse.cmake.org
```

伴随现象（平台模块缺失的连带缺陷）：
- `readelf -d lib/*.so` 无 `Library soname:` 字段（库不生成 SONAME）
- 插件/子目录库的 `DT_NEEDED` 记录相对路径（如 `../../../lib/libdrumstick-rt.so`），运行期从插件目录解析错位，报 `Error loading shared library`
- `rtTest`/`widgetsTest` 等上游测试无法加载库而失败

## 触发条件
- 使用 Conan 2 + CMakeToolchain 适配 OHOS 目标
- OHOS conan profile 将 `CMAKE_SYSTEM_NAME` 默认映射为 `HarmonyOS`
- CMake 版本 4.1.x（自带 `Platform/OHOS.cmake`，但**没有** `Platform/HarmonyOS.cmake`）
- 项目构建共享库（.so）或子目录插件库

## 根因分析
Conan 的 OHOS toolchain（`ci/conan/profiles/ohos-aarch64`）把目标系统标识为
`HarmonyOS`。CMake 4.1.x 自带 `Modules/Platform/OHOS.cmake`（内容为
`include(Platform/Linux)`），但没有 `Platform/HarmonyOS.cmake`。当
`CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 找不到对应平台模块，configure 阶段
报 "System is unknown to cmake"。此时 CMake 回退到无平台模块的构建路径，
产生三个连带缺陷：

1. **SONAME 缺失**：Linux 平台模块（`Platform/Linux.cmake`）会设置
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`，无平台模块时该变量
   为空，链接模板不传 soname → `.so` 的 ELF dynamic section 无 SONAME。
2. **插件 DT_NEEDED 相对路径**：无平台模块时 CMake 对子目录目标生成相对
   路径 NEEDED（如 `../../../lib/libdrumstick-rt.so`），加载器从插件实际
   目录解析错位，`dlopen`/加载失败。
3. **平台宏不可靠**：`Q_OS_LINUX` 等平台相关宏判断受影响。

## 解决方案
**方法**: cmake-system-name-ohos

在 conanfile.py 的 `generate()` 中通过 CMakeToolchain 显式设置：

```python
tc = CMakeToolchain(self)
tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
```

CMake 据此加载 `Platform/OHOS.cmake`（等价 Linux 平台行为），同时修复：
- 平台识别（不再报 "System is unknown"）
- SONAME 正确生成（`Library soname: [libdrumstick-file.so.2]`）
- 插件 DT_NEEDED 用 SONAME（`libdrumstick-rt.so.2`）而非相对路径

实测：设置后 `ctest` 5/5 通过（fileTest1/2/3、rtTest、widgetsTest），
conan-verify G2/G3/G4 全部 PASS。

## 验证证据
- 修复前：configure 报 "System is unknown to cmake"，`readelf -d` 无 SONAME，rtTest 因插件加载失败
- 修复后：`readelf -d lib/libdrumstick-rt.so.2.10.0` 显示 `SONAME libdrumstick-rt.so.2`，插件 DT_NEEDED 为 `libdrumstick-rt.so.2`，上游 5 测试全部通过

## 适用边界
**适用**：Conan 2 + CMakeToolchain 适配 OHOS/HarmonyOS PC 的共享库/插件项目。

**不适用**：
- CMake 版本无 `Platform/OHOS.cmake`（较早版本需用 E092 的 Linux 映射或 E383 的手动 SONAME flag）
- 不需要 SONAME 的纯静态库（无影响但设置也无害）

## 关联条目
- `caused_by: E092`（CMake 不识别 HarmonyOS 平台）
- `similar_to: E383`（OHOS 库缺 SONAME：E383 用手动设置 SONAME flag 方案，E580 用 CMAKE_SYSTEM_NAME=OHOS 更直接且一并修复插件 DT_NEEDED）

---
*草稿（draft），待主编 promote 为正式条目*
