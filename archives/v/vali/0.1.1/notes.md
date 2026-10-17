# vali 0.1.1 适配笔记

> 路径：路径A（基础适配） ｜ 平台任务 ID：11599 ｜ 任务分支：`feat/vali-0.1.1`
> 上游：https://gitlab.freedesktop.org/emersion/vali ｜ 许可证：MIT
> 认领日期：2026-10-03（平台 `claimedAt=2026-10-03T14:10:10Z`） ｜ 状态：适配中
> 依赖：`json-c/0.18`（制品仓裸 ref）、`aml/1.0.0`（制品仓裸 ref） ｜ 构建工具：`meson/1.11.0`（tool_requires）

---

## 1. 上游事实（对 v0.1.1 tarball 实测审计）

| 项 | 值 |
|---|---|
| tarball | `vali-0.1.1.tar.gz`（**release 资产**），**30493 bytes** |
| sha256 | `791785eca66392f91f28ca371ba9cfa2dc11915df0bff9f590a33453f67e5756` |
| 解包根目录 | `vali-0.1.1/`（单根目录，`strip_root=True` 可用） |
| 语言 | C（`default_options: ['c_std=c11', ...]`） |
| 构建系统 | Meson（`meson_version: '>=1.0'`） |
| 外部依赖 | `json-c`（报文编解码）、`aml`（事件循环）；均为纯 C |
| 许可证文件 | `LICENSE`（MIT） |
| 安装产物 | `lib/libvali.so.0.1.1` / `libvali.a`（`soversion=1`）+ `bin/vali`（代码生成器）+ `include/vali.h` + `lib/pkgconfig/vali.pc` |

源码规模（行数 / 字节，逐文件实测）：

| 文件 | 行数 | 字节 | 角色 |
|---|---|---|---|
| `tool.c` | 1436 | 42038 | `bin/vali` 主体：`.varlink` → C 代码生成器 |
| `def.c` | 771 | 15963 | Varlink 接口定义（IDL）解析与校验 |
| `service.c` | 460 | 10901 | 服务端：`vali_service_*`（含 aml 事件循环接入） |
| `client.c` | 204 | 5205 | 客户端：`vali_client_*` |
| `registry.c` | 181 | 5812 | 接口注册表服务 |
| `conn.c` | 177 | 3631 | 连接层（socket / 报文收发） |
| `util.c` | 30 | 538 | 公共工具（被 tool 与 lib 共用） |
| `include/vali.h` | 367 | 10050 | **唯一安装的公共头** |
| `include/conn.h` / `def.h` / `util.h` | 38 / 77 / 15 | 670 / 1402 / 199 | 内部头，**不 install** |
| `test/basic.c` | 167 | — | 上游测试 1 |
| `test/certification.c` | 923 | — | 上游测试 2（Varlink 官方认证套件） |

### 1.1 `meson.build` 关键点（逐条核对）

```meson
project('vali', 'c', version: '0.1.1', license: 'MIT', meson_version: '>=1.0',
        default_options: ['c_std=c11', 'warning_level=3', 'werror=true',
                          'wrap_mode=nodownload'])

cc = meson.get_compiler('c')
add_project_arguments(['-D_POSIX_C_SOURCE=200809L'], language: 'c')
add_project_arguments(cc.get_supported_arguments([
    '-Wundef', '-Wmissing-prototypes', '-Walloca', '-Wconversion',
    '-Wno-unused-parameter', '-Wno-missing-field-initializers',
    '-Werror=implicit',
]), language: 'c')

inc   = include_directories('include')
jsonc = dependency('json-c')
aml   = dependency('aml', 'aml1')          # ← pkg-config 双名回退

tool = executable('vali', ['tool.c', 'def.c', 'util.c'], include_directories: inc, install: true)

org_varlink_service = custom_target('service_iface',
    command: [tool, 'generate', '@INPUT@', '@OUTPUT0@', '@OUTPUT1@'],
    input:  'org.varlink.service.varlink',
    output: ['org.varlink.service.h', 'org.varlink.service.c'])

lib = library('vali', ['client.c', 'service.c', 'registry.c', 'conn.c', 'util.c',
                       org_varlink_service],
              include_directories: inc, dependencies: [jsonc, aml],
              install: true, version: version, soversion: version_minor)

install_headers(['include/vali.h'])

pkgconfig.generate(lib, name: 'vali', description: 'Varlink generator',
                   requires: ['json-c'],            # ← 漏了 aml
                   variables: ['tool=${bindir}/vali'])

vali = declare_dependency(link_with: [lib], dependencies: [jsonc],
                          include_directories: inc, variables: ['tool=vali'])
meson.override_find_program('vali', tool)
meson.override_dependency('vali', vali)

subdir('example')     # 无 test() 注册，但两个 executable 会参与编译
subdir('test')        # 注册 2 条 test()
```

**四个必须记住的点**：

1. **`werror=true` + `warning_level=3` 写死在 `default_options` 里**，另外还有一组
   `-Wundef -Wmissing-prototypes -Walloca -Wconversion`（经 `get_supported_arguments`
   过滤后仍然全部被 clang 接受）。上游 CI 用 `meson setup build/ --fatal-meson-warnings`。
   ⇒ 只要 clang 15 比上游的编译器多报一条 warning，构建就会**失败**（见 §4）。
2. **`org_varlink_service` 是构建期自举的 `custom_target`**：它用**刚刚编译出来的**
   `bin/vali` 去生成 `org.varlink.service.{h,c}`，而这两个文件又参与 `library('vali')` 的编译。
   即"被构建的产物同时是构建过程要用的工具"。本例是**原生构建**，可直接运行，无影响；
   但若改成交叉编译，必须另提供可执行的 host 版 `vali`。
3. `dependency('aml', 'aml1')` 是 pkg-config **双名回退**写法。aml 包的
   `pkg_config_name` 是 `aml1`（其 `aml1.pc` 里 `Libs: -laml -lrt -pthread`，
   `Cflags: -I${includedir}/aml1 -pthread`）。只写 `dependency('aml')` 会找不到。
4. `pkgconfig.generate(..., requires: ['json-c'])` **只声明了 json-c，漏掉 aml**：
   `vali.h` 不暴露 aml（自包含，只 `#include <stdbool.h>`），但 `service.o` 里有
   `aml_*` 未定义符号。静态链接的下游照 `vali.pc` 取参数就会缺 aml 符号（见 §9 第 1 条）。

### 1.2 `test/meson.build` 与 `example/meson.build`

```meson
# test/
test_gen = custom_target('test_gen', command: [tool, 'generate', '--prefix=test', ...],
                         input: 'test.varlink', output: ['test-gen.h', 'test-gen.c'])
test_basic = executable('basic', ['basic.c', test_gen], dependencies: vali)
test('basic', test_basic)

certification = executable('certification', ['certification.c', certification_gen],
                           dependencies: [vali, jsonc])
test('certification', certification, args: ['self-test'])
```

- 上游**注册 2 条 `test()`**：`basic` 与 `certification`（后者以 `self-test` 运行）。
- `example/` 只建两个 `executable`（`client` / `service`），**不注册测试**，但**照样参与
  编译**（因此也会被 werror 检查）。
- 三条 `custom_target` 全部调用 `bin/vali` 生成代码：`service_iface`（lib 用）、
  `test_gen`、`certification_gen`、`example_gen`。**自举点共 4 处**。

### 1.3 `test/basic.c` 硬要求 NDEBUG 关闭（本仓特有的关键约束）

```c
#ifdef NDEBUG
	fprintf(stderr, "NDEBUG must be disabled for tests\n");
	return 1;
#endif
```

上游自己的 CI 用**默认 `buildtype=debug`**（`.builds/alpine.yml` 只写
`meson setup build/ --fatal-meson-warnings`，没写 `--buildtype`），所以这个约束
在上游**永远不会暴露**。而我们的 CI profile 是 `build_type=Release`，
conan `MesonToolchain` 默认写 `b_ndebug = 'true'` ⇒ NDEBUG 被定义 ⇒ 上游 `basic`
测试**必然失败**。⇒ 配方必须显式 `tc.b_ndebug = "false"`。

### 1.4 上游运行机制的实测扫描结论

