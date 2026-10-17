# DRAFT-E622-libheif-aom：libheif 插件子包的「三必修项」（宿主编译 → 插件可装载 → 安装后签名仍有效）

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-20
> Source: `libheif-aom` 1.23.0 适配（HarmonyOS PC，积分赛/新包）
> 对应：`knowledge/drafts/DRAFT-E622-libheif-aom-1.23.0-plugin-switch-matrix-and-vendored-codec.kv`
> 姊妹条：`DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage`（同族子包判类 / 交付面 / N 口径）

## 为什么是「三必修项」

libheif 1.19+ 把编解码后端做成**运行期由宿主 dlopen 的 MODULE 插件**。一个
`libheif-<codec>` 子包要真的可用，必须同时跨过三道坎，**任何一道没过，产物都表现为
"构建成功、装出来却不能用"**（只有第①道会显式编译失败）：

| # | 必修项 | 不过关的症状 | 何时暴露 |
|---|---|---|---|
| ① | `-D_LIBCPP_ENABLE_EXPERIMENTAL` | 宿主 `box.cc` 编译失败（3 errors） | 编译期（显式） |
| ② | `-DCMAKE_SYSTEM_NAME=Linux` | 宿主**没有 SONAME** → 插件 `DT_NEEDED` 写成含斜杠的相对路径 → `heif_init()` dlopen 失败 | 运行期（测试期） |
| ③ | `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` + `CMAKE_INSTALL_RPATH=""` | `cmake --install` 就地改写 RUNPATH → **破坏 OHOS ELF 代码签名** → 装出来的插件 `dlopen: … Permission denied` | 安装后（最隐蔽） |

三条的**共同点**：都能在"配置 rc=0、构建 rc=0、安装 rc=0、宿主可加载"的表象下
产出不可用（或缺失）的插件——判据必须落到**插件自身**（存在性、SONAME/DT_NEEDED、
安装前后 sha256、真 dlopen 一次），不能只看宿主或看构建日志全绿。

---

## 必修项 ①：libc++ 15 的 ranges 缺口 → 编译期宏，不打补丁

### 症状（逐字，clang 15.0.4 / libc++ 15004，`-j2`）

```text
libheif/box.cc:4155:23: error: no member named 'all_of' in namespace 'std::ranges'
libheif/box.cc:4156:25: error: no member named 'find' in namespace 'std::ranges'
libheif/box.cc:4166:22: error: no member named 'find' in namespace 'std::ranges'
3 errors generated.
```

配置阶段 rc=0、只有 build 阶段 rc=2；**不是缺头文件、不是 `-std` 没生效**。

### 根因机制（工具行号）

`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/c++/v1/__config`：

```cpp
39:  #  define _LIBCPP_VERSION 15004
254: #  if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)
255: #    define _LIBCPP_HAS_NO_INCOMPLETE_FORMAT
256: #    define _LIBCPP_HAS_NO_INCOMPLETE_RANGES      // ← 这一行把 <algorithm> 的 ranges 重载隐藏
```

上游 `CMakeLists.txt` 用 `set(CMAKE_CXX_STANDARD 20)`，`libheif/box.cc` 用了
`std::ranges::all_of/find` → 命中被隐藏的算法。
**判读陷阱**：粗粒度特性宏会撒谎——`__cpp_lib_ranges` 仍是 `201811L`，所以
"`#if __cpp_lib_ranges` 通过"不等于"ranges 算法可用"；只能信**真编译器探针**。

### 修法（先例：`archives/l/libpqxx/8.0.1`、`archives/l/ladybug/0.18.2`）

```python
if str(self.settings.os) in ("Linux", "OHOS"):
    tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None
```

不改上游源码、不需要 `-lc++experimental`。对照路线是把 `std::ranges::all_of/find`
换成 C++17 `std::all_of/find` 再打补丁——**能用开关就别打补丁**（R1；少一处上游漂移）。

### 最小复现（无需 libheif）

```sh
printf '#include <algorithm>\n#include <vector>\nint main(){std::vector<int> v{1};return std::ranges::find(v,1)==v.end();}\n' > "$TASK_DIR/ranges_probe.cc"
/data/service/hnp/bin/clang++ -std=c++20 -c "$TASK_DIR/ranges_probe.cc" -o "$TASK_DIR/ranges_probe.o"
# 不带宏 → error: no member named 'find' in namespace 'std::ranges'
# 带宏   → rc=0
/data/service/hnp/bin/clang++ -std=c++20 -D_LIBCPP_ENABLE_EXPERIMENTAL -c "$TASK_DIR/ranges_probe.cc" -o "$TASK_DIR/ranges_probe.o"
```

