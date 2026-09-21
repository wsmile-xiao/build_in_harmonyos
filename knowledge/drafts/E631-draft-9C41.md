# E631 — CMake 视 HarmonyOS 为未知平台：SONAME/RUNPATH 标志与 UNIX 变量全缺，且 install 期 RPATH 改写破坏 OHOS 签名

- **id**：E631（草稿）
- **来源任务**：liblsl 1.18.0.b2（OHOS 适配，2026-09-20）
- **触发工具**：cmake / conan / clang / readelf
- **严重度**：3（本地假绿 + 产物不可加载 + 破坏代码签名，三种表现同时出现）
- **环境**：HarmonyOS PC aarch64，clang 15.0.4（HNP `ohos-sdk_26.0.0.18`），CMake 4.1.2，Conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（`os=OHOS`）

## 1. 现象（三个层次，全是假绿形态）

### 1.1 共享库没有 SONAME

CMake 报（每个 `try_compile` 都打一次，容易被当成噪声刷掉）：

```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org
```

上游 `set_target_properties(lsl PROPERTIES VERSION 1.18.0 SOVERSION 2)` 明明写了，
产物却**只有文件名带版本、ELF 里没有 `DT_SONAME`**：

```
$ readelf -d liblsl.so.1.18.0 | grep SONAME
（空）
```

→ 消费者链接时 `DT_NEEDED` 只能记路径，不可重定位。

### 1.2 完全写不进 RUNPATH

```
$ readelf -d lslver | grep RUNPATH
（空）
$ env -u LD_LIBRARY_PATH ./lslver
Error loading shared library liblsl.so.2: (needed by ./lslver)
Error relocating ./lslver: lsl_library_version: symbol not found
```

`bin/` 下的工具只能靠 `LD_LIBRARY_PATH` 活着 —— 这正是 CI 的 L2「裸 PATH smoke」
能漏出、而 `test_package`（conanrun 注入 `LD_LIBRARY_PATH`）永远绿的那类假绿。

### 1.3 install 期 RPATH 改写破坏 OHOS 代码签名

最小探针（`$TASK_DIR/probe-cmake`，见 §5）实测：

```
$ sha256sum probetool ; cmake --install . --prefix $PREFIX ; sha256sum $PREFIX/bin/probetool
6191fb05e72dcd8d66fd3f585ddb42fac32f6b5a31c862f5915137277da1318f  probetool          # 安装前
5545692d455a86aee17fa66ab3a58dabf919381eeba1d215fd8d5c4ed9cf8454  .../bin/probetool  # 安装后（被改写）
$ env -u LD_LIBRARY_PATH $PREFIX/bin/probetool
env: exec .../bin/probetool: Operation not permitted        # rc=126，EACCES 而非 not found
```

措辞「Operation not permitted」极易被读成权限/属主问题（HMDFS 权限位那类），
实际是 RPATH 就地改写让 `.note.ohos.ident` 代码签名失效。

## 2. 根因

1. Conan 的 `CMakeToolchain` 把 `settings.os=OHOS` 映射成
   `CMAKE_SYSTEM_NAME=HarmonyOS`（`conan/tools/cmake/toolchain/blocks.py` 的
   `cmake_system_name_map = {"OHOS": "HarmonyOS", ...}`）。
2. 设备上的 CMake 4.1.2 **只有 `Modules/Platform/OHOS.cmake`**（内容仅
   `include(Platform/Linux)`），**没有 `Platform/HarmonyOS.cmake`**；而 `OHOS.cmake`
   只在 `CMAKE_SYSTEM_NAME=OHOS` 时被命中，于是 `HarmonyOS` 落回 generic 平台模块。
   这些变量因此保持为空：
   ```
   CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG      -> 无 -Wl,-soname,
   CMAKE_SHARED_LIBRARY_RUNTIME_{C,CXX}_FLAG     -> 无 -Wl,-rpath,
   CMAKE_SHARED_LIBRARY_RUNTIME_{C,CXX}_FLAG_SEP -> 无分隔符
   CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN       -> 无 $ORIGIN 令牌
   CMAKE_EXECUTABLE_RUNTIME_{C,CXX}_FLAG         -> 同上
   ```
3. 同一根因还让 **CMake 的 `UNIX` 变量根本不存在**：它由
   `Platform/<system>-Initialize.cmake` 设置，没有 `HarmonyOS-Initialize.cmake`
   就没人 `set(UNIX 1)`（实测 build 目录 `CMakeCache.txt` 里**连 `UNIX` 条目都没有**）。
   于是上游 `cmake/CompilerSettings.cmake` 的
   `elseif(UNIX AND NOT ANDROID) set(CMAKE_INSTALL_RPATH "$ORIGIN;$ORIGIN/../lib")`
   整支被跳过 —— 即使补上了 RUNPATH 链接标志，RPATH 值依然是空的。
4. 补上 RPATH 之后还有第二道坎：若「构建期 RPATH ≠ 安装期 RPATH」，
   `cmake --install` 会对 ELF 做 `file(RPATH_CHANGE ...)` 就地改写 → 破坏签名（§1.3）。

## 3. 修法（配方侧，无源码补丁）

