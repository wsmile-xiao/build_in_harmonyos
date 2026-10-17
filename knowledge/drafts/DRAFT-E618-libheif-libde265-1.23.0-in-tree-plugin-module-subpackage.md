# DRAFT-E618-libheif-libde265：父 tarball 内「插件模块型」子包的识别、依赖归属与交付面判定

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-20
> Source: `libheif-libde265` 1.23.0 适配（HarmonyOS PC，积分赛/新包）
> 对应：`knowledge/drafts/DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage.kv`

## 问题

任务清单里出现 `libheif-libde265` / `libhwy_test` / `libhwy_contrib` 这类
`<父库>-<组件>` 名字时，第一步要回答四个问题，任何一个答错都会让适配路线跑偏：

1. **上游是谁？** `<组件>` 是独立项目，还是父 tarball 里"顺手编出来的"子模块？
2. **依赖从哪来？** 组件若依赖外部库，是内树构建还是复用已发布的独立包？
3. **交付面是什么？** 只交父库产物，还是必须交出**名字对应的那个产物**？
4. **N 怎么算？** 子包的上游用例数按组件算，还是按父 tarball 算？

同族先例 `DRAFT-10251-libnfc-tools-…-tools-subpackage-identification` 处理的是
第 ① 类的另一半（`<父>-tools/-utils/-cli`，发行版拆分包）。本条记录的是
**父 tarball 内子模块**这一类，判据完全不同：不看 distro spec，看**父 tarball 里
有没有这个目标名**。

## 识别：在父 tarball 里找目标名（不是找仓库名）

```sh
# 在解包后的父 tarball 根执行
grep -rn "add_library(.*\${name}" --include=CMakeLists.txt .   # 目标名模板
grep -rn "<组件>" --include=CMakeLists.txt .                    # 组件出现在哪
find . -iname '*<组件>*'                                        # 有没有可内树构建的源码树
tar -tzf <父>-<ver>.tar.gz | head -3                            # 顶层是 <父>-<ver>/，不是独立 tarball
```

**libheif-libde265 实证**：

```sh
grep -rn "add_library(heif-\${name}" libheif/plugins/CMakeLists.txt
#   → add_library(heif-${name} MODULE ${..._sources} ${..._extra_plugin_sources} ../api/libheif/heif_plugin.cc)
grep -n "plugin_compilation(libde265" libheif/plugins/CMakeLists.txt
#   → plugin_compilation(libde265 LIBDE265 LIBDE265_FOUND LIBDE265 LIBDE265)
find . -iname '*de265*'
#   → ./cmake/modules/FindLIBDE265.cmake
#     ./libheif/plugins/decoder_libde265.cc
#     ./libheif/plugins/decoder_libde265.h        ← 树内**没有** libde265 源码树
```

结论：`libheif-libde265` = 上游 CMake 目标 `heif-libde265` 的产物
`libheif-libde265.so`，源码在**树内**（`libheif/plugins/decoder_libde265.cc`），
而它依赖的 libde265 **在树外**（只有 Find 模块 + 插件适配层）。

**包名规则**（本仓惯例）：包名 = 交付库文件名去掉 `lib` 前缀与扩展名。
`hwy_test` → `libhwy_test.a` → 包名 `libhwy_test`；
`heif-libde265` → `libheif-libde265.so` → 包名 `libheif-libde265`。
（组件型先例 `lensfun-tools`、`libcpuid-tool` 同理，只是产物是可执行文件。）

## 依赖归属：外部库的适配层 ≠ 内树重建

`find` 的结果决定路线，判据是**树内有没有可构建的组件源码**：

| 树内情况 | 路线 | 本仓先例 |
|---|---|---|
| 组件自己的源码/子目录在树内，构建系统本来就用它 | 内树构建，不引外部依赖 | `libhwy_test`（`hwy/tests/*`，`HWY_ENABLE_TESTS=ON` 是交付面必要条件） |
| 组件是**外部库的适配层**（树内只有 Find 模块 + 适配源码） | 复用仓库既有独立包 | `libheif-libde265` → `libde265/1.0.18` |
| 既没有同名目标、也没有同名源码 | 多半是 distro 拆分包或任务名有误 | 见 DRAFT-10251 |

