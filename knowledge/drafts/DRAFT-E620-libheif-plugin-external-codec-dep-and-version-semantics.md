# DRAFT-E620 — libheif 插件子包对外部编解码库的依赖声明与版本口径

> 对应条目：`knowledge/drafts/DRAFT-E620-libheif-plugin-external-codec-dep-and-version-semantics.kv`
> 适用族：`libheif-{openjpeg,aom,jpeg,svtenc,dav1d,libde265,openh264}`（1.23.0）
> 证据来源：本任务（libheif-openjpeg 1.23.0）设备实测，日志与命令逐字列在下面。

## 1. 一句话

子包 `libheif-<codec>` 的**包名是 codec 名、版本号是父 tarball 版本**，而它的依赖声明要同时
跨过三道"名字不一致"：`find_package` 名 ≠ conan 包名 ≠ 变量前缀大小写。任一道没过，
configure **不报错**、包照样建出来，但后端被静默跳过（`Not compiling '…' backend`），
交付物里没有插件——典型假绿。

## 2. 两条版本轴必须分开读

| 维度 | 值 | 说明 |
|---|---|---|
| 子包 ref | `libheif-openjpeg/1.23.0` | 版本 = **父 tarball**（libheif 1.23.0）的版本，不是 OpenJPEG 的 |
| `conandata.yml` url/sha256 | libheif v1.23.0 tag 归档 | 与父包、与同批 6 个兄弟包**同一份 tarball** |
| codec 版本 | `requires("openjpeg/2.5.4")` | OpenJPEG 本体版本只在这里出现 |

推论：不能按"包名 = 软件名"去 `search_url` 找 `libheif-openjpeg-1.23.0.tar.gz`——设备实测
`init-build --auto` 会给出 4 个同名异源/停放页候选（savannah、waterlan.home.xs4all.nl）并
因字节头不是 gzip 而全部否决（rc=1）；正确做法是 `--url <父 tarball 官方 tag URL>`
（配合 `OHC_INIT_BUILD_TARBALL` 离线种子，同批共用一份 tarball）。

## 3. 三个"名字不一致"

以 openjpeg 为例（其余 codec 同构，只是变量名不同）：

| 层 | 值 | 出处 |
|---|---|---|
| 上游 `find_package` | `OpenJPEG`（+ 版本 2） | `CMakeLists.txt:267` `find_package(OpenJPEG 2)` |
| conan 包名 | `openjpeg`（历史包 `openjpeg2`） | `archives/o/openjpeg/2.5.4`、`archives/o/openjpeg2/2.5.4` |
| CMakeDeps 文件名 | `cmake_file_name` 决定 | `openjpeg/2.5.4` 里是 `OpenJPEG`（命中）；`openjpeg2/2.5.4` 是 `openjpeg2`（**不命中**） |
| 消费方判存在用的变量 | **全大写** `OPENJPEG_FOUND` / `OPENJPEG_LIBRARIES` / `OPENJPEG_INCLUDE_DIRS` | 宏体 `libheif/plugins/CMakeLists.txt:2-45`（`:21` 用 `${varName}_INCLUDE_DIRS`、`:22` 用 `${varName}_LIBRARIES`），j2kdec/j2kenc 注册在 `:86,90` |

注意上游自己就不一致：顶层 `CMakeLists.txt:374` 用正确大小写 `OpenJPEG_FOUND`，
而 `plugin_compilation()` 宏用 `OPENJPEG_FOUND`。**决定交付面的是后者**。

### 3.1 为什么默认配置必然静默降级（三态实测）

1. CMakeDeps 默认 `cmake_find_mode=config` → 只生成 `OpenJPEGConfig.cmake`，里面对**大写**
   `OPENJPEG_FOUND` 只字不提（config 模式没有 `additional_variables_prefixes` 的 `_FOUND` 赋值，
   只有 module 模式模板才 `set({{prefix}}_FOUND 1)`，见
   `conan/tools/cmake/cmakedeps/templates/config.py:140-143` 的 `{% if is_module %}` 分支）；
