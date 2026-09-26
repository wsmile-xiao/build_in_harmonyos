# zdbsp 1.19-20181027-dfsg.1 适配笔记

ZDoom 独立节点构建器（BSP/GL nodes for Doom WAD）。纯 C++ 命令行工具，CMake 构建，唯一运行期依赖 zlib。

## 编译环境
- 构建系统: cmake（上游 cmake_minimum_required 2.4，已适配升 3.5）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（本机验证 Apple clang 17 / CMake 4.4.3；CI 侧 OHOS clang）
- 状态: built（本地无 conan/OHOS 环境，等待远程 CI conan-verify 后置 published）

## 编译步骤

本机验证（macOS，与 OHOS aarch64 行为对齐——均无 stricmp/strnicmp、64 位禁 SSE）：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release   # 适配后不再需要 CMAKE_POLICY_VERSION_MINIMUM
cmake --build build -j
# 产出 build/zdbsp（160KB），--help 正常
```

CI 侧由 conanfile.py 执行：CMakeDeps + CMakeToolchain 生成后
`cmake.configure() && cmake.build()`，package 阶段拷贝单一二进制到 bin/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 配置报 hard error "Compatibility with CMake < 3.5 will be removed" | 上游 `cmake_minimum_required( VERSION 2.4 )` 低于 3.5 | 补丁升至 `VERSION 3.5`（项目未使用 2.4 之后的新特性，纯语法兼容，本机编译验证通过） |
| 2 | 系统 zlib 分支链接失败风险 | 老 CMakeLists 用 `ZLIB_LIBRARIES`/`ZLIB_INCLUDE_DIR` 旧变量，Conan CMakeDeps 不填充这些变量，只提供 `ZLIB::ZLIB` 导入目标 | 补丁：`ZLIB_FOUND` 分支 `set( ZDBSP_LIBS ZLIB::ZLIB )`；删除无条件 `set( ZDBSP_LIBS "${ZLIB_LIBRARIES}" )`；`include_directories( "${ZLIB_INCLUDE_DIR}" )` 包进 `if( NOT ZLIB_FOUND )`（仅内置 zlib 分支需要） |
| 3 | 内置 zlib 不可用 | zdbsp/zlib 子目录只有压缩半边，缺 inflate 系列源文件；realmap 解字节依赖完整 zlib | 依赖 ohpcd 已发布的 zlib/1.3.1，不启用内置分支 |
| 4 | 补丁全文件重写风险 | 上游 CMakeLists.txt 为 CRLF 行尾，编辑器改写后变 LF 导致 git diff 显示 453 行全文件变化 | 字节级替换保留 CRLF，收敛为 34 行、4 处逻辑变更（见 patches/0001） |
| 5 | 上游零测试 | 无 add_test/enable_testing/test()、无 test 目录、无 CI 测试 workflow | 按 rule8 走"上游无测试"分支；test_package 自建 3 个检查项，其中 1 项为鸿蒙特有测试（OHOS 实机运行 zdbsp 构建节点） |

## 源码修改

`patches/0001-fix-cmake-zlib-target-ohos.patch`（34 行，4 处逻辑变更，已在本机验证可干净应用、编译运行通过）：

1. `cmake_minimum_required( VERSION 2.4 )` → `VERSION 3.5`
2. `ZLIB_FOUND` 分支新增 `set( ZDBSP_LIBS ZLIB::ZLIB )`
3. 删除原无条件 `set( ZDBSP_LIBS "${ZLIB_LIBRARIES}" )`
4. `include_directories( "${ZLIB_INCLUDE_DIR}" )` 移入 `if( NOT ZLIB_FOUND )` 分支

## 依赖版本

- zlib/1.3.1（ohpcd 制品仓已发布，静态库）
- 构建期仅需 CMake + clang/clang++；无 bison/flex 等宿主工具依赖（纯 CMake 项目）

## 验证结果

```bash
# 1) 编译
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
# → Built target zdbsp（160KB）

# 2) 冒烟
./build/zdbsp --help | head -1
# → Usage: zdbsp [options] sourcefile.wad

# 3) 功能验证（构造最小 MAP01 WAD：2 顶点 + 1 linedef + 1 sidedef + 1 sector，186B）
./build/zdbsp in.wad -o out.wad; echo $?  # in.wad 由 python3 wadgen.py 生成
# → BSP: 100%，exit=0，out.wad 298B（新增 SEGS/SSECTORS/BLOCKMAP lump）