libheif 这一类的关键是**不要内树重建**：树内没有 libde265 源码，
且独立包已发布（R36），重建只会产出重复制品并丢掉既有的平台结论
（libde265 在 aarch64 上必须 `HAVE_NEON=FALSE` + 关 `ENABLE_ARM`，因为
`libde265/arm/*.S` 是 ARMv7-A NEON，aarch64 上不可汇编）。

依赖可用性验证（R35：禁止用 `conan list/search` 判断）：

```sh
conan install --requires=libde265/1.0.18 --build=never -pr:a ci/conan/profiles/ohos-aarch64
# → libde265/1.0.18#c229171963f110ca700356f623612dc8 - Downloaded (ohpcd)
#   Package installed 21b17f8b2bc0e9511e276e3d57a23893067cefe5
```

## 交付面：命名产物 + 宿主（自包含）

插件模块**无法脱离宿主**，这不是取舍而是上游机制的硬约束：

* 链接期 `target_link_libraries(heif-libde265 PRIVATE ${LIBDE265_LIBRARIES} heif)`
  → 插件 `DT_NEEDED` 宿主 `libheif.so`；
* 运行期只有宿主 `heif_init()` 才 `dlopen` 插件目录下的模块并注册后端。

因此**不能** `requires` 一个功能不匹配的既有宿主包：仓库里的
`libheif/1.22.2` 是 `ENABLE_PLUGIN_LOADING=OFF` 的 codec-free 核心，
运行期根本不装载插件（跨版本插件 ABI 也另说）。正确做法是**自包含交付
同源同版本的宿主**——与 `libhwy_test` 自包含交付 PUBLIC 依赖 `hwy` 同口径。

### 运行期插件目录陷阱（本条的第二个可复用点）

上游把默认插件目录**编译期钉死**：

```c
/* libheif/api/libheif/heif_version.h.in */
#define LIBHEIF_PLUGIN_DIRECTORY "@PLUGIN_DIRECTORY@"   /* = ${CMAKE_INSTALL_FULL_LIBDIR}/libheif */
```

即"构建时 Conan 包目录的绝对路径"。Conan 包目录跨缓存/跨机不稳定 →
运行期必须用环境变量覆盖，而**以代码为准**：

```c
/* libheif/plugins_unix.cc:37 —— 单数 PATH */
char* path_variable = getenv("LIBHEIF_PLUGIN_PATH");
/* libheif/init.cc:61-62 —— 环境变量为空时才回退到编译期目录 */
if (plugin_paths.empty()) plugin_paths.push_back(LIBHEIF_PLUGIN_DIRECTORY);
```

⚠️ `heif_library.h` 的注释写的是复数 `LIBHEIF_PLUGIN_PATHS`，与实现不符（上游过期文档）。

Conan 侧在 `package_info()` 里导出，消费方 `VirtualRunEnv` / `conanrun` 自动生效：

```python
self.runenv_info.define("LIBHEIF_PLUGIN_PATH",
                        os.path.join(self.package_folder, "lib", "libheif"))
```

## 工具链陷阱：libc++ 的 `__cpp_lib_ranges` 会说谎

libheif 1.23.0 在 `libheif/box.cc` 的 `Box_rref` 上用了 C++20 ranges 算法。
OHOS SDK 的 libc++ 是 **15004**（clang 15.0.4）：`<version>` 里声明
`__cpp_lib_ranges 201811L`，但 `<algorithm>` **不声明** ranges 算法：

```sh
/data/service/hnp/bin/clang++ -std=c++20 -c rangesprobe.cc
# error: no member named 'find' in namespace 'std::ranges'
# error: no member named 'all_of' in namespace 'std::ranges'
```

