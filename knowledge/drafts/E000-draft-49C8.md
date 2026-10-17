# E000-draft-49C8: CMake 4 不识别 HarmonyOS 平台导致 SONAME 缺失

## 错误特征

```
-- The C compiler identification is Clang 15.0.4
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org
...
Error loading shared library ../librazer/librazer.so: (needed by .../bin/razerd)
Error relocating .../razerd: razer_init: symbol not found
```

- `readelf -d librazer.so` 无 SONAME 字段（只有 NEEDED）
- `readelf -d razerd` 的 NEEDED 为 `../librazer/librazer.so`（相对路径），且无 RUNPATH/RPATH
- 安装到 `bin/` + `lib/` 分离布局后运行 razerd 报 `Error loading shared library ../librazer/librazer.so`

## 触发条件

- 使用 CMake 构建（本项目实测 CMake 4.1.2）
- 目标平台为 HarmonyOS/OHOS（或任何 CMake 不识别、无 `Platform/<Name>.cmake` 模块的新平台）
- 项目结构包含"项目内共享库 + 链接该库的可执行文件"（如 razercfg 的 librazer.so + razerd）

## 根因

CMake 对平台的识别决定其链接命名机制是否生效：

1. configure 阶段 CMake 报 `System is unknown to cmake`，说明没有 `Platform/HarmonyOS.cmake` 模块。
2. 因此 `set_target_properties(... VERSION x.y.z SOVERSION n)` 的链接器命名机制**未应用**——生成的共享库**没有 SONAME 字段**（正常情况下应为 `librazer.so.1` 并生成符号链接链）。
3. 同一项目内可执行文件链接该库时，CMake 使用库文件路径（`../librazer/librazer.so`）作为 NEEDED 名称，而非标准 SONAME。
4. 安装到 `bin/`（可执行文件）与 `lib/`（库）分离布局后，动态链接器按 NEEDED 中的相对路径 `../librazer/librazer.so`（相对当前工作目录）解析，找不到库 → 程序无法启动。

**关键点**：仅设置 RPATH/INSTALL_RPATH 无法修复——NEEDED 本身是相对路径而非标准 SONAME，链接器按 NEEDED 名称解析。

## 解决方案

### 推荐：LINK_FLAGS 显式注入 SONAME + RUNPATH（soname-link-flags-injection）

绕过 CMake 平台命名机制，直接通过链接器 flag 完成两件事：

```cmake
# 共享库 target：注入标准 SONAME
set_target_properties(razer PROPERTIES
    COMPILE_FLAGS ${GENERIC_COMPILE_FLAGS}
    VERSION 1.0.0
    SOVERSION 1
    LINK_FLAGS "-Wl,-soname,librazer.so")

# 可执行文件 target：注入 RUNPATH，使安装后（bin/ + lib/）可定位共享库
set_target_properties(razerd PROPERTIES
    LINK_FLAGS "-Wl,-rpath,'$ORIGIN/../lib'")
```

效果验证（razercfg 0.44 实测）：
- `readelf -d librazer.so` → `(SONAME) Library soname: [librazer.so]`
- `readelf -d razerd` → `(NEEDED) Shared library: [librazer.so]`（已从相对路径修正为标准名）+ `(RUNPATH) Library runpath: [$ORIGIN/../lib]`
- 安装到 `inst6/bin/razerd` + `inst6/lib/librazer.so` 后运行 `razerd -v` 正常输出 "Razer device service daemon"

### 回退：安装期符号链接/复制（create-soname-symlink）

若无法修改链接 flag，可在 conan `package()` 中为版本化 SONAME 创建符号链接或复制文件，使运行时解析成功（与 E274 同思路）：

```python
os.symlink("librazer.so", os.path.join(lib_dir, "librazer.so.1"))
```

## 验证方法