---

## 必修项 ②：`CMAKE_SYSTEM_NAME` 缺省 → 无 SONAME → 插件 `DT_NEEDED` 变相对路径

### 症状（逐字，运行消费者测试的 stderr）

```text
dlopen: Error loading shared library ../libheif.so: (needed by …/libheif-aomdec.so)
heif_init(NULL) -> code=11 (Cannot open plugin (dlopen).)
[FAIL] heif_have_decoder_for_format(AV1) == 1
```

### 根因机制

1. 设备 `uname -s` = **`HarmonyOS`**，而 SDK 的 CMake 只有
   `Modules/Platform/OHOS.cmake`（内容就是 `include(Platform/Linux)`），
   **没有 `Platform/HarmonyOS.cmake`**；
2. Conan 只在"跨平台"时写 `CMAKE_SYSTEM_NAME`（`GenericSystemBlock` 里
   `if(NOT DEFINED CMAKE_SYSTEM_NAME) set(CMAKE_SYSTEM_NAME <mapped>)`，且
   `_get_generic_system_name()` 在 `os_host == os_build` 且 arch 相同时**不返回**系统名）；
   设备上是原生编译（host==build）→ 该变量为空 → CMake 落到"未知平台"通用回退，并打印
   `System is unknown to cmake, create: Platform/HarmonyOS …`（**rc 仍为 0**，是噪声）；
3. 未知平台的通用回退**不设置** `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`，于是共享库
   **既不写 SONAME、也不产生带版本的文件名**（实测构建树只有 `libheif.so`，`readelf -d` 无 SONAME）；
4. 插件以 MODULE 形态链接**树内**宿主 target（`target_link_libraries(heif-<codec> PRIVATE … heif)`），
   宿主没有 SONAME → 链接器把命令行上的路径原样写进 `DT_NEEDED`，即 `../libheif.so`；
5. `DT_NEEDED` 含斜杠的条目**按当前工作目录解析**（不走 RPATH/LD_LIBRARY_PATH），
   装到 `<pkg>/lib/libheif/` 后必然找不到 → dlopen 失败。

### 修法

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"     # 走 Platform/Linux.cmake
```

效果：宿主得到 SONAME `libheif.so.1` + 版本化文件名（`.so.1`、`.so.1.23.0`），
插件 `DT_NEEDED` 变成**无斜杠**的 `libheif.so.1`，由 conanrun 的 `LD_LIBRARY_PATH`
（`cpp_info.libdirs` → `<pkg>/lib`）正常解析。仓库 693 个配方同口径；设备侧
`archives/a/aom/3.9.1/notes.md` 的 `-DCMAKE_SYSTEM_NAME=Linux` 也是同一 workaround。

### 可用性探针（三种取值，5 秒级）

```sh
# add_library(foo SHARED foo.c) + set_target_properties(foo PROPERTIES VERSION 1.2.3 SOVERSION 1)
cmake -S "$TASK_DIR/rpath-probe/src" -B "$TASK_DIR/rpath-probe/b-none"  -G "Unix Makefiles" -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang
cmake -S "$TASK_DIR/rpath-probe/src" -B "$TASK_DIR/rpath-probe/b-linux" -G "Unix Makefiles" -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_SYSTEM_NAME=Linux
# b-none : libfoo.so                     ，readelf -d → (no SONAME)
# b-linux: libfoo.so libfoo.so.1 libfoo.so.1.2.3，readelf -d → SONAME libfoo.so.1
```

### 两条路线（择一即可，**不要求全族统一**）

| 路线 | 写法 | 优点 | 代价 / 副作用 | 仓库先例 |
|---|---|---|---|---|
| **A（本包采用）** | `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"` | 一行；把平台整体拉回 Linux 语义（SONAME＋版本化文件名＋rpath 规则一并恢复） | ① 上游若有 `if(CMAKE_SYSTEM_NAME STREQUAL "Linux")` 分支会**被翻转**（libheif 1.23.0 实测**没有**这类分支：全树 `grep -rn CMAKE_SYSTEM_NAME --include=CMakeLists.txt --include=*.cmake` **0 命中**）；② CMake 进入 **cross-compiling 语义**（host=HarmonyOS ≠ Linux），`try_run` 类探测需预置变量 | 693 个配方（含 `archives/a/ableton-link/3.1.2`）；设备侧 `archives/a/aom/3.9.1/notes.md` |
| **B（更窄）** | `for lang in ("C","CXX"): tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"` | **不动 `CMAKE_SYSTEM_NAME`**，不翻转上游分支、不进入 cross 语义 | 只补 SONAME 相关能力（实测足够：见下） | 160 个配方，如 `archives/a/azure-identity-cpp/1.13.3:77`、`archives/a/attica/6.14.0`、`archives/a/apache-arrow/25.0.0` |

