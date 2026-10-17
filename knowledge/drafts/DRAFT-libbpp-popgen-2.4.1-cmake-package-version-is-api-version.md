# E645: 依赖包的 CMake 包版本是 libtool 的 API 版本，不是发布 tag

> 草稿状态：pending-editor-review（最终编号由主编确认）
> 交付实例：libbpp-popgen 2.4.1（Bio++ 家族，任务 #13070）
> 相邻条目：E498（CMakeDeps 的 include 目录契约）、E495（QT_HOST_PATH 交叉编译）——根因不同

## 错误特征

```
CMake Error at CMakeLists.txt:56 (find_package):
  Could not find a configuration file for package "bpp-seq" that is
  compatible with requested version "2.4.1".

  The following configuration files were considered but not accepted:
    .../libbpp-seq/2.4.1/p/lib/cmake/bpp-seq/bpp-seq-config.cmake,
    version: 12.0.0
```

或者反向：为了让 configure 通过，把请求版本硬改成发布 tag / 直接删掉版本约束。

## 根因

一批 autotools/libtool 时代的库用 libtool 的 `CURRENT:REVISION:AGE` 规则生成共享库版本，
并顺手用它生成 **CMake 包版本**：

```cmake
SET(${PROJECT_NAME}_VERSION_CURRENT  "14")   # 接口号
SET(${PROJECT_NAME}_VERSION_REVISION "0")
SET(${PROJECT_NAME}_VERSION_AGE      "2")    # 向后兼容跨度
MATH(EXPR ${PROJECT_NAME}_VERSION_MAJOR "${${PROJECT_NAME}_VERSION_CURRENT} - ${${PROJECT_NAME}_VERSION_AGE}")  # 12
SET(${PROJECT_NAME}_VERSION "${MAJOR}.${AGE}.${REVISION}")                                                     # 12.2.0
write_basic_package_version_file(... VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
```

于是 `<pkg>-config-version.cmake` 里的 `PACKAGE_VERSION` 是 **API 版本**，与发布 tag 无关。
Bio++ 实测（发布 tag 都是 2.4.1）：

| 包 | 发布 tag | `PACKAGE_VERSION` | 上游实际请求的版本 |
|---|---|---|---|
| bpp-seq | 2.4.1 | **12.0.0** | bpp-popgen: `find_package(bpp-seq 12.0.0 REQUIRED)` |
| bpp-core | 2.4.1 | **4.1.0** | bpp-seq 的 config: `find_package(bpp-core 4.1.0 REQUIRED)` |

两个方向的危害：

1. **按 tag 猜版本** → 请求 `bpp-seq 2.4.1`，CMake 报 "configuration files were considered
   but not accepted ... version: 12.0.0"，很容易被误判成"制品仓没发布这个包/包坏了"
   （本例中 `libbpp-seq/2.4.1` 其实已发布且可用）。
2. **为过配置而删掉版本约束** → 绕过 `SameMajorVersion` 的 ABI 兼容性检查，ABI 不匹配
   可能在 configure/编译期静默通过，运行期才崩。

交叉印证：`SOVERSION` 与 API 版本同源，`readelf -d libbpp-seq.so | grep SONAME`
给出 `libbpp-seq.so.12`，主版本号同为 12。

## 推荐方案

**判定（三处，按权威性排序）**

1. 依赖包自己的 `lib/cmake/<name>/<name>-config-version.cmake`：
   `grep -n PACKAGE_VERSION` → 这是 `find_package` 唯一认可的口径；
2. 依赖方上游 CMakeLists 里写的 `find_package(<dep> X.Y.Z)` —— 直接照搬最省事；
3. `readelf -d <dep_pkg>/lib/lib<dep>.so | grep SONAME` 交叉印证主版本。

```bash
# Bio++ 实测
$ grep -n PACKAGE_VERSION ~/.conan2/p/*/p/lib/cmake/bpp-seq/bpp-seq-config-version.cmake
12:set(PACKAGE_VERSION "12.0.0")
$ grep -n 'find_package *(bpp' bpp-popgen-2.4.1/CMakeLists.txt
56:find_package (bpp-seq 12.0.0 REQUIRED)     # 上游自己请求的就是 API 版本
```

**在 Conan 配方里：两套版本号各司其职**

```python
def requirements(self):
    self.requires("libbpp-seq/2.4.1")        # Conan 侧用发布 tag
# CMake 侧让上游走 Conan target（libbpp-seq::libbpp-seq）：
# ABI 匹配由 Conan 的 settings/package_id 保证，CMake 的版本字符串不再是判据。
```

若必须调用上游 config（依赖方 CMakeLists 写死了版本号且不便改），则把请求版本**显式对齐**
到 `PACKAGE_VERSION`，并在 `notes.md` 记录该值的来源（依赖包 config，不是发布 tag）。

## 实测证据（libbpp-popgen 2.4.1）

| 项目 | 内容 |
|---|---|
| 上游请求 | `bpp-popgen-2.4.1/CMakeLists.txt:56: find_package (bpp-seq 12.0.0 REQUIRED)` |
| 依赖包实际版本 | `libbpp-seq/2.4.1` 的 `bpp-seq-config-version.cmake: set(PACKAGE_VERSION "12.0.0")` |
| 嵌套请求 | `bpp-seq-config.cmake:33: find_package (bpp-core 4.1.0 REQUIRED)`（该包 config 版本 4.1.0） |
| 同族先例的笔误 | `archives/l/libbpp-seq/2.4.1/conanfile.py` 的注释写的是 `find_package(bpp-core 4.0.0 REQUIRED)`，实测 config 为 **4.1.0** —— 说明"按印象记版本号"本身就会出错，必须以 config 为准 |
| 处置 | 0001 补丁把依赖解析改到 Conan target，Conan 侧 `requires("libbpp-seq/2.4.1")` 保留发布 tag |

## 红线

- **禁止**按发布 tag 去请求 `find_package` 版本（会直接找不到 config）。
- **禁止**为了过配置而删掉版本约束（绕过 ABI 兼容性检查）。
- 版本口径的结论必须给出取数命令与来源文件，不接受"我记得是 X.Y.Z"。
