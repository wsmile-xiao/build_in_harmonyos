# DRAFT-E621-libheif-svtenc：「编码器后端」插件子包的构建开关矩阵与 SIMD/多线程能力口径

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-20
> Source: `libheif-svtenc` 1.23.0 适配（HarmonyOS PC，积分赛/新包）
> 对应：`knowledge/drafts/DRAFT-E621-libheif-svtenc-1.23.0-encoder-plugin-options-and-cpu-thread-capability.kv`

## 问题

子包的**判类与交付面归属**（`libheif-svtenc` = 树内目标 `heif-svtenc` → `libheif-svtenc.so`）
已由 `DRAFT-E618` 覆盖。本条只记三件在「**编码**后端」上必然会踩、且都表现为**假绿**的事：

1. **开关矩阵**：哪些 `WITH_*` 组合才真的产出 `libheif-<name>.so`？默认值能不能照抄同族先例？
2. **能力口径**：插件文件在、甚至 `heif_have_encoder_for_format()==1`，凭什么说"编码器可用"？
3. **CPU/多线程特性**：OHOS 上 `__linux__` 与 `__OHOS__` 同时定义会把上游哪条分支选走？
   排除掉一个 Linux-only 调用（`pthread_setaffinity_np`）算"修好了"还是"退化了"？

## 一、开关矩阵：三件套缺一不可，默认值矩阵是不对称的

libheif 1.23.0 `CMakeLists.txt:101-104`：

```cmake
macro(plugin_option optionVariableName displayName defaultEnabled defaultPlugin)
    option(WITH_${optionVariableName}        "Build ${displayName}"                    ${defaultEnabled})
    option(WITH_${optionVariableName}_PLUGIN "Build ${displayName} as a plugin"        ${defaultPlugin})
endmacro()
```

实参矩阵（**编码器与解码器不同，别照抄**）：

| 后端 | 类型 | `WITH_X` 默认 | `WITH_X_PLUGIN` 默认 |
|---|---|---|---|
| `LIBDE265` | 解码 | **ON** | OFF |
| `DAV1D` | 解码 | **OFF** | **ON** |
| `SvtEnc` / `RAV1E` / `OpenJPEG_*` / `OPENJPH_ENCODER` | 编码（+J2K 解码） | **OFF** | **ON** |
| `X265` / `X264` / `AOM_ENCODER` | 编码 | **ON** | OFF |

而 `libheif/plugins/CMakeLists.txt:1-50` 的 `plugin_compilation()` 只有三种出口：

```
① found ∧ WITH_X ∧ PLUGIN_LOADING_SUPPORTED_AND_ENABLED ∧ WITH_X_PLUGIN
     → add_library(heif-<name> MODULE …)      ← 唯一产生命名产物的分支
② found ∧ WITH_X（插件条件不成立）
     → target_sources(heif PRIVATE …)         ← 静默静态编入宿主
③ 其余
     → message("Not compiling '<name>' backend")  ← 静默什么都不编
```

② 与 ③ 都 **exit 0、无告警**，而包名所指的 `libheif-<name>.so` 根本不存在——
"构建成功"与"交付面为空"可以同时成立。**判据必须落在产物上**：
构建日志出现 `Compiling '<name>' as dynamic plugin`，且 install 树里有 `libheif-<name>.so`。
其余后端全部显式置 `False`（否则默认值会引入未发布依赖，直接触发 R36 门禁）。

## 二、能力口径：三件套，register-only 不算证据

```
① readelf -d <pkg>/lib/libheif/libheif-svtenc.so | grep NEEDED
     → 必须同时有宿主 libheif.so 与后端运行库 libSvtAv1Enc.so*
② 宿主侧注册断言 + 反证
     heif_have_encoder_for_format(heif_compression_AV1) == 1
     heif_have_decoder_for_format(heif_compression_AV1) == 0   ← 本包没启用 dav1d/aom
     heif_have_encoder_for_format(heif_compression_HEVC) == 0  ← 本包没启用 x265
③ 真跑一次编码并把输出落盘断言非空
     heif_context_get_encoder_for_format(ctx, AV1, &enc)
     heif_encoder_set_lossy_quality(enc, 60)
     heif_context_encode_image(ctx, img, enc, NULL, &handle)
     heif_context_write_to_file(ctx, "out.avif")  → size > 0
```

只有 ③ 会走到后端的**配置校验、线程创建、SIMD 分派**代码路径。①② 全绿而 ③ 失败
（库缺失、参数不兼容、CPU 特性分支崩）在插件形态里完全可能——所以
`test_package` 的功能断言必须是 ③，反证断言（②）用来排除"其实是别的后端在应答"。

## 三、CPU / 多线程：`__linux__` ∧ `__OHOS__` 双定义口径

```sh
printf '#ifdef __OHOS__\nOHOS_YES\n#endif\n#if defined(__linux__)\nLINUX_YES\n#endif\n' > m.c
/data/service/hnp/bin/clang -E m.c | grep -E 'OHOS_YES|LINUX_YES'
#   → 两行都打印：OHOS_YES / LINUX_YES
```

OHOS 的 clang（15.0.4，target `aarch64-unknown-linux-ohos`）**两个宏都定义**，于是上游
所有 `#if defined(__linux__) && !defined(__ANDROID__)` 的 Linux-only 分支在 OHOS 上一律被
选中。SVT-AV1 3.1.2 的 `Source/Lib/Codec/svt_threads.h` 就是这样：