| 扫描项 | 命令（在解包源码根目录） | 结果 |
|---|---|---|
| GNU/BSD 扩展 | `grep -nE 'asprintf\|strchrnul\|qsort_r\|getline\|err\(' *.c include/*.h` | **零命中** |
| 线程 API | `grep -nE 'pthread_\|clock_gettime\|timer_' *.c include/*.h` | **零命中** |
| 需要的 system libs | 由上一行推出 | **无**（`-lrt`/`-lpthread` 由 aml1.pc 自带，vali 自身不额外需要） |

⇒ 配方 `package_info()` **不需要** `system_libs`。

### 1.5 上游源码的 include 形态（决定了 json-c 那一处适配）

| 文件 | 写法 | 说明 |
|---|---|---|
| `client.c` / `conn.c` / `registry.c` / `service.c` | `#include <json_object.h>`、`<json_tokener.h>` | **顶层兼容头** |
| `service.c` | `#include <aml.h>` | 由 aml1.pc 的 `-I${includedir}/aml1` 提供 |
| `test/certification.c` | `<json_object.h>` + `<json-c/json.h>` | 两种写法混用 |
| `test/basic.c` | `#include <vali.h>` + `"test-gen.h"` | 只依赖公共头 |

**顶层兼容头在 json-c 官方产物里不存在**（见 §3.2），这是唯一迫使配方补 `-I` 的原因。

---

## 2. 适配决策

| 决策 | 取值 | 理由 |
|---|---|---|
| 补丁数 | **0（零补丁）** | 两个真正的障碍都在配方层解决：`extra_cflags` 补 json-c 头目录、`b_ndebug=false` 关 NDEBUG。上游源码一行不改 |
| `shared` | `False`（默认静态） | 遵循仓库 R26：系统名库默认静态；仓库存量以静态库为主 |
| `fPIC` | `True`（非 Windows） | 静态库也保持位置无关 |
| `package_type` | `library` | 上游同时装库与 `bin/vali`，但消费语义是"链接库 + 可用生成器"。按 library 处理 ⇒ 不索要 `commands.json`（L0k），`bin/` 仍随包分发 |
| meson | `tool_requires("meson/1.11.0")` | 真机**没有**全局 meson（见 §3.1；`cairo/1.18.4.2` 的注释是同一实测结论） |
| meson 包装脚本权限 | `generate()` 里 `_fix_meson_launcher()` 补 others r/x | 否则 `conan create` 直接 `Error 126`（见 §3.5），这是真机首轮唯一的失败点 |
| `default_library` | `static`（随 `shared` 选项） | 显式声明，语义明确；与官方 meson 模板一致 |
| `wrap_mode` | `nodownload` | 上游 `subprojects/aml.wrap` 是 `[wrap-git] revision = HEAD`（见 §7 第 2 条），必须封死 subproject 回退 |
| `b_ndebug` | **`false`** | §1.3；这是本包最关键的一行 |
| 依赖声明 | `self.requires("json-c/0.18")` / `self.requires("aml/1.0.0")`，**裸 ref** | 制品仓的包无 `@user/channel`；带 `@ohpcd/stable` 会在依赖解析阶段直接报 `Unable to find`（同仓先例 `archives/r/ruy`、`archives/c/cairo/1.18.4`） |
| 依赖提供方式 | `PkgConfigDeps` + `MesonToolchain.pkg_config_path` | `MesonToolchain` 把 `pkg_config_path` 固定指向 conan 的 generators 目录，上游原样的 `dependency('json-c')` / `dependency('aml','aml1')` 直接命中 conan 生成的 `.pc`，**上游 meson.build 一行不改** |
| `bin/pkgconfig/vali.pc` | `rmdir()` 删除 | 见 §1.1 第 4 条 + §7 第 3 条 |

---

## 3. 构建工具与依赖的供给（三处都需要在配方层补）

### 3.1 meson 不在环境里

真机实测（只读探针 `vali-01-deps-probe.sh` / `vali-02-meson-probe.sh`）：

```
$ command -v meson            → 空
$ python3 -m mesonbuild.mesonmain → ModuleNotFoundError: No module named 'mesonbuild'
$ pip3 show meson             → not found
```

CI profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]`：
`PATH=+(path)/storage/Users/currentUser/usr/local/bin` + `/data/service/hnp/bin`
—— 两者都没有 meson。

⇒ 只能 `tool_requires("meson/1.11.0")`。制品仓有 `meson/1.11.0` 与 `meson/1.11.0.1`。
同款先例（均已合入 main）：`archives/a/account-utils/1.4.0`、`archives/c/cairo/1.18.4.2`、
`archives/c/c-stdaux/1.6.0` 等。

> ⚠️ 这个 `tool_requires` 本身还会带来第二层坑（真机首轮 `conan create` 就死在这里），
> 见 §3.5。

对照：仓库里另有 6 份 meson 配方**完全不用** `tool_requires`，直接吃环境里的 meson
（`archives/c/cairo/1.18.4`、`archives/p/pixman/0.46.4`、`archives/g/gtk4/4.22.4`、
`archives/g/gtksourceview5/5.22.0`、`archives/l/libshumate/1.7.0`、`archives/a/aml/1.0.0`）。
而 `archives/c/cairo/1.18.4.2` 的注释把话说死了：*"True machine has no worker-global
meson on PATH (preflight: `/bin/sh: meson: inaccessible or not found`)"* ——
即"真机上没有全局 meson"是**实测结论**，所以本包必须走 `tool_requires`。

### 3.2 `<json_object.h>` 找不到 —— 本包第一个真障碍

`json-c` 0.18 官方 `CMakeLists.txt`（已核对源码）：

```cmake
install(FILES ${JSON_C_PUBLIC_HEADERS} DESTINATION ${CMAKE_INSTALL_FULL_INCLUDEDIR}/json-c)
```

**只装 `include/json-c/`**。发行版里能写 `#include <json_object.h>` 是因为
Debian/Alpine 的 `json-c-dev` 打包时在 `include/` 下补了 16 个兼容**符号链接**。

真机制品仓实测（`conan download json-c/0.18 -r=ohpcd` 后列目录）：
`include/` 下**只有 `json-c/` 一个目录**（16 个头），**没有任何顶层 `json_object.h`**。

★ 更关键的一点（**已实测，不是推断**）：制品仓的 `json-c/0.18` recipe 的
`package_info()` 只有这三行 ——

```python
self.cpp_info.libs = ["json-c"]
self.cpp_info.set_property("cmake_file_name", "json-c")
self.cpp_info.set_property("pkg_config_name", "json-c")
```

**没有任何 `includedirs` 声明**，而实测 CMakeDeps 落地的
`json-c-release-armv8-data.cmake` 里

```cmake
set(json-c_INCLUDE_DIRS_RELEASE )          # ← 空的，连默认的 include 都没有
```

⇒ 任何消费者（包括本包的 meson 构建、以及 test_package 的 CMake 构建）
**拿不到 `-I`**，`#include <json_object.h>` / `<json-c/json.h>` 必然 fatal error。
（**包内自带**的那份 `lib/pkgconfig/json-c.pc` 里有 `-I${includedir}/json-c`，
但它的 `prefix` 还指向构建机路径，且 `MesonToolchain` 的 `pkg_config_path` 固定为
generators 目录 ⇒ 它根本不会被用到。）

⇒ 两处各自补偿、上游源码零改动：

| 位置 | 手法 |
|---|---|
| 主配方（meson） | `tc.extra_cflags = ["-I<json-c 包目录>/include/json-c"]` |
| test_package（CMake） | `tc.cache_variables["JSON_C_INCLUDE_DIR"] = <同路径>`，CMakeLists 里 `target_include_directories(...)` |

### 3.3 `ar` / `ranlib` 需要显式注入

conan 的 `MesonToolchain` 只从 buildenv 的 `AR`/`RANLIB` 取值来填 `[binaries]`
（`conan/tools/meson/toolchain.py`：`self.ar = build_env.get("AR")`），而 CI profile 的
`tools.build:compiler_executables` **只给了 `c` / `cpp`** ⇒ 它写不出 ar/ranlib，
meson 便按**裸名**探测。OHOS 的 clang 工具链在 `/data/service/hnp/bin`，
那里的归档器叫 `llvm-ar` / `llvm-ranlib`，裸名 `ar`/`ranlib` 不在 PATH 上
⇒ configure 阶段就会失败。