实测（5 秒探针，`add_library(foo SHARED)`＋`VERSION 1.2.3 SOVERSION 1`）：

```text
mode=none                     → libfoo.so                                    (no SONAME)
mode=SONAME_C_FLAG=-Wl,-soname, → libfoo.so libfoo.so.1 libfoo.so.1.2.3        SONAME libfoo.so.1
mode=CMAKE_SYSTEM_NAME=Linux  → libfoo.so libfoo.so.1 libfoo.so.1.2.3        SONAME libfoo.so.1
```

即**路线 B 单独就足以恢复 SONAME 与版本化文件名**；两条路线在 libheif 这个包上等价，
取舍只在"是否愿意翻转 `CMAKE_SYSTEM_NAME`"。本包选 A 是因为设备侧同源先例（aom 归档）
与仓库主流口径一致，且实测上游没有依赖该变量的分支。

### 子工程陷阱（同一根因的第二现场）

`tc.cache_variables` **只写进 `generators/CMakePresets.json`**，
`generators/conan_toolchain.cmake` 里没有它——Conan 的 `CMake.__init__` 是从 preset 文件里
取 `cacheVariables` 再用 `-D` 传给**主工程**的。因此：

* 用 `CMake(self).configure()` 的主工程 → 生效；
* 配方里**自己再 configure 一个子工程**（例如"内树自包含构建一个没有 Conan 包的 codec"：
  `cmake -S <codec> -B … -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake`）
  → **拿不到**，会静默回落到未知平台（噪声满屏；若子工程也要产出共享库则是硬故障）。
  处置：子工程命令行**显式再传一次** `-DCMAKE_SYSTEM_NAME=Linux`。

---

## 必修项 ③：安装期改写 RUNPATH → 破坏 OHOS 代码签名 → `dlopen: … Permission denied`

### 症状（逐字）

```text
dlopen: Error loading shared library <pkg>/lib/libheif/libheif-aomdec.so: Permission denied
heif_init(NULL) -> code=11 (Cannot open plugin (dlopen).)
LIBHEIF_AOM_CONSUMER checks_total=25 checks_passed=11 → RESULT: FAIL
```

**注意是 `Permission denied`（EACCES）而不是 `not found`**——文件存在、可读
（`head -c 4` 正常）、权限位与宿主一致（`-rwxrwx--- 770`，同一 group），
但 `dlopen` 就是被拒。而**同一份未安装**的构建树插件 `dlopen → OK`。

### 根因机制

1. 设备 clang launcher 在**链接期**给 ELF 写入 `.note.ohos.ident` 代码签名
   （`readelf -n` 可见该 note；`compiled` 与 `installed` 两份都有这个 note）；
2. CMake 默认 `BUILD_WITH_INSTALL_RPATH=OFF`：构建树的二进制带**构建树 RUNPATH**，
   `cmake --install` 会把它**就地改写**成安装 RUNPATH（本例被清空）；
3. 文件字节一变，**签名失效** → OHOS 加载器拒绝映射 → EACCES。

判定读数（同一份二进制，安装前 vs 安装后）：

```text
安装前: sha256 921d231fd996047850bfa68ebf3cc8b167da7addafd5a6b5584ffdf0ad5b9038  RUNPATH 1 条  dlopen → OK
安装后: sha256 d5f879295925a53428159a59c59577c392b348095e3247b60adf78afc2d781ce  RUNPATH 0 条  dlopen → Permission denied
（两者**字节数完全相同** 1423808 —— 不比对 sha256 就看不出来）
```

**判读陷阱（最容易误判的一点）**：宿主 `libheif.so.1.23.0` 安装前后 sha256 **完全一致**
（它本来就无需改写 RUNPATH），所以"宿主能加载"不能推出"插件没问题"。必须单独查**插件**。