```c
#if defined(__linux__) && !defined(__ANDROID__)
#define EB_CREATE_THREAD(...)  … pthread_setaffinity_np(…) …   /* OHOS 不提供该函数 */
#else
#define EB_CREATE_THREAD(...)  … svt_create_thread(…) …       /* 仍能建线程，只是不钉核 */
#endif
```

口径三条：

1. **"定义了 `__OHOS__`" 是需要排除它的理由，不是跳过补丁的理由**——要判的是这个
   Linux-only 分支**是否被选中**；
2. 排除后线程照建、只是不再设置线程亲和 → 这是**功能退化**，notes 要写清退化范围与
   替代验证（真跑编码），既不能写"无影响"，也不能把"链接通过"当适配完成；
3. SIMD 侧：aarch64 走 NEON、**不需要 NASM**；configure 的 `HAVE_ARM_PLATFORM` /
   `NEON_FLAG_SUPPORTED` 只是探测，真判据是编译日志里出现 `ASM_NEON` 目标对象（本任务
   实测 `-DHAVE_NEON=1 -DHAVE_NEON_DOTPROD=1 -DHAVE_NEON_I8MM=1`，`HAVE_SVE/SVE2=0`）
   加上运行期真跑（②③）。

## 四、平台模块与 SONAME（插件形态下是硬伤）

```sh
readelf -d <build>/libSvtAv1Enc.so | grep SONAME      # 无输出 ⇒ 中招
readelf -d <pkg>/lib/libheif/libheif-svtenc.so | grep NEEDED
#   中招时：NEEDED ../libheif.so（带斜杠 → 按 CWD 解析）→ 运行期 dlopen 必失败
```

设备 `uname -s` 报 `HarmonyOS`，而 SDK 的 CMake 只有 `Platform/OHOS.cmake`、**没有**
`Platform/HarmonyOS.cmake` → CMake 落"未知平台"回退（配置期打印
`System is unknown to cmake, create: Platform/HarmonyOS`），`CMAKE_SHARED_LIBRARY_SONAME_*`
未定义 → 共享库不带 SONAME → 链接插件的 MODULE 时把**构建期路径**写进 `DT_NEEDED`。
构建期全绿、运行期 `heif_init()` dlopen 失败，正是 `archives/l/libheif/1.18.2/notes.md`
记的"NEEDED 硬编码相对路径、未解决"。

修法：`generate()` 里 `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"`。**必须用 `variables`
而不是 `cache_variables`**——只有 `variables` 会落进 `conan_toolchain.cmake`，内树子工程
复用同一份 toolchain 时才一并生效；子工程若用 `-DCMAKE_TOOLCHAIN_FILE` 单独 configure，
仍应再显式传一次 `-DCMAKE_SYSTEM_NAME=Linux` 兜底。仓库 693 个配方同口径。

## 五、编码器不在制品仓时的接线（R36 机械门禁下唯一可行解）

`self.requires("svt-av1/…")` 不可行：`finish` step[5/10] 与 CI L0i 都对每个 `requires()`
跑 `conan download --only-recipe`，远端没有该包 → 必然 HANDOFF。
可行解 = **包内树构建该编码器**（已合并先例：`archives/h/handbrake/1.11.2` 的 33 个 contribs）：

```yaml
# conandata.yml —— 独立键，不放 sources（sources 是父 tarball 身份）
svt_av1:
  url: [ "<官方 gitlab 归档>", "<官方 github 镜像>" ]   # 列表：Conan get() 逐个回退
  sha256: "<自算>"
patches:                                              # 列表形态；补丁定向到子目录
  - patch_file: "patches/0001-….patch"
    base_path: "svt-av1"                              # ← 作用于内树构建的依赖，不动父 tarball
    strip: 1
    patch_type: "portability"
```

要点：URL 必须在 `conandata.yml`（CI 的 mirror-fallback 与 pre-download **只扫这个文件**）；
子构建复用 `CMakeToolchain` 生成的 `conan_toolchain.cmake`（R33：编译器来自 profile，不读
shell 变量）；安装到 `build_folder` 下的私有 prefix（R49）；`SVT_AV1_LTO=OFF` 规避交叉工具链
的 LTO/`llvm-ar` 链路风险；`tools.build:jobs=1`（设备 affinity=8 而 `os.cpu_count()=20`）。

## 复现命令

```sh
# 开关矩阵与分支出口
grep -n 'plugin_option(' "$TASK_DIR/upstream/libheif-1.23.0/CMakeLists.txt"
sed -n '1,50p' "$TASK_DIR/upstream/libheif-1.23.0/libheif/plugins/CMakeLists.txt"
# 双定义口径
printf '#ifdef __OHOS__\nOHOS_YES\n#endif\n#if defined(__linux__)\nLINUX_YES\n#endif\n' > "$TASK_DIR/probe/m.c"
/data/service/hnp/bin/clang -E "$TASK_DIR/probe/m.c" | grep -E 'OHOS_YES|LINUX_YES'
# 依赖面（R35 + 对照组）
conan install --requires=svt-av1/4.1.0 --build=never -pr:h="$HOST_PROFILE"   # rc=1
conan download --only-recipe libde265/1.0.18 -r=ohpcd                        # rc=0 对照
# 交付面能力证据
readelf -d <pkg>/lib/libheif/libheif-svtenc.so | grep NEEDED
```

## 关联

* `DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage`（子包判类与交付面归属）
* `DRAFT-msquic-2.6.1-pthread-setaffinity-np-android-guard`（同一 `__OHOS__` 排除形态）
* `DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms`（宿主 C++20 能力缺口，本任务实测命中）
* `archives/h/handbrake/1.11.2`（内树构建 svt-av1 的已合并先例）、`archives/l/libheif/1.22.2`