解法（用官方 API，而不是事后改写 ini 文件）：

```python
for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
    os.environ.pop(var, None)          # ① 见下
...
for meson_name, candidates in (("ar", ("llvm-ar", "ar")),
                               ("ranlib", ("llvm-ranlib", "ranlib"))):
    ...                                # ② 先从 c 编译器同目录取，退化到 shutil.which
    tc.binaries[meson_name] = found
tc.generate()                          # ③ tc.binaries 会并入 native file 的 [binaries]，且自动过滤 None
```

① 为什么先清环境变量：CI 侧的 `ci/conan/build_and_test.sh` 有一张
`conf_map` 表（`tools.gnu:gcc:ar → env AR=llvm-ar`、`ranlib → llvm-ranlib`、
`nm → llvm-nm`），说明**构建环境里 `AR` 之类的变量是被 export 的**，值就是
`llvm-ar` 这种**不在普通 PATH 上**的名字。若让它原样落进 native file，meson 会报
`ERROR: Program 'llvm-ar' not found`。
同款先例：`archives/g/gtksourceview5/5.22.0`（原注释：
*"CI/worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names not on PATH;
pin the real tools by ABSOLUTE PATH"*）。

② 顺带说明为什么不沿用 `archives/a/aml/1.0.0` 的"事后改写
`conan_meson_native.ini`"做法：`tc.binaries` 是 conan 的**官方入口**
（`_get_binaries()` 里最后 `ret.update(self.binaries)`），语义等价、少一次文本手术。
两种做法的最终产物一致。

先例（均为等价做法，已合入 main）：`archives/a/aml/1.0.0`、
`archives/c/cairo/1.18.4`、`archives/p/pixman/0.46.4`、`archives/g/gtksourceview5/5.22.0`。

### 3.4 meson 探测 ninja 的已知风险（本包**未**加防御，原因如下）

仓库里有一条草稿知识条目 **DRAFT-E5xx（ohos-meson-detect-ninja-env-pin）**：
`meson setup` 会先跑 `ninja --version` 探测后端；`/data/service/hnp/bin/ninja` 是 ELF，
需要 `libc++_shared.so`，而 conan 重写构建环境后在 OHOS musl loader 下可能找不到它
⇒ `ninja` 以 127 退出 ⇒ meson 报 `Could not detect Ninja v1.8.2 or newer`。
已合入的两份配方（`gtksourceview5/5.22.0`、`libshumate/1.7.0`）用
"向 `conanbuildenv-*.sh` 追加 `NINJA=` 与 `LD_LIBRARY_PATH=/system/lib64`"来兜底。

**本包为什么没抄这段**：同环境、同构建系统、同样需要 ninja 探测的
`archives/a/aml/1.0.0` **没有**这段补丁也成功合入了，说明这台机器上
`ninja --version` 在 conanbuild 环境里是正常的（草稿自己也写了
"CI worker 上 PATH 顺序恰好正确时此问题不显现"）。按"不引入未经证实的作用机制"的原则，
这里不加；**症状与现成修法记录在此**，一旦真机出现 `Could not detect Ninja`
就按上面 `_patch_conanbuildenv()` 的形态补（追加 `export NINJA="/data/service/hnp/bin/ninja"`
和 `LD_LIBRARY_PATH` 前置 SDK llvm/lib）。

真机自检里已加一条只读探针（`ninja --version` + 归档器定位），见 §10.1。

### 3.5 ★ 真机 `conan create` 的 `Error 126`：OHOS 上 conan 无法 `execve` 沙箱内的 `#!` 脚本

**现象**（真机首轮，`~/vali-create-1.log`）：

```
vali/0.1.1: apply_conandata_patches(): No patches defined in conandata
vali/0.1.1: Meson configure cmd: meson setup --native-file "…/conan_meson_native.ini" \
            "…/build-release" "…/b" --prefix=/
/system/bin/sh: /storage/Users/currentUser/.conan2/p/mesonc731ddfc5b264/p/bin/meson: Permission denied
ERROR: vali/0.1.1: Error in build() method, line 200
    meson.configure()
    ConanException: Error 126 while executing
```

依赖图解析、源码下载、`generate()`、零补丁 info（`No patches defined in conandata`）
全部正常，`meson setup` 的命令行也拼得完全正确 —— **只死在"执行 meson"这一步**。

出问题的文件是 tool_requires `meson/1.11.0` 里的 `bin/meson`（121 字节，
**不是 ELF，是 `/bin/sh` 包装脚本**）：

```sh
#!/bin/sh
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
exec python3 "$here/../lib/python3.12/site-packages/meson.py" "$@"
```

**排查矩阵**（三支只读探针 `vali-15` / `vali-16` / `vali-17`，全部在真机、
同一个 `g watch` 上下文里跑，避免"手工跑 vs 自动跑"的干扰）：

| # | 调用方式 | 结果 |
|---|---|---|
| 1 | `"$M" --version`（脚本自己所在的 shell 里直接跑） | ✅ `1.11.0` rc=0 |
| 2 | `/bin/sh -c "'$M' --version"` | ✅ rc=0 |
| 3 | `/system/bin/sh "$M" --version`（脚本作 argv，不走 execve） | ✅ rc=0 |
| 4 | Python `subprocess.run([M, "--version"])` ← **conan `run()` 的做法** | ❌ `PermissionError [Errno 13]` |
| 5 | Python `subprocess.run("'$M' …", shell=True)` | ❌ rc=126 `Permission denied` |
| 6 | Python 手动 `fork()` + `os.execv(M)` | ❌ exit 127 |
| 7 | 对照：`/data/service/hnp/bin/ninja --version`（系统/hnp 文件） | ✅ rc=0 |
| 8 | 对照：`~/usr/local/bin/python3 --version`（**沙箱内的 ELF**） | ✅ rc=0 |
| 9 | 自己新写一个 `#!/bin/sh` 脚本到同一目录 | ❌ 同样 EACCES |
| 10 | 换 shebang：`#!/system/bin/sh`、`#!/data/service/hnp/bin/bash` | ❌ 同样 EACCES（`bad interpreter: Permission denied`） |
| 11 | **去掉 shebang**（首行直接是命令） | ✅ **`shell=True` → rc=0** |
| 12 | `os.chmod(p, 0o755)` | ⚠️ `rc=0` 但 mode 纹丝不动（E046 静默失效） |

⇒ **根因不是"权限位不够"**（这是最初的误判，写在这里以免后人重走）：

- 文件属主 `20001006:file_manager`、mode `0770`；构建进程 euid=`20020085`，
  但 **gid `1006` 就在 `file_manager` 组里**（`os.access(X_OK)` 也返回 `True`）；
- **同一个进程里 shell 能跑、Python 跑不了** ⇒ 差别在**调用方式**，不在权限；
- 三种 shebang 全失败且报 `bad interpreter: Permission denied`
  ⇒ 卡在**内核处理 shebang 这一步**；
- 沙箱内的 **ELF** 完全正常 ⇒ 只有 `#!` 脚本受害。

**可用的形态**：无 shebang 的文件 `execve` 返回 `ENOEXEC`，POSIX shell 会
**回退成"按脚本解释执行"**（实测第 11 行 rc=0）；而 conan 的 `run()` 恰恰是
`/bin/sh -c`。⇒ 去掉 meson 包装脚本的 shebang 即可打通。

**解法**（配方层，仍然零补丁）：`generate()` 里调 `_fix_meson_launcher()`：
读原文件 → 备份为 `meson.conan-orig` → 去首行 shebang → 写临时文件后用
`os.replace()` 换上去（只需目录写权限，不要求属主）→ 立刻以
`subprocess(..., shell=True)` 实跑一次 `meson --version`，把 `rc` 打进日志。
幂等：首行已不是 `#!` 时一个字节都不动（复跑场景会打
`meson launcher already shebang-free`）。

⚠️ 两个别踩的坑：

1. **别想用 `chmod` 修**：实测 `chmod` 返回 0 而 mode 不变（知识库 E046 的静默失效），
   `os.chmod` 同理 ⇒ "把 others 的 x 位补上"这条路在这个文件系统上根本走不通。
