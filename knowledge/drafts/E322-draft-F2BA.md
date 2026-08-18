# E322 — OHOS shared library missing SONAME due to absent Platform/HarmonyOS.cmake

## 错误特征
CMake 构建 shared library (.so) 成功，无任何编译/链接错误，但产物 ELF 动态段缺少 SONAME 字段：
```
$ readelf -d libfoo.so
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
# 期望出现但缺失:
# 0x000000000000000e (SONAME)            Library soname: [libfoo.so.<major>]
```
L5 门禁 (soname_gate) 报 `soname_gate_failed`，readelf -d 无 SONAME 输出。

## 触发条件
- 构建系统: cmake (4.x)
- 阶段: build/linking → verification (L5 soname gate)
- 平台: CMAKE_SYSTEM_NAME 解析为 HarmonyOS/OHOS 时触发
- 前提: 项目 CMakeLists.txt 用 `SET_TARGET_PROPERTIES(... SOVERSION <major>)` 声明了 SOVERSION

## 根因分析
CMake 4.x 不附带 `Platform/HarmonyOS.cmake` 平台模块。Linux 平台模块 (`Platform/Linux.cmake`) 会设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"`，但无 HarmonyOS 等价模块时该变量为空。

链接模板 `CMAKE_C_CREATE_SHARED_LIBRARY` 包含 `<SONAME_FLAG><TARGET_SONAME>` 占位符。当 `SONAME_FLAG`（即 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`）为空时，占位符展开为空字符串，`-Wl,-soname,<soname>` 未传递给链接器，生成的 .so 不含 SONAME 字段。项目声明的 `SOVERSION` 属性对二进制无效果。

## 解决方案

### 推荐方案 (conan-recipe-soname-flag)
在 conanfile.py `generate()` 中通过 `tc.cache_variables` 显式设置 soname flag：
```python
def generate(self):
    tc = CMakeToolchain(self)
    # CMake 4.x 无 Platform/HarmonyOS.cmake, CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空
    tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
    tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
    tc.generate()
```
项目声明的 SOVERSION 会将 TARGET_SONAME 解析为 `libfoo.so.<major>`，配合此 flag 即可正确嵌入 SONAME。

### 回退方案 (patchelf-post-build)
若工具链层修复不可行，在 `package()` 的 `cmake.install()` 后用 patchelf 修补：
```python
import patchelf  # 或直接 self.run("patchelf --set-soname ...")
# 在 package() 中:
patchelf --set-soname libfoo.so.<major> <pkgdir>/lib/libfoo.so
```

### 禁止做法
- ❌ 设置 `CMAKE_SKIP_RPATH` / `CMAKE_NO_SONAME` / `NO_SONAME`：完全禁用 SONAME 会导致下游 DT_NEEDED 条目不可重定位，消费者仅在 Conan cache 精确路径存在时才能运行。

## 验证
```bash
# 修复后验证 SONAME 出现
readelf -d <lib>.so | grep SONAME
# 期望输出: Library soname: [libfoo.so.<major>]

# 确认 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 值
cmake --system-information 2>&1 | grep -i SONAME_FLAG
```

## 关联条目
- 相关: E092 (CMake 不认识 HarmonyOS 平台), DRAFT-expat-cmake-soname-1912 (HMDFS symlink + soname)
