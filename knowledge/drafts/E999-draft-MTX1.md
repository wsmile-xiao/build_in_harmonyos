# E999-draft-MTX1 — OHOS 上 CMake 不实现 VERSION/SOVERSION：目标属性正确仍不产生 -soname 与版本化文件名

> **状态**：`draft: true`（路径 B 候选）
> **来源**：mtxclient 0.10.1 适配（PR #13832，commit `c770174d37`）
> **平台**：HarmonyOS PC / aarch64 / CMake 4.1.2 / clang 15.0.4
> **关联**：E207（HarmonyOS CMake 相对路径链接 / SONAME 缺失）、E274（打包时 SONAME 符号链接缺失）、E050（HMDFS 符号链接不可靠）
> **非重复声明**：`knowledge/drafts/DRAFT-openjpeg2-hmdfs-versioned-soname.kv` 讲的是「设了 VERSION/SOVERSION 后 HMDFS 拒绝创建符号链接」，本条讲的是「**OHOS CMake 根本不落实 VERSION/SOVERSION**」；两者的观测与修法互补，不是同一问题（详见「与既有草稿的边界」）。

## 错误特征

ELF 质量门禁/下游消费侧报出：

```
[fail] L5a: libmatrix_client.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE — 下游必须按完整路径链接
```

或在只补了版本化文件名、没补未版本化文件名时，运行期：

```
Error relocating ./test_package: _ZN3mtx6crypto7decryptE...: symbol not found
ConanException: Error 127 while executing
```

## 根因

OHOS 平台的 CMake **不把 target 的 `VERSION`/`SOVERSION` 属性落实为链接器行为**。
`get_target_property` 能读到属性值，但生成的链接行没有 `-soname`，产物文件名也不带版本号。

### 最小复现（与业务库无关，纯 CMake）

```cmake
cmake_minimum_required(VERSION 3.11...3.13)
project(prov VERSION 0.10.1 LANGUAGES CXX)
add_library(provlib)
target_sources(provlib PRIVATE prov.cpp)
set_target_properties(provlib PROPERTIES
  VERSION ${PROJECT_VERSION}
  SOVERSION ${PROJECT_VERSION})
get_target_property(_t provlib TYPE)
get_target_property(_v provlib VERSION)
get_target_property(_s provlib SOVERSION)
message(STATUS "probe: TYPE=${_t} VERSION=${_v} SOVERSION=${_s}")
```

设备上实测输出与产物：

```
-- probe: TYPE=SHARED_LIBRARY VERSION=0.10.1 SOVERSION=0.10.1
build/libprovlib.so                      ← 无版本化文件名
link.txt 中 -soname 匹配数：0            ← 链接行无 soname
llvm-readobj --dynamic-table build/libprovlib.so → 无 SONAME 条目
```

即：**类型对、属性对，平台不实现**。

### 三个连锁后果

1. 库无 `DT_SONAME` → SONAME 质量门禁失败，下游无法按 soname 寻址。
2. `install` 也只写出未版本化文件名（`-- Installing: .../libmatrix_client.so`，没有任何 `.so.<ver>`）。
3. 导出的 `XxxTargets-release.cmake` 把导入目标标为 `IMPORTED_NO_SONAME TRUE`，下游被迫按完整路径链接。

## 触发条件

- 平台：OHOS（HarmonyOS PC / aarch64），CMake 4.x（实测 4.1.2）
- 目标类型：`SHARED_LIBRARY`（`add_library()` 空参数 + `BUILD_SHARED_LIBS=ON` 亦同）
- 与「是否设置了 VERSION/SOVERSION」无关：**设置了也不生效**

## 推荐方案（本库采用）

三步，缺一不可：

1. **显式把 soname 交给链接器**（补丁，只改 CMake 语法）：

```cmake
set_target_properties(matrix_client PROPERTIES
  VERSION ${PROJECT_VERSION}
  SOVERSION ${PROJECT_VERSION})
set(_mtx_soname "libmatrix_client.so.${PROJECT_VERSION}")
target_link_options(matrix_client PRIVATE "LINKER:-soname,${_mtx_soname}")
```

2. **构建树补 soname 别名**，否则 ctest 无法解析测试二进制的 `DT_NEEDED`：

