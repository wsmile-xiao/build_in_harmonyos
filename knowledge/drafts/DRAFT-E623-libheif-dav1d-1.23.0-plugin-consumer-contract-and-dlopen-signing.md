# E623（草稿）：插件型子包的消费者契约 —— 「交付了 .so」不等于「插件会被 dlopen」

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-20
> Source: `libheif-dav1d` 1.23.0 适配（HarmonyOS PC，积分赛/全新包）
> 对应：`knowledge/drafts/DRAFT-E623-libheif-dav1d-1.23.0-plugin-consumer-contract-and-dlopen-signing.kv`
>
> 同族去重：`DRAFT-E618-…-in-tree-plugin-module-subpackage`（子包**识别**、依赖归属、
> N 清点口径）、`DRAFT-E619-libheif-plugin-subpackage-delivery-surface`（交付面**裁剪**与
> 依赖边界判定）已覆盖「这个包该交付什么、依赖从哪来」。本条只写另一半：
> **交付之后怎么在消费者侧证明它真的被装载、以及 dlopen 对象在鸿蒙上的签名硬门禁**。

## 症状（三种「包能装、插件从不生效」的假绿）

| # | 假绿形态 | 为什么骗得过常规检查 |
|---|---|---|
| 1 | `lib/libheif/libheif-dav1d.so` 确实在包里，`readelf -h/-d` 全绿，`nm -D` 有 `plugin_info` 符号 | 交付面检查全部通过；**但没有任何东西 dlopen 过它** |
| 2 | `test_package` 链接 `libheif::libheif` 成功、`heif_get_version()` 正常 | 宿主库本身可用，与插件是否装载完全无关 |
| 3 | 设了 `LIBHEIF_PLUGIN_PATH` 后能力断言通过 | 证明的是**环境变量**对，不是**交付面**对；把变量去掉可能立刻失效 |

判据：**「配方导出的插件路径 == 产物实际所在目录」且「不额外设任何环境变量、
`heif_init()` 之后该后端的能力查询返回 1」二者同时成立，才是插件可用的证据。**
注意**不能**把判据写成"仅靠编译期内置路径（`LIBHEIF_PLUGIN_DIRECTORY`）"：那个宏是
configure 期的**构建目录**绝对路径，跨构建目录/跨机失效（本包实测：宿主 `libheif.so.1.23.0`
的 sha256 逐构建不同，正因为该路径被烧进了二进制；插件 `libheif-dav1d.so` 不含该引用，
故逐构建逐字节相同）。所以正确形态是**配方用 `runenv_info` 导出真实路径，
测试再断言这个导出值确实等于产物目录**——既不依赖失效的内置宏，也不靠"设对了环境变量"蒙绿。

## 根因（上游机制，逐字读 1.23.0 源码得到）

`libheif/api/libheif/heif_library.h:122-125` 明确写着：

> `heif_init()` will load the external modules installed in the default plugin path.
> Thus, you need it when you want to load external plugins from the default path.

装载路径（`libheif/init.cc:51-66`）：

```c
std::vector<std::string> get_plugin_paths() {
  plugin_paths = get_plugin_directories_from_environment_variable_unix();  // 读 LIBHEIF_PLUGIN_PATH
  if (plugin_paths.empty())
    plugin_paths.push_back(LIBHEIF_PLUGIN_DIRECTORY);   // 编译期钉死的绝对路径
  return plugin_paths;
}
```

`LIBHEIF_PLUGIN_DIRECTORY` 来自 `heif_version.h.in:36` 的 `@PLUGIN_DIRECTORY@`
（= `${CMAKE_INSTALL_FULL_LIBDIR}/libheif`）。扫描规则（`libheif/plugins_unix.cc`）：

```c
if (correct_filetype && strlen(d->d_name) > 3 &&
    strcmp(d->d_name + strlen(d->d_name) - 3, ".so") == 0)   // 只认以 ".so" 结尾的名字
```

即 `libheif-dav1d.so` 命中，而版本化实体 `libheif-dav1d.so.1.23.0` **不**命中——
所以 `install(TARGETS heif-<name> ...)` 生成的那条无版本软链是功能必需品，不是装饰。

### 鸿蒙特有：被 dlopen 的 .so 必须重新签名