2. **别因为"手工跑能过"就排除这类问题**：同一个文件在 shell 里 `rc=0`、
   在 conan 的子进程里 `EACCES`。判据必须以 **Python `subprocess`** 为准。

这条已作为路径B 候选记入 §9 第 6 条（它命中所有走 `tool_requires` 的 meson 包）。

---

## 4. 编译告警与 `werror`（实测结论）

上游把严格度拉到了它能承受的极限：

```meson
default_options: ['warning_level=3', 'werror=true', ...]     # → -Wall -Wextra -Wpedantic -Werror
add_project_arguments(cc.get_supported_arguments([
    '-Wundef', '-Wmissing-prototypes', '-Walloca', '-Wconversion', '-Werror=implicit']))
```

上游 CI（`.builds/alpine.yml`）是 `meson setup build/ --fatal-meson-warnings`，
即 meson 自身的警告也算错。**但上游 CI 跑在 Alpine（gcc），与 OHOS 的 clang 15 不同**，
`-Wconversion` / `-Wundef` / `-Wpedantic` 这类"编译器口味相关"的警告最容易出现差异。

仓库知识库里已有两条直接相关的证据，说明**这不是空想的风险**：

- **E063**（`-Werror` 导致警告变错误，`rec_priority: 1`，`rec_approach: add-cflags-disable-werror`）：
  `affected_scope` 写的是*"所有使用 -Werror 的软件在鸿蒙上都可能遇到
  （**最普遍的适配问题之一**）"*。
- **DRAFT-astronomy-2.1.9-clang15-fortify-misleading-indentation-werror**：
  实测案例，`error: 'sscanf' may overflow … [-Werror,-Wfortify-source]` /
  `error: misleading indentation … [-Werror,-Wmisleading-indentation]`，
  根因明确写成*"上游测试代码按 gcc 环境的告警面编写。OHOS 工具链 clang15 的
  … 比 gcc 更严格，且都被 -Werror 升级为错误"*。

**处置原则**（沿用 astronomy 条目的结论）：若真机中断，**按类降级**，
不用笼统的 `-Wno-error`：

```python
tc.project_options["werror"] = "false"          # 方案 A：整包关掉 -Werror（改动最小）
# 或
tc.extra_cflags = [..., "-Wno-error=<具体类别>"]  # 方案 B：只降级实际命中的类别
```

两个方案都是**纯配方层改动，仍然零补丁**。
`werror` 是 meson 的 builtin 选项，conan 的 `[project options]` 段已证明能承载
builtin 选项（本配方就在同一段里设了 builtin 的 `wrap_mode`，且
`archives/a/aml/1.0.0`、`archives/c/cairo/1.18.4` 也用同段设 `default_library`）。

> ⏳ **待真机实测回填**：见下表与 §10.2。

| 场景 | 实测结果 |
|---|---|
| 全量构建（lib + tool + example + test）| ⏳ |
| `warning_level=3` / `-Wconversion` / `-Wundef` 告警数 | ⏳ |
| 是否触发 `-Werror` 中断 | ⏳ |
| 最终处置 | ⏳ |

---

## 5. 消费者用例（test_package）

### 5.1 为什么不用 `assert()`

CMake/meson 的 Release 配置会定义 `NDEBUG`，`assert()` 会被预处理器抹掉 ⇒ 测试退化成
"必然通过"的假测试，而 **CI 的 L1e 破坏性反向验证正是针对假测试设计的**（把产物移走再跑，
假测试照样通过 ⇒ 判 fail）。因此用例自带不受 `NDEBUG` 影响的 `CHECK` / `CHECK_STREQ` 宏，
失败只累加、最后以退出码 1 结束。同款先例：`archives/r/reliable/1.3.5`。

### 5.2 用例做了什么

`test_vali.c` 用 `socketpair(AF_UNIX, SOCK_STREAM, 0, ...)` + `fork()` 起一个**真实的
Varlink 服务端进程**，父进程作为客户端走完整协议：

| 分组 | 验证内容 |
|---|---|
| 1 | `vali_service_create` / `vali_service_set_call_handler` / `vali_service_create_conn` / `vali_client_connect_fd` 全部成功（任一步返回 NULL 则由子进程 `_exit(1)` + 客户端 `CHECK(client != NULL)` 暴露） |
| 2 | **Echo 往返**：`vali_client_call()` 拿到响应 → `echo` 字段值正确、`error` 字段为空（`err.name == NULL`）、服务端视角的 `oneway` 标记为 false |
| 3 | **错误路径**：调用未注册方法，服务端 `close_with_error(call, "org.example.test.UnknownMethod", NULL)` ⇒ 客户端 `vali_client_call()` 返回 false 且 `err.name` 精确等于该错误名 |
| 4 | **`vali_error_finish()` 契约**：释放后清零再释放一次（见 §5.4） |
| 5 | **oneway 与普通调用不错位**：`vali_client_call_oneway()` 后紧跟一个普通 call，验证 oneway 不占回复队列（服务端对 oneway 必须丢弃回复体） |
| 6 | **多回复（more）**：`CountUntil` 用 `vali_service_call_is_more()` / `vali_service_call_reply()` 流式回 `n=0..upto`；客户端用 `vali_client_call_more()` + `vali_client_call_wait()` + `vali_client_call_is_done()` 收齐并逐条校验 `n` 的值 |
| 7 | 收尾 `Stop`，`waitpid` 校验服务端 `WIFEXITED && WEXITSTATUS == 0` |

**25 处静态宏调用点**（`CHECK` 22 + `CHECK_STREQ` 3）。源码级计数（宏定义行已剔除）：

```
$ grep -o 'CHECK('       test_package/test_vali.c | wc -l   → 23   （含 1 处宏定义）
$ grep -n 'CHECK('       test_package/test_vali.c | grep -vc 'define'  → 22  （实际调用）
$ grep -o 'CHECK_STREQ(' test_package/test_vali.c | wc -l   →  4   （含 1 处宏定义）
$ grep -n 'CHECK_STREQ(' test_package/test_vali.c | grep -vc 'define'  →  3  （实际调用）
                                                     合计 22 + 3 = 25
```

这 25 处里有 4 处在互斥分支（`if (...)` 成功分支 / `else` 的 `CHECK(0)`），只走一支；
另有 3 处在 `test_more_replies` 的 `for (i = 0; i <= 3; i++)` 循环体内。
⇒ **运行时实际执行 18 + 3×4 = 30 次**，与真机输出逐字对应：

```
test_vali: 30 checks run, 0 failed
```

`MANIFEST.yml` 里 `test_case_count: 25` / `assertion_count: 25` 是**静态调用点**口径
（必须与 CI 的裸 grep 一致，所以不能写成 30），另用
`runtime_assertion_count: 30` / `test_counting.integration_runtime_assertions: 30`
记录实跑次数；与上游 2 条 `meson test`（`upstream_test_total: 2`）**相加不重叠**。
⚠️ 两个口径都要如实写：PR 正文的"通过率分母"用 **30/30**（与日志逐字对齐），
而静态 25 处用于 CI 的源码计数比对 —— 只写一个都会被另一半质疑。

### 5.3 头文件用规范路径，不用顶层兼容头

消费者用例是"新写的代码"，没有历史包袱，所以直接写 `#include <json-c/json.h>`
（规范路径），而不是复刻上游的 `<json_object.h>`。
好处：消费者用例本身**不依赖**配方那条 `extra_cflags` —— 万一将来 json-c 包形态变化，
`extra_cflags` 若失效只影响上游源码，不会连累测试用例的判据。

### 5.4 写用例时从上游源码里挖出的两个 API 陷阱（都已规避，真机首轮即暴露过一次）

> 这两个坑是**读 `client.c` / `vali.h` 源码**时发现的，本地首版用例两条都踩了。
> 写"库的使用者"用例之前先读实现，比在真机上反复试错便宜得多。