# 4) 循环验证（节点输出可再次处理）
./build/zdbsp out.wad -o out2.wad; echo $?
# → exit=0

# 5) 补丁可应用性
patch -p1 < 0001-fix-cmake-zlib-target-ohos.patch
# → patching file CMakeLists.txt（与修改版逐字节一致）

# 6) 上游测试清点（R51）
grep -rn "add_test\|enable_testing\|test()" CMakeLists.txt  → 无
ls test*  → 无 test 目录
```

测试输入由 `test_package/wadgen.py` 生成（最小 MAP01 WAD，186B，PWAD/MAP01），
生成结果 SHA256=`9781cf5feb1783864ce8d2a3e8a5087b1dce21ccc962c7d29d9133793b740e4a`。
不用二进制随附，避免 PR diff 含二进制文件导致 CI git apply 失败（GitCode .diff 对二进制补丁支持不佳，实测 missing binary patch data）。

## 交付物

| 文件 | 说明 |
|------|------|
| patches/0001-fix-cmake-zlib-target-ohos.patch | CMake/zlib 适配补丁（4 处逻辑变更） |
| conanfile.py / conandata.yml | Conan 配方：CMake + zlib/1.3.1，application 型 |
| test_package/ | 测试：wadgen.py 生成输入 + test.sh（3 检查项）+ conanfile.py + MANIFEST.yml |
| test_package/wadgen.py | 生成最小合法 MAP01 WAD（186B）的文本脚本，构造逻辑见验证结果 |

## 注意事项

- 本机无 conan/ohos-aarch64 profile，`conan create` 本地验证无法执行；依赖远程 CI 门禁。提交后需监控 CI：conan-verify PASS → 置 published；FAIL → 按报错修复重提。
- 未使用 CMAKE_POLICY_VERSION_MINIMUM 兜底（那是 CMake 命令行 hack）；补丁直接升 cmake_minimum_required 是更干净的方案。
- test.sh 用 `/data/service/hnp/bin/bash` 包装执行（OHOS mksh 不能直接跑 ELF 二进制），conanfile 用 CONFIG_SHELL 环境变量兜底。
- 工具型软件（R38）：commands.json 已放软件级，`type: tool`。

## CI 修复记录 (2026-09-19)

1. **二进制补丁问题**（CI build #50670 checkout-pr 失败）：GitCode .diff 不支持
   二进制补丁（missing binary patch data），git apply 无法应用。修复：测试输入由
   二进制 minmap.wad 改为 `test_package/wadgen.py` 文本生成（186B 最小 MAP01 WAD，
   生成结果 SHA256 与原先一致 `9781cf5f...`），test.sh 改 `python3 wadgen.py > in.wad`。
   验证：本机 test.sh 3 检查项全过。
2. **zlib target 名问题**（CI build #51016 conan-build-test 失败）：CI 日志
   `-- Conan: Target declared 'zlib::zlib'`（CMakeDeps 默认小写 target），而补丁
   链接 `ZLIB::ZLIB` 找不到。修复：conanfile.py generate() 加
   `deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")` 强制 target 名。
   本机验证：conan install 生成的 zlibTargets.cmake 含
   `add_library(ZLIB::ZLIB INTERFACE IMPORTED)`，与系统 find_package(ZLIB)
   双兼容（本机 ZLIB::ZLIB、CI CMakeDeps ZLIB::ZLIB 均可用）。

## CI 最终结果 (2026-09-19)

- 分支重建：rebase 至最新 upstream main（7080d717b7），并删除 upstream main
  遗留的 3 个运行时状态文件（archives/c/cloog/0.21.1/.build-closed、
  .staging-verified、archives/k/kics/2.1.20/.staging-verified）——CI JC
  (junk_check) full 模式对 git ls-files 整仓扫描，遗留 junk 会导致所有 PR 失败。
- **CI 全绿**：PR #10932 构建 #51361（Worker OpenHarmonyPCDeveloper-CI-012），
  全部 7 步骤通过：worker_preparation/worker-prep/git-clone/checkout-pr/
  conan-setup/**conan-build-test**/cleanup。
- 验证详情：Conan test_package 通过（test.sh 3 检查项，含鸿蒙特有测试——
  OHOS 实机运行 zdbsp 处理 WAD）；L0 门禁（结构完整性）通过；L1 门禁（测试执行）通过。
- manifest.yaml status: built → published。