这是本条的第二个可复用点，也是与「普通共享库」最大的差别：

* 鸿蒙 PC XPM 要求**被 `dlopen` 的 `.so`** 与被 `exec` 的可执行文件带有效 `.codesign` 段；
* 链接器给出的自签**会在 `cmake install` 的复制动作里失效**；
* 因此 `package()` 必须在装包**之后**重签，而不是在 `build()` 里签。

本仓 1102 个配方同口径，最小可用形态：

```python
def _sign_elf(self):
    if str(self.settings.os) != "OHOS":
        return
    signer = "/data/service/hnp/bin/binary-sign-tool"
    objcopy = "/data/service/hnp/bin/llvm-objcopy"
    if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
        return
    for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
        for filename in files:
            path = os.path.join(root, filename)
            if os.path.islink(path) or not os.path.isfile(path):
                continue                       # 只签真实 ELF，跳过版本化软链，避免重复签同一目标
            subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
            signed = path + ".signed"
            r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                                "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)
```

判据：**交付物里有 dt_needof/dlopen 目标的包，签名是交付面的一部分，不是可选优化**；
漏签的后果是运行期 `dlopen` 失败，而编译期与静态检查全绿。

### 消费者契约断言集（可直接复用的 test_package 形态）

#### 先避开一个静默陷阱：不要用 `IMPORTED_LOCATION` 反推包内路径

Conan 的 `CMakeDeps` 生成的 `<pkg>::<pkg>` 是 **INTERFACE IMPORTED** 目标
（实测 `<pkg>-Target-release.cmake` 只有 `add_library(<pkg>_DEPS_TARGET INTERFACE IMPORTED)`），
真实库路径放在 `INTERFACE_LINK_LIBRARIES` 的绝对路径里，**`IMPORTED_LOCATION_RELEASE`
与 `IMPORTED_LOCATION` 都是未设置的**。于是这段看起来很合理的 CMake：

```cmake
get_target_property(_loc libheif::libheif IMPORTED_LOCATION_RELEASE)
if(NOT _loc)
    get_target_property(_loc libheif::libheif IMPORTED_LOCATION)   # 同样取不到
endif()
get_filename_component(_libdir "${_loc}" DIRECTORY)                 # _loc 为空 → _libdir 为空
```

会**静默**退化成 `"/libheif/libheif-dav1d.so"` —— 于是"产物是否存在"的断言永远 FAIL
（或更糟：若断言写成"不存在就跳过"，就变成永久假绿）。
本项目实测：`libheif-dav1d` 首轮 test_package 打印
`plugin artifact under test : /libheif/libheif-dav1d.so`、13 条断言里 6 条 FAIL。

正确做法二选一：

```cmake
# ① CMake 侧：CMakeDeps 确实导出了 <pkg>_PACKAGE_FOLDER_<CONFIG>
set(HEIF_PLUGIN_FILE "${libheif_PACKAGE_FOLDER_RELEASE}/lib/libheif/libheif-dav1d.so")
```

```python
# ② Python 侧（更稳，不依赖生成物的变量命名）：test_package/conanfile.py 的 generate() 里
dep = self.dependencies[self.tested_reference_str]
tc.cache_variables["HEIF_PLUGIN_FILE"] = os.path.join(
    dep.package_folder, "lib", "libheif", "libheif-dav1d.so")
```

并在 `CMakeLists.txt` 里 `if(NOT DEFINED HEIF_PLUGIN_FILE) message(FATAL_ERROR ...)`，
让"没注入"变成硬失败而不是静默假路径。

#### 断言集

`test_package` 必须**运行**一个真消费者，并断言下面这组（本包 `test.c` 全部实现）：