### 命中范围判据（谁会踩）

CMake 只会给"链接了**同一构建树内另一个 target**"的目标加构建树 RPATH ——
libheif 插件正是这个形态（`… PRIVATE heif`），所以 **7 个同族插件子包全中**；
只链 Conan 依赖（非树内 target）的普通包不带构建树 RPATH、install 无需改写、**不受影响**。
这解释了为什么仓库里大多数包没有暴雷，而这类"树内互链"的包必踩。
同理适用于：任何交付**可执行文件/共享库且链了树内兄弟 target** 的包。

### 修法（两条路线，语义不同）

**路线 A（本包采用）：从源头不触发改写**

```python
tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True   # 构建树直接用安装 RPATH → 安装期不再改写
tc.variables["CMAKE_INSTALL_RPATH"] = ""                # 不烘绝对路径；运行期靠 conanrun 的 LD_LIBRARY_PATH
```

判据：安装前后 `sha256sum` **逐字节一致**。

**路线 B：失效后修复——装后重签**（已合并先例 `archives/o/openh264/2.6.0:130-136`、
`archives/f/ffmpeg/8.1.2:240-246`，其 `test_package` 14/14 PASS）：

```python
# package() 里，cmake.install() 之后，覆盖 lib/**/*.so*（跳过软链）
objcopy = "/data/service/hnp/bin/llvm-objcopy"
signer  = "/data/service/hnp/bin/binary-sign-tool"
self.run(f'{objcopy} --remove-section .codesign "{f}" 2>/dev/null || true')
self.run(f'{signer} sign -inFile "{f}" -outFile "{f}" -selfSign 1')
```

两条路线的取舍（**附证据强弱，家族首选 = B**）：

| | 路线 A（RPATH 两行） | 路线 B（装后重签） |
|---|---|---|
| 语义 | **从源头不产生改写** → 签名根本没被破坏 | **失效后修复** → 重新签名 |
| 覆盖面 | 只覆盖 "install 改写 RUNPATH" 这一种改写 | 覆盖 install 之外的任何改写（strip、patchelf、conan 打包期加工……） |
| 依赖 | 纯 CMake 变量，无外部工具 | 依赖 HNP 的 `llvm-objcopy`/`binary-sign-tool`（设备与 CI worker 都在 `/data/service/hnp/bin/`） |
| 证据强度 | **单点**：本包的最小探针（default `pre≠post`/RUNPATH 1→0；加两变量 `pre==post`）+ 本包真实 `conan create`（见 notes 的实测读数）。同批 libde265 用类似探针**两遍都没能复现"默认会被改写"**——所以 A 的机理虽清楚，**可复现性尚未在多包上坐实** | **强**：① 同文件、同进程的前后对比（重签前 `Permission denied`/`code=11`/`decoder=0` → 重签后 `dlopen OK`/`code=0`/`decoder=1`，跑通上游 `tests/data/rainbow-451x461.heic` 真实解码）；② 同批 **2 个真实包端到端通过**（dav1d 13/13、openh264 14/14）；③ 2 个已合并先例 `archives/o/openh264/2.6.0:130-136`、`archives/f/ffmpeg/8.1.2:240-246` |

**落地建议**：优先 B（证据最强、覆盖最广）；A 在 libheif-aom 上已用**真实 `conan create` 自证**
（插件安装前后 sha256 逐字节一致 + RUNPATH 0 条 + `test_package` 25/25 PASS），因此两条都可采，
但判据一律以**真实构建**为准，不照抄探针结论：

```text
（读数取自采信轮＝清缓存后全量重建；构建树 Release/... vs 安装树 <pkg>/...）
libheif-aomdec.so  pre=831e474416c6c8aa… post=831e474416c6c8aa… identical=YES  RUNPATH 0
libheif-aomenc.so  pre=5bfeddf2d387ae67… post=5bfeddf2d387ae67… identical=YES  RUNPATH 0
libheif.so.1.23.0  pre=f6d6c0862c539895… post=f6d6c0862c539895… identical=YES  RUNPATH 0
LIBHEIF_AOM_CONSUMER checks_total=25 checks_passed=25 → RESULT: PASS
```

两个插件模块的哈希跨构建**可复现**；宿主哈希随构建路径变化（另一轮为 `dc933d37cda9…`），
但「安装前后逐字节一致」这一判据在每一轮都成立——**判据是性质，不是某个固定哈希**。