2. 即使同时生成 config+module（`cmake_find_mode=both`），CMakeToolchain 默认
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`（`conan/tools/cmake/toolchain/blocks.py:678`），
   **config 先赢** → 仍然没有 `OPENJPEG_FOUND`；
3. `plugin_compilation()` 的 `if (${foundName} AND WITH_${optionName})` → 假 →
   `message("Not compiling '" ${name} "' backend")` → 不 `add_library(heif-j2kdec MODULE …)`、
   不 install。**exit code 全程 0**。

设备实测三态对照（同机同依赖，只改 `set_property`；原始读数
`$TASK_DIR/cmakedeps-three-way-evidence.txt`，逐字日志
`$TASK_DIR/dep-wiring-evidence/probe-{config,both,openjpeg}-cmake.log`）：

| CMakeDeps 配置 | 生成的发现文件 | `OpenJPEG_FOUND` | `OPENJPEG_FOUND` | `OPENJPEG_LIBRARIES` | 后果 |
|---|---|---|---|---|---|
| 默认（config，无 `set_property`） | `OpenJPEGConfig.cmake` | 1 | **（空）** | **（空）** | `Not compiling 'j2kdec' backend` |
| `both` + `OPENJPEG` 前缀 | Config + Find 两套 | 1 | **（空）** | `OPENJPEG::OpenJPEG` | 仍静默降级 |
| `module` + `OPENJPEG` 前缀（本包采用） | 仅 `FindOpenJPEG.cmake` | 1 | **1** | `OPENJPEG::OpenJPEG` | `Compiling 'j2kdec' as dynamic plugin` ✅ |

三态的 `conan install` 与 `cmake configure` **退出码都是 0**。

### 3.2 正确形态（消费方 `generate()` 覆盖属性，上游源码零修改）

```python
deps = CMakeDeps(self)
deps.set_property("openjpeg", "cmake_find_mode", "module")
deps.set_property("openjpeg", "cmake_additional_variables_prefixes", ["OPENJPEG"])
deps.generate()
```

设备实测（`$TASK_DIR/probe-openjpeg/`，cmake configure 输出）：

```text
FindOpenJPEG.cmake:35  set(OPENJPEG_INCLUDE_DIRS ${openjpeg_INCLUDE_DIRS_RELEASE} )
FindOpenJPEG.cmake:37  set(OPENJPEG_LIBRARIES ${openjpeg_LIBRARIES_RELEASE} )
FindOpenJPEG.cmake:63  set(OPENJPEG_FOUND 1)
-- PROBE OpenJPEG_FOUND=1
-- PROBE OPENJPEG_FOUND=1
-- PROBE OPENJPEG_INCLUDE_DIRS=…/p/openj175ac3bcf1357/p/include/openjpeg-2.5
-- PROBE OPENJPEG_LIBRARIES=OPENJPEG::OpenJPEG
-- PROBE OpenJPEG_VERSION=2.5.4
-- PROBE OPENJPEG_MAJOR_VERSION=      ← 空；因为首轮 find_package 已命中，上游的 2.x 兜底分支不会执行
```

`find_package(OpenJPEG 2)` 的版本检查由 module 内的
`find_package_handle_standard_args(OpenJPEG … VERSION_VAR OpenJPEG_VERSION)` 承担：2.5.4 ≥ 2 通过。

同族先例：`archives/l/leptonica/1.85.0/conanfile.py` 也为自己设了
`deps.set_property("openjpeg", "cmake_additional_variables_prefixes", ["OPENJPEG"])`。

### 3.3 反例：选了 `openjpeg2/2.5.4`

`archives/o/openjpeg2/2.5.4` 是同一上游库的另一个配方，`cmake_file_name="openjpeg2"`、
`cmake_target_name="openjpeg2::openjpeg2"`，**命中不了** `find_package(OpenJPEG 2)`；
且它是仓库里少数派（1 个已合并包在用，`openjpeg/2.5.4` 有 4 个）。选它 = 后端静默消失。

## 4. 依赖前置：必须是"有配方且已发布 binary"的包（R35/R36）

- 用 `conan install --requires=openjpeg/2.5.4 --build=never` **真跑**验证（R35 禁止用
  `conan list/search` 判 binary 存在）；
- `archives/` 下存在只有 `manifest.yaml`/`notes.md` 的"元数据孤儿"包——对它们写 `requires()`
  会在 `finish` step[5/10] 与 CI L0i（`conan download --only-recipe`）Hard Fail；
- 本任务实测（`$TASK_DIR/pipeline-logs/s1-08-w0-deps.log`）：

```text
Requirements
    openjpeg/2.5.4#9f4e31751289e8fdf8faec21932895ed - Downloaded (ohpcd)
    openjpeg/2.5.4#…:30a828c3393c8a79c509dc8bed859f16757b162f#98a1e2430800b5723e771b77da9f2a0f - Download (ohpcd)
openjpeg/2.5.4: Package installed 30a828c3393c8a79c509dc8bed859f16757b162f
--- W0 OK: openjpeg/2.5.4
```

## 5. 配套的反假绿动作（写进配方）

1. **构建期判据**：日志里必须出现 `Compiling 'j2kdec' as dynamic plugin` /
   `Compiling 'j2kenc' as dynamic plugin`（反面：`Not compiling '…' backend`）；
2. **打包期自检**：`package()` 末尾断言 `<pkg>/lib/libheif/libheif-j2kdec.so*` 与
   `libheif-j2kenc.so*` 存在、`lib/libheif.so*` 存在，缺失即 `ConanException`——
   把上游的"静默降级"变成硬失败；
3. **特性级检查**（W0/agent_review 要求）：
   `readelf -d <pkg>/lib/libheif/libheif-j2kdec.so | grep NEEDED` 应含 `libopenjp2.so.*`
   （证明依赖真被链接，而不是恰好命中了系统同名库）；
   `nm -D`/`strings` 应能命中 `opj_*` 符号。

## 6. 复现命令（设备可直接执行，落 `$TASK_DIR`）

```sh
TASK_DIR=$HOME/tmp/libheif-openjpeg-1.23.0
sh "$TASK_DIR/verify-openjpeg-dep-wiring.sh"
```

脚本做四件事（rc≠0 即复现失败）：① `conan install --requires=openjpeg/2.5.4 --build=never`
真拉依赖；② 生成 CMakeDeps 并 cmake configure，打印 `OpenJPEG_FOUND`/`OPENJPEG_FOUND`/
`OPENJPEG_LIBRARIES`；③ 从采信轮日志里取 `Compiling 'j2kdec' as dynamic plugin`；
④ `readelf -d` 插件模块的 `DT_NEEDED`。

## 7. 与 E619 的分工

E619 讲**交付面裁剪与依赖边界**（要不要自包含宿主、插件目录不可移植、MODULE 不能单独交付）；
本条只讲**依赖怎么声明、版本怎么读、名字怎么对上**（CMakeDeps 形态 + 版本双轴 + 反假绿自检）。
两条可同时命中同一份日志，不重复。
