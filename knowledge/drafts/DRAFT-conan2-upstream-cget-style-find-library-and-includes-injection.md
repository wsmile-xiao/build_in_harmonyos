# DRAFT-conan2-upstream-cget-style-find-library-and-includes-injection：上游 CMake 用裸 find_library + 直接 #include 依赖头（cget 风格）时的 Conan 双注入

> Status: **Draft**（待审核 promote）| severity: `P2` | category: `conan` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-conan2-upstream-cget-style-find-library-and-includes-injection.kv`

---

**匹配关键词**：find_library not found, lzma.h file not found, cget, CMAKE_LIBRARY_PATH, extra_cxxflags, 上游测试编译失败, conan create

## 错误签名（error_signature）

```text
undefined reference to ...        # 只注入了库路径没注入头路径时，先头文件报错
fatal error: '<dep>.h' file not found
CMake Error: Could NOT find <Dep>  # find_library 变体
```

## 错误摘录（error_excerpt）

```text
shrinkwrap 1.2.0（真机 r2）:
/xz.hpp:8:10: fatal error: 'lzma.h' file not found
```

## 根因（root_cause）

一批上游 CMake 项目（典型：GitHub 上用 cget/requirements.txt 管依赖的库）在
CMakeLists 里**裸调 find_library(lzma/z/zstd)** 且源码**直接 #include <lzma.h>**
等依赖头——它们假设依赖已装进系统前缀（/usr、cget 工具链）。Conan 化后依赖在
各自包目录，两条链路同时断：

1. **链接定位断**：find_library 搜不到包目录里的 .a/.so；
2. **头文件定位断**：上游不会给测试目标加依赖 include 目录（连 INTERFACE
   target 都只 export 自己的 include/）。

只解决其一必死：注入 CMAKE_LIBRARY_PATH 后头文件仍报 not found（真机 r2 即此）。

## 推荐方案（rec_approach）

不改上游任何文件，在 conanfile.py 的 generate() 里"双注入"：

```python
tc = CMakeToolchain(self)
libdirs, incdirs = [], []
for dep in ("xz", "zlib", "zstd"):          # 按实际依赖替换
    libdirs.extend(self.dependencies[dep].cpp_info.libdirs)
    incdirs.extend(self.dependencies[dep].cpp_info.includedirs)
tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(libdirs)   # find_library 命中
tc.extra_cxxflags.extend("-I" + d for d in incdirs)      # 头文件命中
```

要点：用 extra_cxxflags 而不是覆盖 CMAKE_CXX_FLAGS（会冲掉工具链自带 flags）；
两个清单都从 cpp_info 聚合，依赖换版本配方零改动。

## 复用价值

所有"上游自带测试 + 依赖走系统路径假设"的 CMake 库（cget/requirements.txt
风格）Conan 化时通用；shrinkwrap 1.2.0 真机 r2 失败 → r3 全绿的实证。
`CMAKE_LIBRARY_PATH` 在知识图谱 0 命中（查重 2026-09-27）。