若复跑时出现 EACCES，立即改 B 兜底，不在 A 上多耗轮次。

### 附带陷阱一：宿主机静默回退（`~/.harmonybrew`）——设备全绿、干净 worker 必红

**配方带 Conan 依赖时**，`CMakeToolchain` 会写 `CMAKE_FIND_PACKAGE_PREFER_CONFIG`
（`conan/tools/cmake/toolchain/blocks.py:577`；`cmakeconfigdeps.py:247` 亦显式置 `ON`），
于是上游的 `find_package()` 优先匹配 config 模式的 `*-config.cmake`——包括设备
`~/.harmonybrew/...` 下的那些。若配方**没声明**某依赖而上游又探测它，就可能**链上一个未声明的依赖**：
设备上全绿，干净 CI worker 上必红，且构建日志里零异常。
（本包 `requirements()` 为空，实测生成的 `conan_toolchain.cmake` 里**没有**该变量，
所以这条对本包只是"核查过、无泄漏"，见下。）
判据（必须为 0）：

```sh
grep -c harmonybrew <build>/CMakeCache.txt <build>/build.ninja
nm -D <pkg>/lib/<lib>.so | grep -E ' (inflate|deflate|compress2|crc32)$'   # 不该出现未声明库的符号
readelf -d <pkg>/lib/<lib>.so | grep NEEDED                                # 只应有声明过的依赖
```

libheif-aom 实测：`CMakeCache.txt` 里有 1 条 `ZLIB_DIR=…/.harmonybrew/lib/cmake/ZLIB`
（`find_package(ZLIB)` 的探测残留，`WITH_HEADER_COMPRESSION=OFF`/`WITH_UNCOMPRESSED_CODEC=OFF`
时该分支关闭），但**link.txt 0 条、DT_NEEDED 无 libz、`nm -D` 无 zlib 符号、
installed `libheif.pc` 的 Requires/Requires.private 为空** ⇒ 没有 brew 库进入交付面。
内树 libaom 侧 0 命中（cache 变量钉死路径）。**结论口径**：cache 里有探测残留 ≠ 有依赖泄漏，
必须用"链接行 + `DT_NEEDED` + 符号 + `.pc`"四条实物判据确认。

### 附带陷阱二：`finish` 副作用的**假绿还原**

`finish` 会把 `conandata.yml` 的官方 URL 改写成含 `gh-proxy.com` 的镜像列表
（该域名在 preflight PF7 / R39 黑名单里）、重建 `SUMMARY.md`、并在 `notes.md` 尾部追加
"编译结束/最终状态"。`finish_restore.sh --apply` 声称"副作用已全部还原"，但它枚举未跟踪物时
用的是 `git status --porcelain`，而 `conandata.yml.orig` / `*.ghfast-bak` 被 `.gitignore` 忽略
⇒ **不进清单、仍打印 ✅**（假绿）。收尾必须自己机械兜底：

```sh
sh "$WORKSPACE_ROOT/tools/finish_restore.sh" --apply "$TASK_DIR" "$TARGET_REPO" "$PACKAGE_DIR"
find "$TARGET_REPO" \( -name 'conandata.yml.orig' -o -name 'conandata.yml.*-bak' -o -name '*.rej' \) -not -path '*/.git/*' -print -delete
git -C "$TARGET_REPO" diff --stat      # 必须为空
git -C "$TARGET_REPO" status --short   # 必须为空
```

### 附带陷阱三：`CMakeDeps` 生成的目标**没有** `IMPORTED_LOCATION_RELEASE`

消费者侧（`test_package`）若用 `get_target_property(... IMPORTED_LOCATION_RELEASE)` 去定位
被测包的产物，在 Conan `CMakeDeps` 下**恒失败**：CMakeDeps 生成的是
`INTERFACE IMPORTED` 目标，`IMPORTED_LOCATION_RELEASE`/`IMPORTED_LOCATION` 都**未设置**，
脚本会**静默退化**到一条看着"像包内路径"的错误路径（同批 dav1d 第一轮因此 13 条断言里 6 条 FAIL）。
正确做法二选一：

* CMake 侧：用 `<pkg>_PACKAGE_FOLDER_<CONFIG>`（CMakeDeps 会生成该变量）；
* 或者 Python 侧：`self.dependencies[self.tested_reference_str].package_folder` 注入，
  并在 CMakeLists 里加 `if(NOT DEFINED <VAR>) message(FATAL_ERROR ...)` 硬守卫。