判据教训：**特性测试宏不等于实现完整**，要么用真编译器探针，要么直接看
`__cpp_lib_ranges_find` 这类**细粒度**宏（libc++ 15004 未定义）。
处置：补丁换成等价的 C++17 `std::all_of`/`std::find`（对 `std::vector`/`std::array`
语义完全相同），不引入平台宏。

## 静默失败：`conandata.yml` 的 `patches` 用 dict 形态 = 补丁永不生效

补丁写完、补丁文件也在 `patches/` 下，编译错误却照旧，日志里连 `Apply patch`
都不出现。根因在 Conan 2 的 `patches` 语义：

```python
# conan/tools/files/patches.py: apply_conandata_patches / export_conandata_patches
if isinstance(patches, dict):
    entries = patches.get(str(conanfile.version), [])   # ← dict 被当成 {version: [条目…]}
elif isinstance(patches, list):
    entries = patches
```

即 **dict 形态的 key 是"版本号"而不是"补丁文件名"**。用文件名当 key 时
`patches.get("1.23.0", [])` 得到空列表 → 既不导出也不应用，**无告警无报错**。
`knowledge/ARCHIVE-SPEC.md` §4.3 给的 dict 示例是 Conan 1 时代写法，照抄即踩。

正确形态（与 `archives/l/libde265/1.0.18` 一致）：

```yaml
patches:
  - patch_file: "patches/0001-libheif-box.cc.patch"
    patch_description: "..."
    patch_type: "portability"
```

自检命令（应为 `list`）：

```sh
python3 -c "import yaml;d=yaml.safe_load(open('conandata.yml'));print(type(d['patches']).__name__)"
# 导出侧的第二道证据：conan export 的输出里必须出现 "Copied 1 '.patch' file"
```

这一类是典型的**假绿形态**：被测对象"看起来做了适配"（补丁文件在、manifest 里
写了 `patches_applied`），实际编译的是未打补丁的上游源码。凡补丁类改动，
必须以「导出日志出现 Copied .patch」+「构建日志出现 Apply patch」两条正面证据判定。

## 致命陷阱：不钉 `CMAKE_SYSTEM_NAME=Linux` ⇒ 插件运行期必挂（构建期全绿）

**病链**（本机逐段实测）：

1. 设备 `uname -s` = **HarmonyOS**；Conan 对 `os=OHOS` 默认下发
   `CMAKE_SYSTEM_NAME=HarmonyOS`（configure 日志逐字：
   `System is unknown to cmake, create: Platform/HarmonyOS …`）；
2. SDK 的 CMake（`/data/service/hnp/bin/cmake`，4.1.2）的 `Modules/Platform/`
   下**只有 `OHOS.cmake`，没有 `HarmonyOS.cmake`** → 落到「未知平台」通用回退；
3. 后果：**共享库不写 SONAME、也没有版本化文件名**。最小探针（同一
   `add_library(foo SHARED)` + `VERSION 1.2.3 SOVERSION 1`，用包构建目录里的
   `conan_toolchain.cmake`）：

   ```sh
   cmake -S probe -B probe/b-a -DCMAKE_TOOLCHAIN_FILE=<build>/generators/conan_toolchain.cmake
   cmake --build probe/b-a
   ls probe/b-a/libfoo*                      # → 只有 libfoo.so
   readelf -d probe/b-a/libfoo.so | grep SONAME   # → 无输出（NO SONAME）

   cmake -S probe -B probe/b-b -DCMAKE_TOOLCHAIN_FILE=<build>/generators/conan_toolchain.cmake \
         -DCMAKE_SYSTEM_NAME=Linux
   cmake --build probe/b-b
   ls probe/b-b/libfoo*                      # → libfoo.so + libfoo.so.1 + libfoo.so.1.2.3
   readelf -d probe/b-b/libfoo.so.1.2.3 | grep SONAME
   #   → 0x000000000000000e (SONAME)  Library soname: [libfoo.so.1]
   ```