```python
_so = os.path.join(self.build_folder, "libmatrix_client.so")
_soname = os.path.join(self.build_folder,
                       "libmatrix_client.so.%s" % self.version)
if os.path.exists(_so) and not os.path.lexists(_soname):
    os.symlink("libmatrix_client.so", _soname)
```

3. **包内物化 soname 文件名**：运行期加载器按**文件名**（而非 soname）解析 `DT_NEEDED`，
   只留未版本化文件会得到 `symbol not found` / exit 127。因此 `package()` 里把版本化名
   写成真实文件；不要用符号链接（HMDFS 不可靠，E050）：

```python
plain = os.path.join(lib, "libmatrix_client.so")
versioned = os.path.join(lib, "libmatrix_client.so.%s" % self.version)
if os.path.exists(plain) and not os.path.lexists(versioned):
    shutil.copy2(plain, versioned)
```

### 验证

```
llvm-readobj --dynamic-table p/lib/libmatrix_client.so | grep SONAME
  → 0x000000000000000E SONAME  Library soname: [libmatrix_client.so.0.10.1]
ls p/lib/  → libmatrix_client.so 与 libmatrix_client.so.0.10.1 同时存在（均为真实文件）
test_package 能加载并跑完全部 39 项断言
```

## 回退方案

若 ABI 不要求版本化 SONAME，可只做「跳过 VERSION/SOVERSION」这一步（openjpeg2 草稿的做法）。
但要注意：**该回退只规避 HMDFS 符号链接失败，不能修好「库缺 DT_SONAME」**。
本条的观测恰恰是「设了属性也不会有 soname」，所以两者是互补关系。

## ★ 禁止策略 ★

- 不要用 `patchelf` 事后改动态段：会破坏 OHOS 产物内嵌签名，导致无法加载
  （参见 `DRAFT-patchelf-breaks-ohos-signing.kv`）。
- 不要在补丁里用空壳 `#ifdef __OHOS__` 绕过（R8）。

## 与既有草稿的边界

| 条目 | 讲的是什么 | 与本条的关系 |
|------|-----------|-------------|
| `DRAFT-openjpeg2-hmdfs-versioned-soname.kv` | 设了 VERSION/SOVERSION 后，HMDFS 工作目录拒绝创建符号链接 → `cmake_symlink_library` 失败 | 同族但不同观测：那条的失败点在「创建符号链接」，本条的失败点在「CMake 压根不生成 soname 与版本化文件名」。openjpeg2 的修法是关闭版本化；本条的修法是显式补 soname |
| E207 | HarmonyOS CMake 链接同项目内库时用相对路径而非 SONAME | 同族：本条给出该现象的底层原因（无 DT_SONAME）与可复现判据 |
| E274 | 打包时漏了 SONAME 符号链接，运行期解析 NEEDED 失败 | 本条的第 3 步正是该失效模式在 OHOS 上的成因 |
| E050 | HMDFS 符号链接不可靠 | 本条据此要求「用真实文件而非符号链接」 |

## 备注：本条不解释的两个近似报错

下列两个报错与 SONAME 无关，不属于本条的 `error_signature`，遇到时不要套用本条的修法：

| 报错 | 真实机制 | 记录位置 |
|------|---------|---------|
| `The link interface of target "..." contains: GTest::GTest but the target was not found` | googleTest 1.13 起把导出目标改名为 `GTest::gtest`/`GTest::gtest_main`，1.14 删除旧名；上游链接旧名即失败，与平台无关 | `archives/m/mtxclient/0.10.1/notes.md`、`manifest.yaml`、`patches/0002-cmakelists-gtest-targets.patch` |
| `Could not find a package configuration file provided by "olm"` | 生成器未运行（`generators` 未声明为类属性），依赖本身已正确发布 | 本目录 `E999-draft-MTX3` |

## 备注：门禁工具可用性

L5 门禁用 `readelf -d` 读 `DT_SONAME`。若执行机**没有 `readelf`**（例如只有 `llvm-readobj`），
`ELF_INFO` 恒为空，L5a/L5b 会无条件失败——这与库本身是否正确无关。
诊断时应改用 `llvm-readobj --dynamic-table` 复核。该设备上任何产出 `.so` 的包都会如此。