```python
# generate()
rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
save(self, rules, "\n".join([
    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
    'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
    'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
    'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_CXX_FLAG "-Wl,-rpath-link,")',
    'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
    'set(CMAKE_EXECUTABLE_RUNTIME_C_FLAG "-Wl,-rpath,")',
    'set(CMAKE_EXECUTABLE_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
]))
tc.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules     # 关键：用 variables 不用 cache_variables
tc.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules
tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"   # UNIX 未定义，上游不会设
tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"            # 构建期就带最终 RPATH → install 不改写
```

三点理由：

- **为什么用 `CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}`**：该文件在
  `CMakeCInformation.cmake` / `CMakeCXXInformation.cmake` 里、**平台模块之后**才被
  `include()`，因此能覆盖平台模块给的（这里其实是「空」）值；同时它天然早于任何
  target 创建。先例 `archives/c/curl/8.15.0.1/conanfile.py`。
- **为什么用 `tc.variables` 而不是 `tc.cache_variables`**：`cache_variables` 只写进
  `CMakePresets.json` 与打印出的命令行，**不进 `conan_toolchain.cmake`**；只要有人
  用 `-DCMAKE_TOOLCHAIN_FILE=...` 手工 configure，这些修正就静默消失。
- **反过来的例外**：像「版本号覆盖」这类必须**在 `project()` 之前**可见的变量
  （liblsl 的 `LSL_VERSION_OVERRIDE` 在 `project()` 之前就被读）**必须**用
  `cache_variables`（`-D` 形式），只写 `tc.variables` 会静默失效（本轮实测：产出
  `liblsl.so.1.17.7`、`lsl_library_version()` 返回 117）。两者语义不同，别互相替代。

自证：

```
$ readelf -d $PKG/lib/liblsl.so.1.18.0 | grep -E 'SONAME|RUNPATH'
  (SONAME)  Library soname: [liblsl.so.2]
  (RUNPATH) Library runpath: [$ORIGIN;$ORIGIN/../lib]
$ readelf -d $PKG/bin/lslver | grep RUNPATH
  (RUNPATH) Library runpath: [$ORIGIN;$ORIGIN/../lib]
$ env -u LD_LIBRARY_PATH $PKG/bin/lslver --version ; echo rc=$?
LSL version: 118
git:v1.18.0.b2/branch:conan/build:Release/compiler:Clang-15.0.4/link:SHARED
<时钟值>
rc=0
# 安装前后逐文件一致（无签名破坏）
$ sha256sum $BUILD/liblsl.so.1.18.0 $PKG/lib/liblsl.so.1.18.0     # 两行相同
```

## 4. 不推荐的替代路线（实测反例）

`tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（449 个配方在用，最省事）：
让 `Platform/Linux.cmake` 生效确实补上了所有标志，但 **`CMAKE_HOST_SYSTEM_NAME`
仍是 HarmonyOS ⇒ `CMAKE_CROSSCOMPILING=TRUE`**，且实测该路线下 `cmake --install`
**真的改写了 ELF**（sha256 变化 + 落地可执行文件 exec 报 `Operation not permitted`），
还得再叠一层 `CMAKE_BUILD_WITH_INSTALL_RPATH`。既然要叠，不如直接用上面的窄修法，
把 `CMAKE_SYSTEM_NAME` 留在 `HarmonyOS`（与 conan 的映射一致，也不引入
cross-compiling 语义）。

## 5. 复现命令（设备可直接执行）

```sh
TASK_DIR=/storage/Users/currentUser/tmp/liblsl-1.18.0.b2
# ① 观察平台变量为空
cmake --version | head -1
ls /data/service/hnp/cmake.org/cmake_4.1.2/share/cmake-4.1/Modules/Platform/ | grep -E '^(OHOS|HarmonyOS)'
#   -> 只有 OHOS.cmake（内容 include(Platform/Linux)），没有 HarmonyOS.cmake
cat /data/service/hnp/cmake.org/cmake_4.1.2/share/cmake-4.1/Modules/Platform/OHOS.cmake

# ② 最小探针：SONAME / RUNPATH / install 改写 / 裸跑（约 20 秒）
#    探针工程在 $TASK_DIR/probe-cmake（conan install 出的 toolchain + 一个小 .so + 一个 exe）
cd "$TASK_DIR/probe-cmake" && rm -rf b && mkdir b && cd b
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE_C="$TASK_DIR/probe-cmake/cmake/ohos_rules_c.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE_CXX="$TASK_DIR/probe-cmake/cmake/ohos_rules_cxx.cmake" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
cmake --build .
readelf -d libprobe.so.1.2.3 | grep -E 'SONAME|RUNPATH'
cmake --install . --prefix "$TASK_DIR/probe-prefix3"
sha256sum probetool "$TASK_DIR/probe-prefix3/bin/probetool"     # 必须相同
env -u LD_LIBRARY_PATH "$TASK_DIR/probe-prefix3/bin/probetool"  # 必须 rc=0

# ③ 去掉规则文件再跑一遍 -> 无 SONAME / 无 RUNPATH（修前复现）
```

## 6. 检索线索

- 日志关键词：`System is unknown to cmake, create`、`Platform/HarmonyOS`、
  `Error loading shared library <lib>.so`、`Operation not permitted`（exec 阶段）、
  `(RUNPATH)` 缺失、`L2_RESULT` 里 bin/ 工具失败而 `test_package` 全绿。
- 判据文件：`notes/device-facts.md` §一（设备边界）、`AGENTS.md` §3.3（采信轮）。
- 同族条目：`DRAFT-libharu-2.3.0-missing-dt-soname`（只覆盖 SONAME 一层）、
  `E481`。