4. 对本类包是**致命**的：MODULE 插件链接宿主时把**相对路径**写进 DT_NEEDED
   （`NEEDED ../libheif.so`，含斜杠 ⇒ 按 CWD 解析）→ 运行期 `heif_init()`
   加载插件失败 → `heif_have_decoder_for_format(HEVC) == 0` → `test_package`/G2
   必红，而**链接期与编译期完全看不出问题**（典型假绿）。

**修法**（配方 `generate()` 一行）：

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
```

Conan 的 `GenericSystemBlock` 生成的是 `if(NOT DEFINED CMAKE_SYSTEM_NAME)`，
故 cache 变量优先；编译器与目标仍由 toolchain 决定（产物仍是 OHOS aarch64）。
仓库 693 个配方同口径（先例 `archives/a/ableton-link/3.1.2`）。

## 最隐蔽的一条：`cmake --install` 改写 RUNPATH → 破坏 OHOS 代码签名 → `dlopen` 报 Permission denied

**现象**：编译、链接、安装全部成功；只有运行期 dlopen 失败，而且报的是
`Permission denied`（**不是** not found），极易被误读成权限位问题：

```text
dlopen: Error loading shared library <pkg>/lib/libheif/libheif-libde265.so: Permission denied
heif_init(NULL) -> code=11 (Cannot open plugin (dlopen).)
heif_have_decoder_for_format(HEVC) == 0     → test_package RESULT: FAIL（7/9）
```

**机制**（本包真实 `conan create` 产物，逐条可复现）：

| 观察点 | 构建树 | 安装后 |
|---|---|---|
| 插件 RUNPATH | `<build>/libheif/` | **无** |
| 插件 sha256 | `eb04f0f6…` | `abb4b2be…`（同尺寸 514496，`cmp -l` **182 字节**差异） |
| 宿主 `libheif.so.1.23.0` sha256 | `7590122b…` | `7590122b…`（**完全相同**） |
| `.note.ohos.ident`（OHOS 签名段） | 有 | 有（已随改写失效） |

链接期由设备 clang launcher 写入的代码签名，被 `cmake --install` 对 RUNPATH 的
**就地改写**破坏 → 字节一变签名即失效 → OHOS 加载器拒绝映射。
**只查宿主会误判**：宿主不链接同构建树的其它 target，没有构建树 RPATH，
安装前后逐字节相同 —— 必须查**插件**（本包命名产物）。

**隔离验证**（同一设备、同一进程，只对安装后的插件重签）：

```sh
llvm-objcopy --remove-section .codesign <pkg>/lib/libheif/libheif-libde265.so
binary-sign-tool sign -inFile <same> -outFile <same> -selfSign 1
# 重签前：raw dlopen → Permission denied；heif_init code=11；decoder=0
# 重签后：raw dlopen → OK；            heif_init code=0；decoder=1
```

**修法**（已合并先例 `archives/o/openh264/2.6.0`、`archives/f/ffmpeg/8.1.2` 同口径）：
`package()` 在 `cmake.install()` 之后对 `lib/**/*.so*` 逐个重签（跳软链与非 ELF）。

**等价路线**：`CMAKE_BUILD_WITH_INSTALL_RPATH=True` + `CMAKE_INSTALL_RPATH=""`
（从源头不改写，同批 aom 采用）。本机最小探针未能复现 RPATH 改写现象
（默认与加变量两种配置都 pre==post、都无 RUNPATH），故按证据强度选「装后重签」。
两条路线效果等价：都让插件在安装后 dlopen 成功。

**命中判据**：只有**链接了同一构建树内另一个 target** 的目标才会被打上构建树
RPATH、才会在 install 时被改写 —— 插件包（以及打包可执行文件的包）必查。

## N（rule4）：子包按父 tarball 全量注册面取最大值

脚本化审查的判据是「上游实测 N > 声明 N 即不通过」。子包若按组件自身或按
`ctest` 口径申报必然少报——libheif 1.23.0 的三档读数差了一个数量级：

| 口径 | 读数 | 取数命令（父 tarball 根） |
|---|---:|---|
| Catch2 `TEST_CASE` 注册点 | **217** | `grep -rho "^TEST_CASE" tests/*.cc \| wc -l` |
| CTest `add_test`（全开关上限） | 39 | `grep -c "add_libheif_test(\|add_heifio_test(" tests/CMakeLists.txt` |
| 测试源文件 | 41 | `ls tests/*.cc \| wc -l` |
| 断言（**另一单位**，不并入 N） | 4016 | `grep -rhoE "(REQUIRE\|CHECK)(_FALSE\|_THROWS\|…)?\(" tests/*.cc \| wc -l` |

主 N = max(用例/注册类) = **217**；交付面外用例逐项归因后按 NOT_RUN 记账，
不为跑它们放开不属于交付面的上游 build 开关（R1/§3.5）。

## 设备并发：工具没有 jobs 旋钮 ⇒ **配方自己限流**（`build_tool_args` 追加在 `--` 之后）

`finish.py` / `conan_verify.py` **都没有 jobs 旋钮**（grep 0 命中）：经工具发起的
`conan create`，在**配方未自限时**必然按 `os.cpu_count()`（本设备 20，而容器 affinity 只有 8）
并发。可复用的自限模式（本包实测有效）：

```python
jobs = self.conf.get("tools.build:jobs", default=None, check_type=int) or 1
cmake.build(target=["heif", "heif-libde265"], build_tool_args=[f"-j{jobs}"])
```

**机制**：conan 自己会在 `cmake --build …` 后追加 `-- -j20`；`build_tool_args` 的内容被
追加在**更后面**，而 GNU make 对重复 `-j` **取最后一个** ⇒ 有效并发 = 配方给的值。

**三条独立取数证据**（照抄即可复用）：

```sh
# ① 合成夹具：4 个各 sleep 2s 的目标
printf 'all: a b c d\na b c d:\n\t@sleep 2\n' > Makefile
time make -j20 -j1          # → 8s（串行；若 20 路生效应 ~2s）
# ② 进程表逐字
ps -ef | grep make          # → make -f Makefile -j20 -j1 heif heif-libde265
# ③ 量级自证：日志里 RUN: cmake --build … -- -j20 -j1，且全量 core+插件+test_package 实测 37 分钟
```

调用方若显式给 `-c tools.build:jobs=N`，配方尊重之（`default=None` 分支）。共享设备上
建议外层再用 `taskset -c <cpuset>` 做 CPU 硬隔离（槽位制）：taskset 限核、配方限 make 并发，两者互补。

## 旧标题（保留索引）：设备并发

`conan_verify` 等官方入口不传 `-c tools.build:jobs`，而 conan 的默认值是
`os.cpu_count()`（本设备 20，容器 affinity 只有 8）。配方内显式限流：

```python
jobs = self.conf.get("tools.build:jobs", default=None, check_type=int) or 1
cmake.build(target=["heif", "heif-libde265"], build_tool_args=[f"-j{jobs}"])
```

实测 `make -j20 -j1`（4 个各 `sleep 2` 的目标）串行 8s → **最后一个 `-j` 生效**，
故把显式值追加在 conan 自己生成的那一个之后即可安全覆盖。

## 复现（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/libheif-libde265-1.23.0
cd "$TASK_DIR/upstream/libheif-1.23.0"
grep -rn "add_library(heif-\${name}" libheif/plugins/CMakeLists.txt
find . -iname '*de265*'
grep -rho "^TEST_CASE" tests/*.cc | wc -l
grep -c "add_libheif_test(\|add_heifio_test(" tests/CMakeLists.txt
conan install --requires=libde265/1.0.18 --build=never -pr:a ci/conan/profiles/ohos-aarch64
```

## 关联

* `DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification`（`<父>-tools` 拆分包判类）
* `E542`（provider 配方复用父制品）
* 同批同族先例：`archives/l/libhwy_test/1.3.0`、`archives/l/libheif/1.22.2`、`archives/l/libde265/1.0.18`