本包不受影响：`test_package/CMakeLists.txt` 只用 `find_package(libheif REQUIRED)` +
`target_link_libraries(... libheif::libheif)`，不自行解析产物路径；产物存在性由
`heif_get_version()` 版本指纹与插件装载检查承担。

### 最小复现（30 秒，无需 libheif）

```sh
T="$TASK_DIR/rpath-probe"; mkdir -p "$T/src"
printf 'int bar(void);\nint foo(void){return bar()+1;}\n'            > "$T/src/lib.c"
printf 'int bar(void){return 41;}\n'                                  > "$T/src/mod.c"
printf 'cmake_minimum_required(VERSION 3.16)\nproject(rp C)\nadd_library(rp SHARED lib.c)\nset_target_properties(rp PROPERTIES VERSION 1.2.3 SOVERSION 1)\nadd_library(rpmod MODULE mod.c)\ntarget_link_libraries(rpmod PRIVATE rp)\ninstall(TARGETS rp LIBRARY DESTINATION lib)\ninstall(TARGETS rpmod LIBRARY DESTINATION lib/plugins)\n' > "$T/src/CMakeLists.txt"
for mode in default fixed; do
  d="$T/b-$mode"
  [ "$mode" = fixed ] && extra='-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DCMAKE_INSTALL_RPATH='
  # shellcheck disable=SC2086
  cmake -S "$T/src" -B "$d" -G "Unix Makefiles" -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_SYSTEM_NAME=Linux $extra >/dev/null
  cmake --build "$d" >/dev/null; pre=$(sha256sum "$d/librpmod.so" | cut -c1-12)
  cmake --install "$d" --prefix "$d/inst" >/dev/null; post=$(sha256sum "$d/inst/lib/plugins/librpmod.so" | cut -c1-12)
  echo "mode=$mode pre=$pre post=$post identical=$([ "$pre" = "$post" ] && echo YES || echo NO)"
done
# default → identical=NO（会被改写）
# fixed   → identical=YES
```

### 附带判读陷阱：插件目录里多余的文件会拖累 `heif_init()`

libheif 的插件装载会**逐个 dlopen 插件目录下的文件**；目录里只要有一个加载不了的
文件（旧版本残留、手工拷贝的样本），`heif_init()` 就整体返回
`code=11 (Cannot open plugin (dlopen).)`，于是**正确的插件也被判为未注册**。
本任务实测：包目录里多放了一个旧插件样本 → 25 项消费者检查只过 24（唯一失败是
`heif_init`），删掉后全绿。**验收前先 `ls <pkg>/lib/libheif/` 确认目录里只有交付面文件**。

---

## 附：共享设备上的构建自限（两种模式，②更稳）

`conan_verify` / `finish` 等**官方入口不传** `-c tools.build:jobs`，而 Conan 的 `CMake.build()`
默认按 `os.cpu_count()` 追加 `-j20`（本设备 20 而容器 affinity 只有 8 → 超订）。
配方自限有两种写法，取舍不同：

| 模式 | 写法 | 优点 | 代价 |
|---|---|---|---|
| ① 追加覆盖 | `cmake.build(target=[…], build_tool_args=[f"-j{jobs}"])` | 一行改动，仍用 Conan 的 helper | 依赖"make 取**最后一个** `-j`"这条隐式规则；命令行里会留下 `-- -j20 -jN` 的痕迹（易被误读成超订）；**覆盖不到"配方自己 configure 的子工程"** |
| ② 显式命令行（**本包采用**） | `jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)`<br>`self.run(f'cmake --build "{build}" -j{jobs}')` | **从根上不产生 conan 的 `-j20`**，不依赖隐式规则；主工程与内树子工程**共用同一个 `jobs`** | 放弃 `CMake.build()` 的少量便利（configure 仍可用 `CMake(self).configure()`） |

机械自检（应只剩"被覆盖形态"，不留未覆盖的 `-j20`）：

```sh
grep -n "build_tool_args\|tools.build:jobs\|cmake.build\|cmake --build" <pkgdir>/conanfile.py
grep -c -- "-j20" <conan create 日志>       # 期望：0（模式②）或仅 test_package 那种被覆盖的形态
```