1. **★ `vali_error_finish()` 不是幂等的 —— 重复调用 = double free**
   ```c
   void vali_error_finish(struct vali_error *err) {   // client.c:167
       free(err->name);
       json_object_put(err->parameters);
   }
   ```
   它**不把字段置零**。`vali.h` 的注释写的是
   *"This function can be called safely on a zero error."* —— 意思是
   **对零值结构体调用是安全的**，**不是**"可以重复调用"。
   首版用例据此写成"连续 `finish` 两次，验证幂等"，实际是 double free。
   正确用法：**用完后若还要复用该结构体，必须自己 `err = (struct vali_error){0};`**。
   现在的用例两条都覆盖：先 `finish` 一次，再清零后 `finish` 一次。

2. **`vali_client_call_has_more()` 在头文件里根本不存在**
   `vali.h` 中 `vali_client_call_more()` 的文档注释写着
   *"clients should call vali_client_call_wait() while vali_client_call_has_more()
   returns true"*，但全头文件**没有这个声明**（只有 `vali_client_call_is_done` /
   `vali_client_call_wait` / `vali_client_call_destroy`）。
   照抄文档注释写 `while (vali_client_call_has_more(call))` 会直接编译失败。
   正确写法来自 `client.c` 的实现：
   ```c
   bool vali_client_call_is_done(struct vali_client_call *call) {
       return call->client->pending_call != call;   // 收到 continues=false 后 pending_call 被清空
   }
   ```
   ⇒ 循环判据用 `while (!vali_client_call_is_done(call))`。
   **上游文档注释陈旧**这一条本身就是一类值得进知识库的问题。

---

## 6. 逐项过门禁

| 门禁 | 处理方式 |
|---|---|
| **L0a/b/c** | `test_package/` 含 `conanfile.py` + `test_vali.c`（`.c` 在允许后缀内） |
| **L0d** | `test()` 内**显式调用 `self.run(binary, env="conanrun")`**。⚠️ 官方 `test_package` 模板只写 `cmake.test()`，不含 `self.run`，照抄会被裸 grep 判为 `stub_test_method` |
| **L0e** | `test_package/MANIFEST.yml` 已提供，声明 2 条上游 `meson test` + 25 处消费者断言调用点（运行时 30 次，见 §5.2） |
| **L0f** | `conandata.yml` 的 `patches:` 段为空（仅注释），不触发"文件名当 key"的格式校验 |
| **L0g** | 无任何 `-r=` / `-r ` 硬编码 remote |
| **L0h** | 无 `self.run()` 依赖裸 shell 变量（`${CC}` 等） |
| **L0i** | 依赖 `json-c/0.18`、`aml/1.0.0` **均已发布**（真机 `conan list` 确认） |
| **L0j** | 制品仓是否已有 `vali/0.1.1` —— 见 §8 第 1 项 |
| **L0k** | `package_type = "library"`，无需 `commands.json` |
| **L0m** | `archives/v/vali/0.1.1/`：首字母 `v` = `vali` 首字母；包名/版本均为 conan slug 且与目录一致 |
| **L0n** | 分支 `feat/vali-0.1.1`，剥前缀后 `vali-0.1.1` 精确等于 `包名-版本`，无后缀 ✅ |
| **L0o** | 源码用 `get(self, **self.conan_data["sources"])`，无外部 `curl`/`wget` |
| **L0p** | `settings = "os", "compiler", "build_type", "arch"` 四项齐全 |
| **L0q** | 无 `patches/` 目录（零补丁） |
| **L1a–L1e** | `conan create` 会执行 test_package；`test()` 内无 echo/print/true；用例真实链接包内静态库并调用 `vali_*` API ⇒ L1e 把产物移走后必然失败 |
| **L1c** | `build()` 里显式输出 `Meson upstream test: meson test -v -C <build>` 并调用 `meson.test()` ⇒ 日志含 `meson test` 痕迹 |
| **JC1/JC2/JC3/JC4** | 不提交状态文件、二进制产物、源码 tarball、构建目录 |
| **JC5** | `archives/v/vali/` 下无未登记隐藏文件 |
| **JC6** | 本 PR 只涉及 `archives/v/vali/` 一个软件 |
| **KC** | 未改动 `knowledge/` |

---

## 7. 踩坑记录

1. **release 资产 ≠ `/-/archive` 动态归档，但本包两者内容相同**
   `https://gitlab.freedesktop.org/emersion/vali/-/releases/v0.1.1/downloads/vali-0.1.1.tar.gz`
   （30493 B）与 `.../-/archive/v0.1.1/vali-v0.1.1.tar.gz`（30275 B）**逐文件 sha256 完全一致**
   （30 个文件全同，无增无减无改），差别只在 gzip 头。选前者：它是维护者**冻结上传**
   的成品，可复现性更好；后者由 GitLab 按 tag 即时打包。
   `conandata.yml` 里两个 URL 都实测过，最终只留 release 资产那一条。

2. **`subprojects/aml.wrap` 是不可复现隐患**
   ```
   [wrap-git]
   url = https://github.com/any1/aml.git
   revision = HEAD          ← 浮动引用
   ```
   一旦 meson 走 subproject 回退，就会去 clone 上游 **HEAD**（不可复现，且 CI 无网络）。
   上游 `project()` 的 `default_options` 里已经写了 `wrap_mode=nodownload`，
   但配方里**再显式声明一遍** `tc.project_options["wrap_mode"] = "nodownload"`，
   保证永远只用 conan 提供的 `aml1.pc`。

3. **`vali.pc` 的 `prefix` 是构建期根目录**
   conan 用 `meson setup --prefix=/` + `meson install --destdir <pkg>` 的方式安装，
   于是 `.pc` 里落的是 `/`（不是包目录）。加上 §1.1 第 4 条（漏 aml），
   这份 `.pc` 对下游只有误导作用 —— conan 侧本来就会由 `CMakeDeps`/`PkgConfigDeps`
   另生成完整描述。⇒ `rmdir(self, package_folder/lib/pkgconfig)`。
   同款先例：`archives/r/reliable/1.3.5`。

4. **官方 meson 配方模板是错的，不能照抄**
   `单库适配工作台/仓库模板/conanfile-meson.py.tmpl` 里调用了 `meson_layout(self)`，
   但 conan 2.29.1 的 `conan/tools/meson/__init__.py` **只导出 `Meson` /
   `MesonToolchain`**，**没有 `meson_layout`**（已读源码确认）⇒ 照抄必 `NameError`。
   正确写法是 `from conan.tools.layout import basic_layout`，
   与 `archives/a/aml/1.0.0`、`archives/c/cairo/1.18.4`、`archives/a/account-utils/1.4.0` 一致。

5. **`Meson.test()` 没有 `stdout=` 参数**
   `.build()` / `.install()` 支持输出重定向，但 `Meson.test()` 的签名就是
   `def test(self)`，**没有** `stdout=`/`stderr=`。本包是 meson（非 CMake），
   也就不存在 `archives/r/reliable` 那条"conan `run()` 把输出流继承给子进程导致
   clang 静默失败"的坑 —— 那条是 CMake 配方的经验，**不要照搬**。

6. **`b_ndebug` 是"字符串形式的布尔"**
   conan 的 native file 模板里，`b_ndebug` 那一行是「等号 + 模板变量」且**不带引号**
   （同段的 `c_args = [...] + preprocessor_definitions` 也是裸写），
   由 `to_meson_value()` 把 Python 值转成 `'true'` / `'false'` 字符串再落地。
   所以覆写时写 `tc.b_ndebug = "false"`（字符串）最贴合上游写法；
   写 Python `False` 经 `to_meson_value` 后同样是 `false`，效果等价。

7. **上游 `basic` 测试的 NDEBUG 自杀逻辑（本包最容易踩的一次失败）**
   见 §1.3。如果忘了 `b_ndebug=false`，`conan create` 会走到 `build()` 里
   `meson test` 才失败，且报错信息是上游自己打印的
   `NDEBUG must be disabled for tests` —— 看到这行**不要怀疑环境**，
   直接改 `b_ndebug`。

8. **Windows 侧 `curl` 与 Git Bash 的 `/tmp` 不是同一目录**
   给 Python 脚本传路径一律用 `C:/...` 形式。

9. **远程脚本必须纯 ASCII**
   下发到鸿蒙 PC 的 `.sh` 必须先自检 `LC_ALL=C grep -n '[^ -~]' x.sh` 输出为空；
   中文 commit message 走 base64 + `git commit -F`。

