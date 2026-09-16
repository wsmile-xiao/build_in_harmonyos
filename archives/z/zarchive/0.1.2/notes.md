# zarchive 0.1.2 适配笔记

## 编译环境

- 构建系统: CMake（>= 3.15），`target_compile_features(zarchive PUBLIC cxx_std_20)`
- 平台任务: contrib-12339（zarchive 0.1.2），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 编译器: clang/clang++ 15.0.4
- 依赖: `zstd/1.5.7.1`（已发布）
- 上游: https://github.com/Exzap/ZArchive tag `v0.1.2`（GitHub API 实证：非 fork、未归档、C++、MIT）
- 源码 sha256: `676e2c6eb9a2aeece702a53f39ecf8f057bc4e032071ec6ee23e5ac6e358ceed`（本机与设备实拉逐字节一致）
- 状态: built（G0/G1/G2/G3 全过，库级 25/25 + CLI 级 7/7）

## 源码面貌（摸底结论）

- 主体 **C++**：`src/zarchivereader.cpp`、`src/zarchivewriter.cpp`（+ 一份 `sha_256.c`、4 个头）
- 交付形态：**静态库 + 命令行工具**（`add_library(zarchive)` + `add_executable(zarchiveTool)`，`OUTPUT_NAME zarchive`）。CLI 随包安装到 `bin/`（`cpp_info` 默认 bindirs 即 `bin`，消费者可直接取用），但**不放包级 `commands.json`**：仓内 262 个 `package_type=library` 且 `bindirs` 非空的包全部不放，该文件只属于 `package_type=application` 的 CLI 包；且 PF8 对声明了 bindirs 的包会反过来强制要求commands.json、而 PF9 又拒绝包级路径，二者对纯库包会互相锁死，故按仓库惯例不声明 bindirs、不放该文件
- 依赖：`find_package(zstd MODULE REQUIRED)`，走上游自带的 `cmake/Findzstd.cmake`（先 `find_package(zstd CONFIG QUIET)`，未命中则退到 pkg-config）
- 上游**无测试套件**：无 `tests/`、无 `*test*` 源文件、无 `include(CTest)`/`enable_testing()`/`add_test()`、无 ctest 注册项

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify zarchive 0.1.2 --project-dir "$PWD"
```

## 遇到的问题与解决方案

| # | 问题（预判依据） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Target "zarchive" links to target "zstd::zstd" but the target was not found` | conan 的 zstd 包 `package_info` 设了 `cmake_target_name="zstd::libzstd"`，只导出 `zstd::libzstd`；而上游 `Findzstd.cmake` 的名字归一化只覆盖 `zstd::zstd` / `zstd::libzstd_static` / `zstd::libzstd_shared`，`zstd_FOUND` 为真但 `zstd::zstd` 始终没被建出来 | 补丁 0001：在 `Findzstd.cmake` 既有的归一化链条上补 `elseif (TARGET zstd::libzstd)` 一支——这正是该文件存在的目的（把各种查找结果统一到 `zstd::zstd`），不改 `CMakeLists.txt`、不改链接语义、不影响非 conan 构建 |
| 2 | `find_package(zstd CONFIG QUIET)` 静默落空、退到 pkg-config 分支（而设备无 pkg-config） | OHOS 的 `conan_toolchain.cmake` 交叉模式把 `find_package` 限制在 `CMAKE_FIND_ROOT_PATH` 内且 `MODE_PACKAGE=ONLY`；CMakeDeps 生成的 `zstd-config.cmake` 在 generators 目录，默认不在查找根里 | `tc.variables["CMAKE_FIND_ROOT_PATH"] = [self.generators_folder]` + `CMAKE_FIND_PACKAGE_PREFER_CONFIG = True`（plutosvg/avogadrolibs 同款做法） |
| 3 | 上游无测试可继承 | — | test_package 覆盖两条真实链路：库级 C++ 消费者测试（打包→读回→逐字节比对，25 项断言）+ 已安装 CLI 的 shell 测试（打包/解包/三文件逐字节 `cmp`/失败码，7 项断言） |

## 源码修改

1 个补丁：`patches/0001-cmake-Findzstd-accept-conan-target-name.patch`
（在 `cmake/Findzstd.cmake` 的目标名归一化链条上补 `zstd::libzstd` 分支；语义等价，
只影响"用 conan 的 zstd 包"这一场景，非 conan 构建路径完全不变。）

## 依赖版本

- `zstd/1.5.7.1`（归档的压缩后端；由 `cpp_info.requires = ["zstd::zstd"]` 向消费者传播）

## 验证结果（设备实机实测，2026-09-14）

```text
✅   G1: PASS
✅   G0: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: zarchive 0.1.2
```

库级消费者测试（test_package，ctest + 直接执行）：

```text
ok 1 - MakeDir(sub/deep, recursive) succeeds
...
ok 23 - LookUp on a missing path returns ZARCHIVE_INVALID_NODE
ok 24 - second OpenFromFile succeeds
ok 25 - library-extracted file matches the original on disk
1..25
# 25 checks, 0 failures
```

CLI 级消费者测试（对已安装的 `bin/zarchive` 真实调用）：

```text
ok 1 - installed CLI exists and is executable: .../p/bin/zarchive
ok 2 - no-argument invocation prints usage
ok 3 - CLI packs a directory into an archive
ok 4 - archive file is non-empty
ok 5 - CLI extracts the archive
ok - extracted hello.txt is byte-identical to the source
ok - extracted sub/pattern.txt is byte-identical to the source
ok - extracted sub/deep.txt is byte-identical to the source
ok 6 - every extracted file is byte-identical to its source
ok 7 - extracting a missing archive fails with a non-zero exit code
```

## 可复用要点

本包沿用 libcaca 一轮沉淀的做法（见 `archives/l/libcaca/0.99.beta20/notes.md` 与
`knowledge/drafts/DRAFT-libcaca-0.99.beta20-autotools-ohos-shell-and-deps-env.md`）：
自实现 `_fetch()`（显式 CA 兜底 + 重试 + `.part` 原子改名 + sha256 校验）、
设备 job 首行 `mkdir` 互斥锁、`conan remove` 清缓存残留、tar 用 `COPYFILE_DISABLE=1`。
CMake 类库的两条 OHOS 要点（`CMAKE_FIND_ROOT_PATH` 指 generators、目标名归一化）
记于本包 manifest 的 `knowledge_gained`。
