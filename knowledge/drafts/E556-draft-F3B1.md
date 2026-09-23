# E556-draft-F3B1: CMake install(FILES) 引用构建目录路径但文件仅存在于源码目录

## 基本信息
- **严重度**: 2（🟡 中，构成 conan create package() 阶段阻塞但修复简单）
- **类别**: cmake, build-system, packaging
- **来源**: check 0.11.0 OHOS 适配（pc2-16, 2026-09-16）
- **状态**: 草稿（待审核提升）
- **similar_to**: E555（同阶段 `file INSTALL cannot find`，根因/方案不同）

## 错误特征
```
file INSTALL cannot find "/storage/.../build/Release/lib/libcompat.h": No such file or directory
cmake_install.cmake:45 (file)
  file INSTALL cannot find ...
Call Stack (most recent call first):
  cmake_install.cmake:46 (include)
ERROR: check/0.11.0@ohpcd/stable: Error in package() method
	cmake.install()
	ConanException: Error 1 while executing
```

## 根因分析
上游 `lib/CMakeLists.txt` 写入：

```cmake
install(FILES ${CMAKE_BINARY_DIR}/lib/libcompat.h DESTINATION include)
```

该写法假设 `libcompat.h` 是构建阶段生成物（类似 `configure_file` 产物，只存在于构建目录）。
实际上它是源码目录中的静态头文件（`lib/libcompat.h`），构建目录中不存在 `build/Release/lib/libcompat.h`，
因此 `cmake --install` 执行安装清单时必然报 `file INSTALL cannot find`，配方 `package()` 阶段整体失败。

## 推荐方案
将 `install(FILES ...)` 中错误的构建目录路径改为源码目录路径：

```cmake
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/libcompat.h DESTINATION include)
```

判定要点：
1. `stat` 确认该文件是否真实存在于源码目录；若存在 → 改 `${CMAKE_CURRENT_SOURCE_DIR}`
2. 若该文件确为 configure_file/自定义生成目标的产物（只存在于构建目录）→ 改 `${CMAKE_CURRENT_BINARY_DIR}`
   并确认生成目标先于 cmake --install 执行（否则属 E555 构建闭包问题而非路径笔误）

## 验证
- 应用补丁后 `conan create` / `conan-verify G2` 通过（check/0.11.0 实证：G0-G4 + L2/L4/L5 全 PASS）
- `finish` W3 本地 CI 模拟通过（.ci-result.json exit_code=0）
- 复验命令：`grep -rn "install(FILES.*CMAKE_BINARY_DIR.*\.h" <src>/CMakeLists.txt` 应无残留

## 适用边界与反例
- **适用**：上游 `install(FILES ${CMAKE_BINARY_DIR}/...)` 引用源码目录静态头文件的旧 CMake 工程（与平台无关，OHOS/常规 Linux 均会失败）
- **反例**：若头文件确实由 configure_file 或 custom target 生成（构建树产物、源码目录无此文件），本方案不适用，应检查生成目标是否进入构建闭包（见 E555）
- **与 E555 区别**：E555 根因是 `--target` 定向构建绕过 ALL 生成目标 + 平台门控选项默认 OFF，产物从未生成；本条目根因是 install 规则路径笔误，文件一直存在只是目录写错

## 查重结论（同 stem 草稿依据）
- `exact_duplicate`：否
- `causal_duplicate`：否（E555 生成物缺构建 vs 本条目源码文件路径写错）
- `trigger_overlap`：部分（均为 cmake --install 阶段 `file INSTALL cannot find`）
- `solution_overlap`：低（E555 修构建闭包/选项门控；本条目改 install 路径一行）
- `combination_novelty`：是（与 E555 组合形成 CMake install 失败完整谱系：未生成 vs 路径错误）
- `boundary_novelty`：是
- 关系：`similar_to=E555`，无 conflicts_with

### E555 部分覆盖差异（R02 补充，similar_to 关系明细）

**已覆盖部分**（E555-draft-9C21 / E555-draft-A7F3）：
1. `error_signature`：`file INSTALL cannot find "<…>"` 错误签名（两稿共享同一触发面）
2. 根因类别：CMake install 清单引用构建树中不存在的文件
3. 修复处：cmake_cmake --install 阶段（package()/install）

**本轮新增部分**（E556 独立价值）：
1. 根因细分：E555 = 产物**从未生成**（--target 定向构建绕过 ALL 生成目标 + `if(UNIX OR MINGW)` 平台门控选项默认 OFF，.pc/软链/生成头缺失）；E556 = 产物**一直存在但 install 路径字面量写错目录**（`${CMAKE_BINARY_DIR}/lib/…` vs 源码目录静态头文件）
2. 修复方向细分：E555 = 构建完整闭包/修正选项门控（多文件、构建链问题）；E556 = 改一行 `${CMAKE_CURRENT_SOURCE_DIR}`（路径字面量笔误）
3. 判定要点：E556 先 `stat` 判定文件真实位置；若确为构建期生成物才回到 E555 闭包诊断
4. E555 无法覆盖本候选：其 match_keywords 不含 source-dir/build-dir 路径笔误变体，engine 以本错误实测仅弱命中 E050（HMDFS 软链，无关）

**结论**：E555 部分覆盖（仅 error_signature 与阶段），根因/方案/判定边界均属新增差异，成立 new_draft。

## 验证/命令
```bash
# 判定文件位置
stat lib/libcompat.h

# 修复
sed -i 's|install(FILES ${CMAKE_BINARY_DIR}/lib/libcompat.h|install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/libcompat.h|' lib/CMakeLists.txt

# 复验
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```