10. **平台接口没有单任务端点**
    `/api/contrib/tasks/<id>` 返回 `{"detail":"Method Not Allowed"}`，
    要查某个任务的状态只能整池分页扫描（`status=assigned&limit=200&offset=N`）后本地匹配 id。
    本次即用此法确认 `11599 vali 0.1.1` 的状态为 `assigned`（不是 `claimed`）。

11. **`ci/conan/build_and_test.sh` 里有一张 `conf_map`，会改写配方里的 conf 调用**
    ```python
    conf_map = {
        'tools.gnu:gcc:ar':     {'val': 'llvm-ar',     'env': 'AR'},
        'tools.gnu:gcc:ranlib': {'val': 'llvm-ranlib', 'env': 'RANLIB'},
        'tools.gnu:gcc:nm':     {'val': 'llvm-nm',     'env': 'NM'},
    }
    ```
    CI 会把 `self.conf.get("tools.gnu:gcc:ar", default="llvm-ar")` 之类的调用
    **改写成 `os.environ.get("AR", "llvm-ar")`** 后再构建/上传（"Conf compat patch"，
    因为 OHOS 的 conan 2.29.1 没注册这些 conf，直接 `get()` 会抛异常）。
    两个推论：
    - **构建环境里 `AR`/`RANLIB`/`NM` 确实被 export 成 `llvm-*` 名字**
      （这正是 §3.3 要先把它们清掉的原因）；
    - 配方**不要**去读 `tools.gnu:gcc:*` 这类 conf —— 会被 CI 就地改写，
      导致"本地能跑、CI 上配方已变样"。本包只读 `tools.build:compiler_executables`，
      不在 `conf_map` 覆盖范围内。
    （L0j 的版本占用比对还会做"改写逆向归一化"，说明这套改写是既定机制。）

12. **平台的 `lang` 字段与 `difficulty` 字段不可信**
    `vali` 在池里的 `lang` 标的是 `c/cpp`（勉强对），但同池 `libpathrs`/`libkrun`
    是 Rust、`snakeyaml` 是 Java 也被标成 `c/cpp`；`difficulty` 恒为 `medium`。
    分配目标库时只信源码，别信这两个字段。

13. **★ 配方逻辑全对，却死在"执行 meson"上（Error 126 = conan 无法 execve `#!` 脚本）**
    真机首轮 `conan create` 的失败点不在配方：依赖图解析、源码下载、`generate()`
    生成的 native file、`apply_conandata_patches()` 的零补丁 info 全部正常，
    `meson setup` 的命令行拼得完全正确，然后：
    ```
    /system/bin/sh: …/p/mesonc731ddfc5b264/p/bin/meson: Permission denied
    ConanException: Error 126 while executing
    ```
    **这是"末位一环"的坑：不要往源码/meson.build/依赖上找。**
    ⚠️ 头号误判是**去查权限位**：文件确实是 `0770`、属主也确实不是构建用户，
    但 `os.access(X_OK)` 是 True、`file_manager` 组也在进程的 groups 里 ——
    **同一个进程里 shell 能跑、Python `subprocess` 跑不了**，这才是判据。
    真正的分界线是：**文件有没有 shebang**。带 `#!` 的脚本（换哪个解释器都一样）
    在 Python `execve` 下必然 EACCES；无 shebang 的脚本会走 shell 的 ENOEXEC
    回退，正常执行。完整矩阵与修法见 §3.5。