```c
/* 1. 交付面：插件产物落盘且是 ELF —— 路径由被测包 package_folder 注入，不猜 */
stat(HEIF_PLUGIN_FILE) == 0 && S_ISREG && size > 0;
fread(magic,1,4,f) == 4 && magic == "\x7fELF";

/* 2. 版本面 */
heif_get_version(); heif_get_version_number_major(); heif_get_version_number_minor();

/* 3. 装载面：宿主扫描配置导出的插件目录（LIBHEIF_PLUGIN_PATH），
      并断言该变量确实等于产物所在目录（防"导出个名字但指错地方"） */
getenv("LIBHEIF_PLUGIN_PATH") != NULL;
strcmp(normalize(getenv("LIBHEIF_PLUGIN_PATH")), dirname(HEIF_PLUGIN_FILE)) == 0;
heif_init(NULL);                                   /* 不调用它，外部插件永远不会被装载 */
heif_have_decoder_for_format(heif_compression_AV1) == 1;   /* 本包后端生效 */

/* 4. 负对照：证明不是别处的后端把测试蒙绿 */
heif_have_decoder_for_format(heif_compression_HEVC) == 0;
heif_have_encoder_for_format(heif_compression_AV1) == 0;   /* dav1d 是纯解码后端 */
```

**负对照是本条最容易被省掉、也最不该省的一步**：只断言「AV1 解码可用」时，
任何别的 AV1 后端（aom / 系统 libheif / 内置 fallback）都能让断言变绿；
加上「HEVC 解码必须缺席」，就把「本包只提供 dav1d 一条 AV1 解码路径」钉死了。

#### 宿主没有 SONAME 时，插件链接的是相对路径（同族共踩）

插件 MODULE `target_link_libraries(... heif)` 记录进 `DT_NEEDED` 的是宿主**链接时给出的路径**，
宿主有 SONAME 时记 SONAME、没有 SONAME 时记路径本身。OHOS 的 CMake 缺
`Platform/HarmonyOS.cmake`，落"未知平台"回退 → 宿主不写 SONAME、不出带版本的文件名
→ 实测插件 `DT_NEEDED` 里出现 **`[../libheif.so]`**（含斜杠 → 按 CWD 解析）→
`heif_init()` 的 `dlopen` 失败。修法：`tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`
走 `Platform/Linux.cmake`，宿主得到 SONAME `libheif.so.1`，`DT_NEEDED` 变无斜杠。
**注意**：`cache_variables` 由 Conan 以 `-D` 送给主工程（实测 configure 行含
`-DCMAKE_SYSTEM_NAME="Linux"`）；若另外用 `-DCMAKE_TOOLCHAIN_FILE=…` 单独 configure
子工程/测试构建，那边必须**显式再传** `-DCMAKE_SYSTEM_NAME=Linux`。

### 运行期可选依赖的边界（决定断言写法）

插件把后端库变成宿主的**运行期可选依赖**，依赖边落在插件上而不是宿主上：
`readelf -d libheif-dav1d.so` 有 `libdav1d.so`，而 `readelf -d libheif.so` 没有。
后果：消费者只装宿主不会因缺后端而**加载失败**，只会**能力缺席**。
所以契约只能断言**能力**（`heif_have_*_for_format`），不能断言「链接成功」——
后者对插件型子包恒真，是结构性的假绿面。