```bash
# 1. 确认平台不识别（configure 阶段）
cmake -B build 2>&1 | grep "System is unknown to cmake"

# 2. 确认共享库无 SONAME（修复前）
readelf -d build/librazer/librazer.so | grep SONAME   # 无输出

# 3. 确认 NEEDED 为相对路径（修复前）
readelf -d build/razerd/razerd | grep NEEDED          # ../librazer/librazer.so

# 4. 修复后重新检查（应见 SONAME + 标准 NEEDED + RUNPATH）
readelf -d build/librazer/librazer.so | grep SONAME   # librazer.so
readelf -d build/razerd/razerd | grep -E "NEEDED|RUNPATH"

# 5. 安装到 bin/ lib/ 分离布局后运行验证
install 后 ./bin/razerd -v   # 正常输出版本信息
```

## 适用边界

- **适用**：CMake 构建、项目内含共享库且可执行文件链接之、目标平台 CMake 不识别（HarmonyOS/OHOS 及同类新平台）。
- **不适用**：
  - 纯静态库项目（无 SONAME 概念）；
  - CMake 已识别平台（Linux/Windows/macOS 等），VERSION/SOVERSION 正常生效；
  - 可执行文件与库安装在同一目录（无分离布局问题）。

## 与已有条目关系（部分重复）

| 维度 | E207 | 本草稿 E000 |
|------|------|------------|
| 症状 | 同一项目内 CMake 链接使用相对路径 NEEDED，运行失败 | 相同 |
| 根因 | HarmonyOS 平台 CMake 链接行为（未涉及 SONAME 命名机制根因） | 明确为 CMake 不识别平台 → VERSION/SOVERSION 机制未应用 → 无 SONAME |
| 方案 | 仅临时 workaround（mkdir libxxx 目录 + bin 目录下运行），声明"RPATH 设置无效" | 根本修复：LINK_FLAGS 显式 `-Wl,-soname` + `-Wl,-rpath,$ORIGIN/../lib`，实测安装布局可运行 |
| 边界 | 依赖可执行文件在特定相对位置运行，非标准安装布局 | 标准 bin/ lib/ 分离安装布局可运行 |
| 验证 | strings 检查硬编码路径 | readelf 确认 SONAME/NEEDED/RUNPATH + 安装后实际运行 |

**新增价值**：E207 认为"RPATH 设置在此平台无效"、"需平台适配"；本草稿证明可通过 LINK_FLAGS 显式注入 SONAME + RUNPATH 在标准安装布局下根本修复，无需平台层修改，并给出完整的 readelf 验证证据链。

**关联条目**：
- `similar_to: E207`（同症状——同一项目内 CMake 链接相对路径 NEEDED，本草稿提供根本修复）
- `similar_to: E274`（SONAME 符号链接缺失场景，回退方案同源）
- `similar_to: E383`（同为 CMake 4 无 Platform/HarmonyOS.cmake 导致共享库无 SONAME；E383 通过 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 修复共享库侧，本草稿聚焦可执行文件侧 NEEDED 相对路径 + RUNPATH 注入，两者互补）
- `caused_by: E092`（CMake 不识别 HarmonyOS 平台，本问题由该平台缺陷引发）

**与 E383 的差异点**：
| 维度 | E383 | 本草稿 E000 |
|------|------|------------|
| 触发工具 | cmake/conan/readelf（共享库 SONAME 缺失） | cmake/ld/runtime（可执行文件链接内部库 + 安装布局运行失败） |
| 根因 | CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 → .so 无 SONAME | 同根因 + 同一项目内可执行文件 NEEDED 记录相对路径 ../libxxx/libxxx.so |
| 方案 | conan generate() 设 SONAME_C_FLAG（共享库侧） | LINK_FLAGS 注入 -soname（共享库侧）+ -rpath,$ORIGIN/../lib（可执行文件侧 RUNPATH） |
| 验证 | readelf -d lib*.so 看 SONAME | readelf 看 SONAME + NEEDED + RUNPATH，且安装 bin/lib 分离布局后实际运行 |
| 新增价值 | 无（既有） | 补充可执行文件侧 NEEDED 相对路径的修复（E383 未涉及）+ 安装布局运行验证证据链 |