本包实测（模式②）：`tools.build:jobs` 缺省 **2**（`notes/device-facts.md` §一.7 的安全区间 2..4 下界，
含内树 codec 时 `-j2 ≈ 24 min`、`-j1 ≈ 47 min` 逼近 `conan_verify` 的 3600s create 预算）。
另外，`conan remove -c` 的"清缓存轮"**连带删掉 source/build 缓存** ⇒ 每轮都是**全量**构建，
预算按全量估，不要按增量估。

## 组合验收（四项判据，缺一不可）

```sh
PID=$(conan list "libheif-aom/1.23.0:*" -f json | python3 -c "import sys,json;d=json.load(sys.stdin);print(next(iter(next(iter(next(iter(d.values())).values()))['revisions'].values())['packages']))")
CP=$(conan cache path "libheif-aom/1.23.0:$PID")
# ① 交付面成立（配置期）：+ separate plugin 而不是 + built-in / - not found / - disabled
grep -E "AOM AV1 (decoder|encoder) +: " <configure 日志>
# ② 文件齐 + SONAME 正确 + DT_NEEDED 无斜杠
find "$CP/lib" -name 'libheif*.so*' | sort
readelf -d "$CP/lib/libheif.so.1.23.0" | grep SONAME          # libheif.so.1
readelf -d "$CP/lib/libheif/libheif-aomdec.so" | grep NEEDED  # libheif.so.1（**不能**含 /）
# ③ 安装前后逐字节一致（签名未被破坏）
sha256sum <build_tree>/libheif/plugins/libheif-aomdec.so "$CP/lib/libheif/libheif-aomdec.so"
# ④ 真跑消费者测试（env="conanrun"）
#    LIBHEIF_AOM_CONSUMER checks_total=25 checks_passed=25 → RESULT: PASS
```

## N（rule4，子包口径，附带给同族）

子包的上游 N **按父 tarball 完整注册面**取「用例/注册类」候选口径的最大值：
libheif 1.23.0 → Catch2 `TEST_CASE` **217**（主 N）
＞ CTest `add_test` 39（全开关上限）= 测试目标 39 ＞ 测试源文件 41 中的可运行项；
断言（`REQUIRE(` 3994 + `CHECK(` 18 + `REQUIRE_FALSE/CHECK_FALSE(` 4 = 4016）属**另一单位**，
只披露不并入。交付面外的上游用例按 NOT_RUN + 逐项归因，**不为凑数字放开不属于交付面的
上游开关**（`BUILD_TESTING=ON` 会额外拉 heifio 与 TIFF/JPEG/PNG/WEBP 探测以及未适配后端）。

## 复现（设备可直接执行，全部落 `$TASK_DIR`）

```sh
TASK_DIR=$HOME/tmp/libheif-aom-1.23.0
S=$WORKSPACE_ROOT/tmp/builds/libheif-aom-1.23.0.work
# ① ranges 缺口
printf '#include <algorithm>\n#include <vector>\nint main(){std::vector<int> v{1};return std::ranges::find(v,1)==v.end();}\n' > "$TASK_DIR/ranges_probe.cc"
/data/service/hnp/bin/clang++ -std=c++20 -c "$TASK_DIR/ranges_probe.cc" -o "$TASK_DIR/ranges_probe.o" || true
grep -n "_LIBCPP_HAS_NO_INCOMPLETE_RANGES" /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/c++/v1/__config
# ② SONAME / DT_NEEDED（见上文 SONAME 探针脚本与 readelf 两条）
readelf -d "$S/../heif-explore/build-b/libheif/libheif.so" | grep SONAME || echo "(no SONAME)"
# ③ 安装期改写（见上文 30 秒最小复现脚本）
# ④ 交付面与消费者测试：见「组合验收」
```

## 关联

* `DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage`（同族姊妹条：子包判类/交付面/N）
* `DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification`（`<父>-tools` 拆分包判类）
* `archives/h/handbrake/1.11.2`（in-tree contrib + `requirements()` 为空先例）
* `archives/a/aom/3.9.1`（元数据孤儿反例：有 manifest 无 conanfile；同时是 `CMAKE_SYSTEM_NAME=Linux` 的同口径先例）
* `archives/l/libpqxx/8.0.1`、`archives/l/ladybug/0.18.2`（`_LIBCPP_ENABLE_EXPERIMENTAL` 先例）
* `archives/l/libheif/1.18.2/notes.md`（"NEEDED 字段硬编码相对路径、未解决"——本条给出结论）