## 复现命令（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/libheif-dav1d-1.23.0
sh "$TASK_DIR/run-upstream-tests.sh"          # 上游 ctest（BUILD_TESTING=ON 原生构建）
# 插件装载与签名：
PKG=$(conan cache path libheif-dav1d/1.23.0:<package_id>)
readelf -S "$PKG/lib/libheif/libheif-dav1d.so" | grep -i codesign
readelf -d  "$PKG/lib/libheif/libheif-dav1d.so" | grep NEEDED     # → libdav1d.so, libheif.so
readelf -d  "$PKG/lib/libheif.so"               | grep -i dav1d   # → 空（依赖不在宿主上）
```

## 实测读数

设备：HarmonyOS PC aarch64，OHOS SDK `ohos-sdk_26.0.0.18`（clang 15.0.4，libc++ 15004），
profile `ci/conan/profiles/ohos-aarch64`，`conan create` 结果 `rc=0`。

### 三个"修前 → 修后"对照（全部来自本包真实构建）

| 项 | 修前 | 修后 |
|---|---|---|
| 宿主 SONAME | 无（`llvm-readelf -d` 无 SONAME 行；包里只有 `libheif.so`，无 `.so.1` / `.so.1.23.0`） | `SONAME libheif.so.1`；包内 `libheif.so` / `.so.1` / `.so.1.23.0` 三件套齐 |
| 插件宿主 `DT_NEEDED` | `Shared library: [../libheif.so]`（含斜杠） | `Shared library: [libheif.so.1]` |
| `test_package`（13 条断言） | 6 FAIL（`lib/libheif/libheif-dav1d.so exists` 等产物断言全 FAIL，`plugin artifact under test : /libheif/libheif-dav1d.so`） | **13/13 PASS**，打印真实路径 `<package_folder>/lib/libheif/libheif-dav1d.so` |

### 安装期改写与装后重签（自己包内的插件产物）

以下读数取自**现存采信轮包**（`conan_verify_round.sh` ROUND_RC=0 产物）：

| 读数 | 构建树（安装前） | 包内（装后重签） |
|---|---|---|
| 插件 sha256 | `7916303b93283ab522ba7960b9cd4079d020b53c4832ce7b610766c6b72ef314` | `848fc43f7c7a80385cf70bd30c6319ab686d5d49c1ab4c3060ac192c8082a65b` |
| 字节数 | 68032 | 68032（**同尺寸**） |
| `RUNPATH` | `<dav1d-pkg>/lib:<build>/libheif:` | **无（0 条）** |
| `.codesign` | 有 | **有**（装后重签写入） |

宿主 `libheif.so.1.23.0` 同样被改写并被重签：构建树 `645551993fa2fa2525f245e734e00a451b43e8f8977c54f82a1531af316a2526`
→ 包内 `fbe1208c67ed16e0…`（完整值随构建目录变化，见下），`.codesign` 仍在。

**跨构建差异本身就是"内置路径不可移植"的最强证据**（两个不同构建目录各产物一次实测）：

| 产物 | 构建 A（开发轮） | 构建 B（采信轮） | 结论 |
|---|---|---|---|
| 插件 `libheif-dav1d.so` | `848fc43f…` | `848fc43f…` | **逐字节相同**：插件不引用插件目录宏 |
| 宿主 `libheif.so.1.23.0` | `1d6762e4…`（另一构建目录） | `fbe1208c…` | **逐构建不同**：`LIBHEIF_PLUGIN_DIRECTORY`（= 构建期 `package_folder`）被烧进宿主 |

即宿主二进制里带着"构建时那个包目录"的字符串，换个构建目录产物就变——
这正是必须由配方在 `package_info()` 里导出运行期插件路径、而不能依赖内置宏的原因。

> 判据以**功能性证据**收口：`test_package` 的
> `heif_init() scans and loads the plugin directory` 与
> `AV1 decoder registered => libheif-dav1d.so was dlopen'd and is functional` 两条 PASS，
> 即插件确实被 `dlopen` 成功。**只比宿主 sha256 会漏判**——先比"自己包内的插件产物"。

### 插件目录可移植性

`configure` 行逐字含 `-DCMAKE_INSTALL_PREFIX="<build-pkg-folder>"`，即
`LIBHEIF_PLUGIN_DIRECTORY` 被烧成**构建期**绝对路径（`.../p/b/<hash>/p/lib/libheif`），
而 `conan create` 结束后包落在 `.../p/<name><hash>/p`，下载安装的消费者更没有该构建目录。
故配方用 `runenv_info.define_path("LIBHEIF_PLUGIN_PATH", <package_folder>/lib/libheif)` 导出；
`test_package` 断言"导出值 == 产物实际所在目录"。内置宏指向的构建目录在本机尚未清理时**看似**可用，
但上表已证明它随构建目录变化，**是巧合而非保证**，不作为依据。

### 上游用例里的端到端 AVIF 解码

`mini_decode` 的 `check image handle size` PASS，逐字用到上游夹具
`tests/data/simple_osm_tile_alpha.avif`（`REQUIRE(ispe_width == 256)` 通过），
即"真 AVIF → 交付宿主 libheif → dlopen dav1d 插件 → 解出图像句柄"这条链路在设备上成立。

## 关联

* `DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage`（子包识别 / 依赖归属 / N 口径）
* `DRAFT-E619-libheif-plugin-subpackage-delivery-surface`（交付面裁剪 / 依赖边界）
* `archives/d/dav1d/1.5.0/conanfile.py`（`_sign_binaries` 同口径的独立包先例）
* `knowledge/doc/E077`（鸿蒙 ELF 需有效 `.codesign` 段才能被内核加载）