14. **★ 本地 CI 模拟必须用 `zsh` 跑，`bash` 必然语法报错**
    `ci/conan/build_and_test.sh` 第 1 行是 `#!/usr/bin/zsh`，正文里用了 **zsh 专有的
    glob 限定符**：
    ```zsh
    G0_DRAFT_COUNT=$(ls -1 "${GRAPH_DIR_G0}/draft"/*.kv(N) 2>/dev/null | wc -l)
    ```
    `(N)` 是 zsh 的 `nullglob` 限定符。换成 bash 会得到
    ```
    ci/conan/build_and_test.sh: line 107: syntax error near unexpected token `(' while looking for matching `)'
    ```
    而且**只在跑到第 107 行时才炸**（bash 逐条读取执行，前面的 6 行 echo 都已打印），
    症状极像"脚本内容坏了"，实际是解释器选错。
    真机两个 shell 都在：`/usr/bin/zsh`(5.9, musl) 与 `/data/service/hnp/bin/bash`(5.3.0)。
    ⇒ 跑 W3 时一律 `zsh ci/conan/build_and_test.sh`；这也是仓库自带脚本
    `真机辅助脚本/final-verify.sh` 里 `SH=zsh`（无 zsh 才回退 bash）的原因。
    顺手结论：**该脚本不能当 bash 脚本读**，任何 shellcheck/重写都要按 zsh 语义来。

15. **★ 跑完本地 CI 模拟，档案目录会被塞进 2 个文件 + 1 棵构建树**
    实测：`zsh ci/conan/build_and_test.sh` 成功退出后，`archives/v/vali/0.1.1/` 下多出
    ```
    archives/v/vali/0.1.1/ci-metadata.json            ← CI 生成的元数据
    archives/v/vali/0.1.1/conanfile.py.confbak        ← "Conf compat patch" 改写的备份
    archives/v/vali/0.1.1/test_package/build/…        ← 消费者用例的 CMake 构建树
    archives/v/vali/0.1.1/test_package/CMakeUserPresets.json
    ```
    **这三个（类）都会进 `git diff`**（`git add -N archives/v/vali` 之后），
    实测 pr.diff 因此从 10 个文件涨到 11 个。提交前必须按**白名单**清：
    ```sh
    # 期望恰好 10 个文件
    find archives/v/vali -type f | wc -l
    ```
    清完再重新生成 pr.diff，`grep -c '^diff --git ' pr.diff` 必须是 **10**。
    ⚠️ 两件必须顺手确认的事：
    - `conanfile.py.confbak` 的存在说明 CI **就地改写过 `conanfile.py`**（把
      `tools.gnu:gcc:*` 的 `conf.get()` 改写成 `os.environ.get()`，见 §7.11）。
      改写后它会还原，但要**用 sha256 复核还原是否干净**，别把 CI 改过的配方提交上去。
    - CI 还会在**仓库根**建 `.ci_logs/`（日志目录）。它不在 G0e 白名单里，但 G0 早于
      这一步执行、且 CI 自己会忽略它；只要**别 `git add` 仓库根**就无影响。

16. **CI 日志里的 `[fail] [Errno 2] No such file or directory: 'curl'` 是无害噪音**
    `build_and_test.sh` 在 conan 之前有一个**可选的**源码预下载步骤，用 `curl` 抓
    `conandata.yml` 里出现的 URL。OHOS 设备上 `curl` 不在 Python 子进程继承到的 PATH 上
    ⇒ 每个 URL 打印 3 次 `[fail] … 'curl'`，然后自己降级：
    ```
    [WARN] Failed to pre-download vali-0.1.1.tar.gz, will rely on conan's download
    [done] No files pre-downloaded
    ```
    **它不是门禁**（不在 L0–L5 任一项里），也没有影响本包 —— 源码最终由 conan 自己
    从 `conandata.yml` 的 URL 下载并用 sha256 校验通过。看到这批 `[fail]` 不要去找配方问题。
    副产品：URL 提取器连**注释里的示例 URL** 也会一并尝试（本包实测"found 2 source URL(s)"，
    其中一条来自 conandata 注释里的模板 URL）。

---

## 8. 本地验证记录（在鸿蒙 PC 上实跑后回填）

> 本表是**证据记录**，不是待办清单。提 PR 前必须把下面每一行的结果换成实跑输出
> （原始日志节选见 §10）。PR 正文中不得出现任何"未验证"性质的表述。

| # | 验证项 | 命令 | 实测结果 |
|---|---|---|---|
| 1 | 制品仓是否已存在 `vali/0.1.1`（L0j） | `conan list "vali/0.1.1" -r=ohpcd` | ✅ `ERROR: Recipe 'vali/0.1.1' not found` ⇒ 版本号未被占用 |
| 2 | 依赖是否已发布（L0i） | `conan list "json-c/0.18:*" -r=ohpcd`、`conan list "aml/1.0.0:*" -r=ohpcd` | ✅ json-c/0.18 rrev `04bc64d2a27c2c6150492abc7d054cec`（2026-07-14）、pkg `01d92cf349a0dd98ff915f4bd99a04430171517f`；aml/1.0.0 rrev `a5e758fd4b11f8f58a93c7473f0df0a0`（2026-09-26）、pkg `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`；两者均 armv8/Release |
| 3 | `conan create` 是否零补丁通过 | CI 门禁内的 `conan create`（**绝对路径** profile，见 §3 与 §7.14） | ✅ 退出码 **0**；`export_conandata_patches(): No patches defined in conandata` 与 `apply_conandata_patches(): No patches defined in conandata` 各出现一次 ⇒ 零补丁既被声明也被执行 |
| 4 | 上游 2 条 `meson test` 通过率 | `conan create` 日志中的 `meson test` 汇总 | ✅ **2/2 = 100%**：`1/2 vali:basic OK 0.04s`、`2/2 vali:certification OK 0.04s`；`Ok: 2 / Fail: 0` |
| 5 | 消费者用例断言通过率 | `./test_vali` 输出 | ✅ **30/30 = 100%**：`test_vali: 30 checks run, 0 failed` + `ALL CHECKS PASSED`（静态宏调用点 25 处，其中 3 处在 4 轮循环内 ⇒ 运行时 30 次；口径见 `test_package/MANIFEST.yml`） |
| 6 | `extra_cflags` 补 json-c 头目录是否生效 | 构建日志里上游源码不再报 `<json_object.h>` file not found | ✅ 上游 5 个 `.c` 全部编译通过、无 `file not found`；消费者侧另有独立口径（用规范路径 `<json-c/json.h>`，由 `JSON_C_INCLUDE_DIR` 注入，见 §5.3） |
| 7 | 改动范围是否只有 `archives/v/vali/` | `git diff --name-only origin/main...HEAD \| cut -d/ -f1-3 \| sort -u` | ✅ 只有 `archives/v/vali`（提交前复核，同时确认 `archives/l/libxext` 的 CRLF 噪音**未**被 `git add`） |
| 8 | 本地 CI 模拟整体结果（G0/KC/JC/L0–L5） | `CI_PACKAGES=… CI_BRANCH=… JUNK_PR_DIFF=… zsh ci/conan/build_and_test.sh` | ✅ `CI_RC=0`；`G0_RESULT=pass`（含 `[ok] G0e: Root directory whitelist passed`）、`KC_RESULT=pass`、`JC_RESULT=pass`、`L0_RESULT=pass: all checks passed`、`L1_RESULT=pass: upstream tests + test_package executed`、`L2_RESULT=skip`、`L4_RESULT=pass: no patches`、`L5_RESULT=pass: bin/ has content`；`Total 1 / Success 1 / Failed 0 / Pass rate: 100.0% (1/1)` |
| 9 | meson 包装脚本 shebang 修复是否真的生效（§3.5） | `conan create` 日志中的两行 | ✅ `meson launcher already shebang-free: …/p/bin/meson`（幂等分支，首轮已改写过）+ `meson launcher usable via /bin/sh (shebang-free): … -> 1.11.0`（以 `/bin/sh -c` 实跑自检，拿到版本号） |
| 10 | `bin/vali` 是否有 `--version`/`--help`（L2 为何 skip） | `<pkg>/bin/vali`、`--version`、`--help` 三种调用 | ✅ 三者均 `rc=1` 并打印 `usage: vali generate [options...] <definition> <header> <code>` ⇒ 上游 `vali` 是**代码生成器**，不实现 version/help ⇒ L2 非阻塞 skip，不是产物坏了 |
| 11 | 是否残留上游的 `lib/pkgconfig/vali.pc` | `find <pkg> -type f` | ✅ 包内只有 `bin/vali`、`include/vali.h`、`lib/libvali.a`、`licenses/LICENSE`（+ conan 自身的 `conaninfo.txt`/`conanmanifest.txt`）⇒ `rmdir(lib/pkgconfig)` 生效 |
| 12 | 产物确实是被测 API 的实现而非源码内联 | `file` / `readelf -d` / `nm` | ✅ `lib/libvali.a` 定义 **38 个** `vali_*` 文本符号（含 `vali_client_call*`、`vali_service_*`、`vali_registry_*`、`vali_error_finish`）；`bin/vali` 为 `ELF 64-bit LSB arm64 (musl)`，`NEEDED` 仅 `libc.so`；`include/vali.h` 367 行、只 `#include <stdbool.h>`（自包含） |

> 行 1–2 是**只读**核对（`conan list`），3–12 是实跑。
> 首轮的失败记录（§3.5 的 Error 126）**不进 PR 正文**，只在 §10.2 留档：
> PR 正文里写的必须是修好之后的绿灯结果。
> 行 5 的 30 来自 CI 自己那轮 `conan create` 的日志（`test package: RUN: ./test_vali`），
> 与设备上档案的逐字节哈希一致（§10.6），因此这份数字就是将被提交的那份字节跑出来的。

---

## 9. 可沉淀为知识库素材的点（路径B 候选，本 PR 不提交）

按路径B 场景一的要求，得是能解决"一类问题"（而非 case-by-case）的点。本包有 5 个候选：

1. **★ meson 项目的 pkg-config `requires` 漏声明私有依赖 ⇒ 静态链接下游必缺符号**
   判据：`pkgconfig.generate()` 的 `requires:` 只列了公共头暴露的依赖，而 `.c` 里用了
   另一个库的符号。`vali.h` 自包含（不暴露 aml），但 `service.c` 有 `aml_*` 调用 ⇒
   `vali.pc` 的 `Requires` 只有 `json-c`。静态链接的下游按 `vali.pc` 取参数时，
   链接器报的全是一串 `aml_*` 未定义符号，**而报错的库名和 aml 毫无字面关系**，
   排查方向极易跑偏。跨库通用（GLib 系、systemd 系、wayland 系都是重灾区），
   可给出一条固定判据：`grep -o 'dependency('\''\?[a-z0-9_-]*'\''\? *,' meson.build`
   与 `pkgconfig.generate(..., requires: [...])` 做差集。

2. **构建期自举（`custom_target` 调用本工程刚编译出的可执行文件）在交叉编译下必挂**
   vali 有 4 处（§1.2）。原生构建无感，交叉编译时必须给 meson 一个 host 版可执行文件
   （`--native-file` 里指定 `[binaries]` 的对应项，或用 `meson.override_find_program`）。
   判据：`custom_target` 的 `command:` 第一项是同一工程里 `executable()` 的产物名。
   这是一类**所有**"代码生成器 + 库同工程"的项目（protobuf / wayland-scanner /
   gdbus-codegen / varlink / flatbuffers）共有的问题。

3. **`[wrap-git] revision = HEAD` 是供应链/可复现性隐患**
   CI 无网络时会直接失败；有网络时会 clone 到"那个时刻的 HEAD"。判据：
   `find . -name '*.wrap'` 后看 `revision` 是否为 `HEAD`/分支名。
   这类项目必须用包管理器提供依赖并封死 `wrap_mode=nodownload`。

4. **`xxx_finish()` / `xxx_release()` 不置零 ⇒ 重复调用是 double free**
   判据：`grep -A3 'void .*_finish(struct\|void .*_free(struct\|void .*_destroy(struct'`
   看函数体里有没有 `= (struct ...){0}` / `memset(..., 0, ...)` / `= NULL`。
   没有就是"只对零值安全、不对重复调用安全"。文档里常见的
   *"can be called safely on a zero X"* 极易被误读成"幂等"。
   跨库通用（这是 C 句柄式 API 的普遍形态），可作为消费者用例的设计准则：
   **每个 `_finish`/`_destroy` 调用点旁边都要能指出"之后谁负责清零"。**

5. **上游文档注释可能引用不存在的函数**
   `vali.h` 里 `vali_client_call_more()` 的注释提到 `vali_client_call_has_more()`，
   而该函数在头文件中并不存在（见 §5.4 第 2 条）。
   判据可以机械化：把文档注释里出现的 `foo_bar(` 全部抽出，与头文件里的函数声明做差集，
   非空即为陈旧注释。这类"文档与实现漂移"在移植时会导致直接编译失败，
   属于跨库通用的一类问题。

> 本节按用户要求仅作记录，**不随本 PR 提交**（路径A 只允许改 `archives/`）。

---

## 10. 真机原始输出留档（节选）

> 环境：鸿蒙 PC（OpenHarmony 6.0 / aarch64 / clang 15.0.4 / conan 2.29.1 / meson 1.11.0 /
> ninja 1.13.1 / zsh / 仓库 `build_in_harmonyos`）。

### 10.1 上游事实核验（只读探针）

```
$ conan download json-c/0.18 -r=ohpcd
$ ls ~/.conan2/p/<jsonc>/p/include/
json-c                     ← 只有这一个目录，无顶层 json_object.h
$ ls ~/.conan2/p/<jsonc>/p/include/json-c | wc -l
16
$ ls ~/.conan2/p/<aml>/p/include/
aml1/aml.h                 ← aml 的头在 include/aml1 下
```

### 10.2 `conan create`

**首轮（失败，故障定位用；PR 正文不引用）**

```
vali/0.1.1: Not found in local cache, looking in remotes...
vali/0.1.1: Checking remote: ohpcd
vali/0.1.1: Downloaded recipe revision …
vali/0.1.1: apply_conandata_patches(): No patches defined in conandata   ← 零补丁的第一个证据
vali/0.1.1: Meson configure cmd: meson setup --native-file "…/conan_meson_native.ini" \
            "…/build-release" "…/b" --prefix=/
/system/bin/sh: /storage/Users/currentUser/.conan2/p/mesonc731ddfc5b264/p/bin/meson: Permission denied
ERROR: vali/0.1.1: Error in build() method, line 200
	meson.configure()
	ConanException: Error 126 while executing
```

**可执行性诊断（`vali-14-meson-exec.sh`，只读）**

```
$ stat -c '%a %u:%g %s %n' ~/.conan2/p/mesonc731ddfc5b264/p/bin/meson
770 20001006:file_manager 121 /storage/Users/currentUser/.conan2/p/mesonc731ddfc5b264/p/bin/meson

$ cat -A ~/.conan2/p/mesonc731ddfc5b264/p/bin/meson      # 前 3 行，确认是纯 LF 的 sh 包装
#!/bin/sh
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
exec python3 "$here/../lib/python3.12/site-packages/meson.py" "$@"

$ file …/bin/meson
…/bin/meson: /bin/sh script

--- a) 直接执行 ---        1.11.0  rc=0     ← 交互 shell 里成功！
--- b) 经 /bin/sh ---      1.11.0  rc=0
--- c) 经 sh -c ---        1.11.0  rc=0

$ mount | grep /storage/Users
tmpfs on /storage/Users type tmpfs (rw,nosuid,relatime,hmmac=use_task,mode=755,seclabel)
```

⇒ 这里**曾一度被误判为权限位问题**（"0770 且属主非构建用户"）。它是错的：
`vali-16-pyspawn-bisect.sh` 用同一个 Python 进程分别按 `shell=False` / `shell=True`
派生子进程，结果是**shell 能跑、Python `execve` 跑不了**；`vali-17-form-probe.sh`
又把三种 shebang（`#!/bin/sh`、`#!/system/bin/sh`、`#!/data/service/hnp/bin/bash`）
各试一遍，**全部 EACCES**，而把首行 `#!` 去掉后立刻 `rc=0`。
⇒ 判据是**首行有没有 shebang**（连 `os.access(X_OK)` 都是 True，权限位无关）。
完整矩阵见 §3.5，修法是配方 `generate()` 里的 `_fix_meson_launcher()`：
去掉 shebang 后由 shell 走 ENOEXEC 回退解释执行，自检行由配方自己打印。

**修复后（第二轮起，`~/vali-create-4.log` 与 CI 内嵌的那次 `conan create`）**

```
vali/0.1.1: export_conandata_patches(): No patches defined in conandata
vali/0.1.1: apply_conandata_patches(): No patches defined in conandata
vali/0.1.1: meson launcher already shebang-free: /storage/Users/currentUser/.conan2/p/mesonc731ddfc5b264/p/bin/meson
vali/0.1.1: meson launcher usable via /bin/sh (shebang-free): /storage/Users/currentUser/.conan2/p/mesonc731ddfc5b264/p/bin/meson -> 1.11.0
vali/0.1.1: Meson configure cmd: meson setup --native-file "…/conan_meson_native.ini" \
            "…/build-release" "…/b" --prefix=/
…（27 行 ninja 进度；grep -E 'error:|fatal error:|Error [0-9]+ while executing' 无命中）
======== Installing packages ========
Installing vali to …/p/bin
Installing libvali.a to …/p/lib
Installing …/b/include/vali.h to …/p/include
Installing …/build-release/meson-private/vali.pc to …/p/lib/pkgconfig     ← 随后被 package() 删掉
```

### 10.3 上游 `meson test`

```
 1/2 vali:basic         RUNNING
 2/2 vali:certification RUNNING
 1/2 vali:basic         OK              0.04s
 2/2 vali:certification OK              0.04s

Ok:                2
Fail:              0
```

### 10.4 消费者用例（test_package）原文

```
vali/0.1.1 (test package): Running test()
vali/0.1.1 (test package): RUN: ./test_vali
test_vali: 30 checks run, 0 failed
test_vali: ALL CHECKS PASSED
```

（静态宏调用点 25 处：`CHECK` 22 + `CHECK_STREQ` 3；其中 3 处在 `test_more_replies`
的 4 轮循环里 ⇒ 运行时 18 + 3×4 = 30 次。口径说明写在 `test_package/MANIFEST.yml`。）

### 10.5 `package()` 产物与 ELF / 动态依赖

```
$ find <pkg> -type f | sed "s|^<pkg>/||" | sort
bin/vali
conaninfo.txt
conanmanifest.txt
include/vali.h
lib/libvali.a
licenses/LICENSE
                                          ← 无 lib/pkgconfig/vali.pc（rmdir 生效）

$ file <pkg>/bin/vali
bin/vali: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d <pkg>/bin/vali | grep -E 'NEEDED|RUNPATH'
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]

$ file <pkg>/lib/libvali.a
lib/libvali.a: ar archive

$ nm <pkg>/lib/libvali.a | grep -E ' [TtWw] vali_' | awk '{print $NF}' | sort -u | wc -l
38                                        ← vali_client_call* / vali_service_* / vali_registry_* / vali_error_*

$ grep -n '#include' <pkg>/include/vali.h
4:#include <stdbool.h>                     ← 唯一一个 include，头是自包含的
$ wc -l < <pkg>/include/vali.h
367

$ <pkg>/bin/vali < /dev/null ; echo rc=$?
usage: vali generate [options...] <definition> <header> <code>
rc=1                                      ← 代码生成器，无 --version/--help（L2 skip 的原因）
```

### 10.6 本地 CI 模拟结果

```
$ JUNK_PR_DIFF=~/tmp/vali-pr.diff CI_PACKAGES=archives/v/vali/0.1.1 \
  CI_BRANCH=feat/vali-0.1.1 TMPDIR=~/tmp zsh ci/conan/build_and_test.sh
CI_RC=0                                   （日志 422 行）

G0_RESULT=pass                            （含 [ok] G0e: Root directory whitelist passed）
KC_RESULT=pass
JC_RESULT=pass                            （JC_ERRORS=0；JC6 涉及软件数 1，合规）
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: vali version/help failed   （非阻塞，原因见 §10.5 最后一段）
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content

[step] CI_PACKAGES received: archives/v/vali/0.1.1
━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully
```

`L1e`（R34）破坏性反向验证按预期触发：
`[sabotage] bin/ moved away` / `lib/ moved away` / `include/ moved away` →
`[ok] L1e: Negative test confirmed — test genuinely depends on vali`。

> 跑完之后档案目录会被 CI 塞进 `ci-metadata.json` / `conanfile.py.confbak` /
> `test_package/build/`，提交前必须按白名单清回 10 个文件（§7.15）。
> 另：日志里 6 行 `[fail] … 'curl'` 来自 CI 的可选预下载步骤，非门禁（§7.16）。

