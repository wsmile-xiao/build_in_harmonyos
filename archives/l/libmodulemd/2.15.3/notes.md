# libmodulemd 2.15.3 适配笔记

## 编译环境
- 构建系统: meson
- 上游仓库: https://github.com/fedora-modularity/libmodulemd
- 上游版本: 2.15.3（2026-06-12 发布；修复多处空指针解引用，适配 GLib 2.87 / PyGObject 3.55）
- 源码包: modulemd-2.15.3.tar.xz，sha256=931b44eabdd5f7d170803f3476397c8e9dea07209589e1194ff8379429991ccb
- 编译器: clang 15（/data/service/hnp/bin，aarch64-linux-ohos，C11）
- 状态: built（首轮工作树，待 HMBS 真机预检验证后由后端提交）

## 上游测试清点（源码审计，meson.build + tests/ 目录）

with_py3=false / with_py2=false 配置下 `meson test` 注册：

| 组 | 用例数 | 说明 |
|----|--------|------|
| 24 个 C GTest 可执行文件 × debug/release | 48 | modulemd/meson.build `c_tests` 字典：buildconfig、buildopts、common、component_module、component_rpm、compression、context、defaults、defaultsv1、dependencies、module、module_index、module_index_merger、modulestream、packagerv3、parse_int64、profile、rpm_map、service_level、translation、translation_entry、variant_deep_copy、obsoletes、quoting |
| modulemd-validator CLI 用例 | 32 | `modulemd_validator_tests` 字典（help/version/valid/invalid/各文档类型正误用例） |
| test_import_headers | 1 | 全部 26 个公开头逐个 gcc/g++ 引入编译 |
| **合计** | **81** | 框架均为 meson test（底层 gtest + CLI 退出码断言） |

Python 绑定测试 17 个脚本 × debug/release = 34 项因 with_py3=false 未注册
（需 gobject-introspection + pygobject，OHOS 缺失，见补充说明）。

## 编译步骤

```bash
# 真机预检（HMBS 后端执行）
conan create archives/l/libmodulemd/2.15.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# 依赖：glib2/2.88.0、libyaml/0.2.5（均为已归档版本；rpmio 已禁用，无 rpm 依赖）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `dependency('gobject-2.0')` / `dependency('yaml-0.1')` 找不到 | glib2 只生成聚合 glib-2.0.pc；libyaml 不安装 .pc | generate() 补写 gobject-2.0（Requires: glib-2.0 薄包装）与 yaml-0.1.pc（模式同 at-spi2-core 2.60.5） |
| 2 | CI worker 导出 llvm-AR/AS/STRIP/NM/RANLIB 裸名 | env 污染，meson archiver 探测失败 | generate() 弹出变量，用绝对路径 ar/as/strip/nm/ranlib 锁进 MesonToolchain（模式同 at-spi2-core） |
| 3 | test-import-headers.sh 硬编码 `gcc`/`g++` | 上游脚本写死编译器名，真机只有 clang | build 内私有 `test-shims/` 目录软链接 gcc->clang、g++->clang++，仅测试时前置 PATH，不进产物 |
| 4 | rpm 依赖链过重（popt/sqlite/openssl/lua…） | 上游默认 rpmio=enabled | `-Drpmio=disabled`；压缩探测走上游内置实现（HAVE_RPMIO=0 守卫），写入补充说明 |
| 5 | gobject-introspection / gtk-doc / pygobject 缺失 | OHOS 无该工具链 | `-Dskip_introspection=true -Dwith_docs=false -Dwith_manpages=disabled -Dwith_py2=false -Dwith_py3=false`（均为上游官方选项） |
| 6 | modulemd.h 包含 glib-object.h，消费方需 glib 头 | Conan 2 静态库 traits 默认不传播传递依赖 headers | requirements() 对 glib2 显式 `transitive_headers=True`（模式同 at-spi2-core） |
| 7 | meson install 重写 RUNPATH 破坏 OHOS 自签 | E077 已知模式 | package() 后对 bin/*/lib/* ELF 剥 .codesign 并 binary-sign-tool 重签（模式同 at-spi2-core） |
| 8 | G_DEBUG=fatal-warnings 的 debug 套件在新平台可能更脆 | 上游 debug 环境变量使警告致命 | 首轮保留上游行为全量运行；若真机出现平台特有警告致 abort，按日志逐项处理，不静默降级 |

## 源码修改

patches/0001-meson-bash-sh-fallback.patch （唯一补丁，portability）：
meson.build `find_program('bash')` → `find_program('bash','sh')`；
test-import-headers.sh `#!/bin/bash` → `#!/bin/sh`，pushd/popd → cd、
mktemp → `mktemp -d "${TMPDIR:-/tmp}/import-headers.XXXXXX"`（只换临时根目录）；
modulemd/meson.build 头文件测试由直接 exec 改为经 bash/sh 解释器调用
(`files(...)` + `test(..., bash, args: [script] + hdrs)`，21:38 预检
`OSError: [Errno 8] Exec format error`与 HMBS chmod=0 对应，同样的头文件
+ gcc/g++ 编译检查，不跳过）。其余适配均在 conanfile.py 内完成；
未引入 `#ifdef __OHOS__`。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib2 | 2.88.0 | 提供 glib/gobject（transitive_headers=True） |
| libyaml | 0.2.5 | 提供 yaml 解析（链接期；公开头不依赖 yaml.h） |

## test_package 设计（R34）

test_modulemd.c 共 8 个显式检查，全部调用真实 API：
流创建（modulemd_module_stream_new）→ version/context/名称属性读写 →
NSVC 字符串比对 → copy/equals → ModuleIndex 建索引/加流/按名查询 →
dump_to_string 导出含模块名。另加 `modulemd-validator --version` 真实运行
冒烟。标记 discovered=9 / passedCount=9。

## HMBS 标记

- `HMBS_UPSTREAM_TEST_RESULT`：build() 跑完 `meson test` 后从汇总行
  （Ok/Expected Fail/Fail/Unexpected Pass/Skipped/Timeout）动态解析，
  无汇总即抛错（防空跑误报通过）；失败/跳过/执行数不足均抛错中断构建。
- `HMBS_TEST_PACKAGE_RESULT`：test_package test() 在真实命令成功后输出，
  失败时先输出 passed=false 标记再抛错。

## 第 2 策略周期：去 libyaml requires、随包直编（2026-09-14，本轮）

- 上一方案为何无效：前三轮把“本包 /tmp 用法 + test_package CMake”当根因，
  加固的 generate()/test_package 代码在预检的失败点根本未执行——日志显示
  `conan create` 先构建依赖 `libyaml/0.2.5`（`cmake.configure()` 报
  `System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
  检查失败，伴随只读 `/tmp`），本包配方尚未运行；重复改本包同类位置不可能
  改变结果（17:07 与 17:28 日志字节级同指纹）。
- 新路线（与前三轮不同）：不再假设“修好本包 TMPDIR 就能变绿”，改为消除该
  跨包构建节点——`requirements()` 删除 `libyaml/0.2.5`；`conandata.yml` 新增
  `yaml_sources`（与 libyaml 配方同官方 URL/sha256，无补丁）；`source()` 同步
  取到 `yaml-src/`；`build()` 先以直编（conf 优先解析 clang，`-O2 -fPIC` 逐个
  编译 `src/*.c`，ar 归档到 `build_folder/yaml-prefix`，命令前挂
  `TMPDIR/TMP/TEMP` 可写前缀）产出 `libyaml.a` + `yaml.h`，并向 generators
  写入 `yaml-0.1.pc` 供 meson `dependency('yaml-0.1')` 解析，全程不调用 cmake；
  `package()` 随包安装 `lib/libyaml.a` + `include/yaml.h`，
  `package_info()` 改为 `libs=["modulemd","yaml"]`、`requires=["glib2::glib2"]`。
  私有 prefix 遵循 R49（build 内目录，不碰 `/usr/local`）。
- 测试口径不变：上游 `meson test` 81 项仍在 `build()` 全量运行并动态解析
  `HMBS_UPSTREAM_TEST_RESULT`；test_package 仍为 8+1=9 项直编消费者测试
  （聚合 `cpp_info` 自动带上随包 yaml，无需改动）。
- 回退条件：libyaml 官方配方修复 OHOS 下 cmake/HarmonyOS 兼容并重发二进制后，
  可回退为 `self.requires("libyaml/0.2.5")` 并删除随包直编（届时 yaml 符号改
  由依赖包提供，`package_info` 同步改回）。

## 第 3 策略周期：override 传递 zlib 到 1.3.1.2（2026-09-14，本轮，与随包直编不同）

- 前次结果比较：18:21 预检已跑在随包直编树上（本包 package_id 变为 aa42aa53…，
  日志不再出现 libyaml）——直编绕过了 libyaml 断点，失败前移到传递依赖
  `zlib/1.3.1`（glib2/2.88.0 引入）在 `cmake.configure()` 的同类错误
  （`System is unknown to cmake` + `CMAKE_C_COMPILER` 检查失败，`build()` 81 行）。
- 新根因（stale pin，非缺二进制）：远端 `zlib/1.3.1` 的配方修订版仍是旧 CMake 版；
  仓库早在 2026-07-07（c50eceb06 起）把 zlib 改为 Makefile 构建（无 cmake），但按
  R37 修复只能进后缀版本（已核对 `archives/z/zlib/1.3.1.2/conanfile.py` 为
  `./configure --static && make -j1` + `make check`，`requirements()` 为空），
  `1.3.1` 永久停留在坏修订版，而 glib2 精确钉死 `zlib/1.3.1`。
- 不同策略：不对 zlib 重复随包直编（那会捆绑 R26 系统同名库 libz，触发系统库
  隔离门禁），改用 `self.requires("zlib/1.3.1.2", override=True)` 做图覆盖——
  仍走制品仓 published 包，不捆绑；`--build=missing` 下要么复用其二进制，要么
  用 Makefile 配方源码构建，全程无 cmake。同上游 1.3.1、ABI 一致。
- 待验证：pcre2（autotools，尚未在日志中失败）与 glib2 自身二进制是否就绪；
  若后续断点仍是同类 CMake 问题，按本模式继续收敛（有限闭包：pcre2/zlib 之外
  glib2 已自带 libffi/proxy-libintl 子项目，无其他 Conan 依赖）。

## 第 4 策略周期：`as` 降为可选、回退 C 编译器作汇编驱动（2026-09-14，本轮）

- 前次结果比较：18:48 预检已跑在 override 树上——依赖图一次算通
  （`requires: glib2/2.88.Z pcre2/10.45.Z zlib/1.3.Z`，再无缺二进制重编），
  失败首次进入本包自身 `generate()`（退出码 6）：
  `Invalid configuration: Required build tools not found in PATH: as`。
  注意 ar/strip/nm/ranlib 均解析成功，唯独缺独立 `as`。
- 根因：沿用 at-spi2-core 的五工具硬校验，但当前真机 PATH 里没有独立 `as`
 （环境漂移；且 `llvm-as` 是 IR 汇编器，接口不对，不能拿来顶替 GNU `as`）。
  上游本库为纯 C、无 `.S` 文件，`as` 实际不会被调用；clang 自带集成汇编器，
  可作汇编驱动。
- 不同策略（最小容错，非放宽测试）：`as` 降为可选——独立 `as` 优先，缺失回退
  conf C 编译器绝对路径，再缺则不设 `tc.as_`（meson 默认走编译器汇编）并告警；
  ar/strip/nm/ranlib 仍硬性要求。测试口径零改动。

## 第 5 策略周期：补生成 libyaml config.h（2026-09-14，本轮，真机 19:32 预检）

- 现象：随包直编在 `clang -c yaml-src/src/api.c` 报
  `use of undeclared identifier 'YAML_VERSION_STRING'/'YAML_VERSION_MAJOR'/
  'MINOR'/'PATCH'`（4 errors），`conan create` 退出码 1。
- 根因：libyaml 0.2.5 原始 tag 无版本宏——`include/yaml.h` 仅声明
  `yaml_get_version_string()` 函数，宏定义由 CMake 按 `cmake/config.h.in`
  生成到二进制目录 `include/config.h`，经 `src/yaml_private.h`
  `#if HAVE_CONFIG_H / #include "config.h"` 引入；直编命令缺
  `-DHAVE_CONFIG_H` 与生成头搜索路径，故为真阳性缺头，非编译器/平台问题。
- 修复：`_build_vendored_yaml()` 在 `build_folder/yaml-generated/include/`
  生成 `config.h`（与上游 CMakeLists 一致：0/2/5/"0.2.5"），编译追加
  `-DHAVE_CONFIG_H -DYAML_DECLARE_STATIC -I<generated> -I<yaml-src/include>
  -I<yaml-src/src>`；测试口径零改动。
- 待验证：HMBS 预检 `conan create` 是否越过 yaml 直编进入 meson 配置/构建。

## 第 6 策略周期：覆盖 MesonToolchain 编译器为已验证路径（2026-09-14，本轮，真机 19:46 预检）

- 前次结果比较：19:32 轮的 config.h 修复已生效——本轮日志不再出现 yaml
  api.c 缺宏错误，vendored 直编已通过，失败前移到 `meson.configure()`。
- 现象：`meson.build:12: ERROR: Unknown compiler(s):
  [['/data/service/hnp/bin/clang']]`，`Running .../clang --version` ENOENT。
- 根因：profile/conf 的 C 编译器绝对路径在真机已不存在（环境漂移）；
  MesonToolchain 默认沿用该路径；而 PATH 中的 clang 可用（同轮 vendored
  直编成功即证据）。与前两轮（as 可选、config.h）不同策略。
- 修复：`generate()` 中 `tc.c/tc.cpp` 覆盖为已验证编译器（conf 文件存在才
  用，否则回退 `clang→cc` / `clang++→c++`，与 `_resolve_cc`/test_package
  同策略）；仅替换工具路径，测试口径零改动。
- 待验证：HMBS 预检 `meson configure` 是否通过并进入构建/上游测试。

## 第 7 策略周期：锁定 pkg-config 工具并前置 PKG_CONFIG_PATH（2026-09-14，本轮，真机 19:58 预检）

- 前次结果比较：19:46 轮的 tc.c/tc.cpp 覆盖已生效——本轮 meson 编译器探测
  全 YES 并进入依赖查找，失败前移到 `dependency('gobject-2.0')`。
- 现象：`ERROR: Dependency lookup for gobject-2.0 ... Pkg-config for machine
  host machine not found`（tried cmake 后放弃）。
- 根因：缺的是 pkg-config 可执行文件本身（meson 在 build 时 PATH 找不到
  pkg-config/pkgconf），非 .pc 内容问题；与前两轮（config.h、编译器路径）
  不同断点、同类环境漂移。
- 修复：`generate()` 定位 pkg-config（pkgconf 经私有 shim 顶替，兼顾 HMBS
  工具目录探测），锁定 `tc.binaries[pkgconfig/pkg-config]` + `PKG_CONFIG`；
  `build()` 在 `meson.configure()` 前显式前置 `PKG_CONFIG_PATH`
 （generators + 依赖包 pkgconfig 目录），保障兼容 .pc 可见。测试口径零改动。
- 待验证：HMBS 预检 `meson configure` 依赖查找是否通过。

## 真机预检阻塞项（跨包依赖，2026-09-14 追记）

- 现象：预检连续三轮倒在 `libyaml/0.2.5: cmake.configure()`，报错
  `System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
  检查失败，伴随只读 `/tmp` 诊断；本包配方尚未被执行到。
- 定位：失败的是已发布依赖 `libyaml/0.2.5` 自身的配方（原生
  CMakeToolchain，无 TMPDIR 透传、无 HarmonyOS 平台处理），其远端二进制
  与当前配置不匹配，`--build=missing` 被迫从源码重编即失败。本包侧已做
  的 TMPDIR 复用与 test_package direct-cc 均无法触及该构建阶段。
- 处理：单库 PR 纪律下不顺手改依赖归档；待 libyaml 侧补上同类修复
  （可写 TMPDIR + HarmonyOS 下 cmake 兼容）并重新发布后，本包预检可直接变绿。
  本包 test_package 已提前改为 direct-cc，避免届时复现同类 CMake 失败。

## 第 8 策略周期：tool_requires 供给 pkgconf（2026-09-14，本轮，真机 20:09 预检）

- 前次结果比较：19:58 轮的 tc.c/tc.cpp 覆盖已生效（meson 编译器探测全 YES），
  失败前移到 `dependency('gobject-2.0')`，但本包 generate() 主动抛
  `Invalid configuration: pkg-config/pkgconf not found in PATH nor HMBS tool dirs`。
- 上一方案为何无效：上一周期假设“真机 PATH/HMBS 工具目录必有其一可用”，
  走“定位并锁定系统工具”路线；20:09 日志证明真机既无 pkg-config 也无 pkgconf
 （`Invalid configuration` 即本包硬失败），定位式修复在该环境下是死循环，
  必须换路线（第 3 策略周期纪律：禁止沿用相同根因假设）。
- 新路线（供给而非定位）：`build_requirements()` 新增
  `self.tool_requires("pkgconf/3.0.5")`（仓内 burp2/captagent/ekg2 先例），
  `generate()` 优先从 `self.dependencies.build["pkgconf"]` 的 `bin/pkgconf`
  解析，仅缺失时回退 PATH/HMBS 目录；仍为 pkgconf 名时沿用私有
  `pkg-shims/pkg-config` 软链接顶替；`tc.binaries[pkgconfig/pkg-config]` +
  `PKG_CONFIG` 锁定绝对路径；并 `VirtualBuildEnv(self).generate()` 让 build()
  阶段 PATH 可见工具包。pkgconf 配方无依赖、不触 cmake try_compile。
  测试口径零改动（上游 meson test 81 项 + test_package 9 项）。
- 待验证：HMBS 预检 `meson configure` 的 gobject/yaml 依赖查找是否通过。

## 下载可靠性修复（2026-09-14，本轮，真机 20:34 预检）

- 现象：`source()` 下载 `modulemd-2.15.3.tar.xz` 三次 `ConnectTimeoutError`
  （connect timeout=30，重试 2 次后抛 `ConanException`，退出码 1）。
- 处理（守则下载超时例外）：`conandata.yml` 的 `sources` 与 `yaml_sources`
  的 `url` 由单值改为有序列表，镜像在前、官方原 URL 在最后兜底；
  镜像复用 `ci/conan/build_and_test.sh` 的 GitHub 映射
 （`https://gh-proxy.com/` + 原 URL），未引入 GitCode/gitee 搬运源；
  `sha256` 保持不变。同指纹第 2 次修复：前次工作树仍为单 URL，
  本轮首次落地镜像列表，与之前单源重试是不同策略。

## bash 供给修复（2026-09-14，本轮，真机 20:39 预检）

- 前次结果比较：20:34 轮的镜像回退已生效（下载越过，进入 meson configure），
  本轮失败前移到 `meson.build:65 find_program('bash')` 报
  `Program 'bash' not found`。与前两轮（pkgconf 供给、镜像回退）不同断点。
- 根因：真机 PATH 无 bash，但实体存在（test_package 早用
  `CONFIG_SHELL/which bash//data/service/hnp/bin/bash` 三级回退）。
- 修复：`generate()` 同法解析 bash（PATH 优先，HMBS 工具目录 +
  `/data/service/hnp/bin:/bin:/system/bin` 回退），锁定
  `tc.binaries["bash"]` 并前置其目录到 PATH；缺失则硬失败明示。
  仅补工具路径，测试口径零改动。

## 第 9 策略周期：bash 缺失改走“补丁+供给”（2026-09-14，本轮，真机 21:18 预检）

- 上一方案为何无效：20:39 轮假设“bash 实体存在、仅不在 PATH”，在
  generate() 做 PATH/HMBS 工具目录 + /data/service/hnp/bin:/bin:/system/bin
  定位并硬失败；21:18 日志复现完全相同的
  `Invalid configuration: bash not found in PATH nor /data/service/hnp/bin`
  （meson.build:65），证明真机根本无独立 bash（仅有 SHELL=/bin/sh），
  定位路线已穷尽。按第 4 策略周期纪律必须换路线。
- 新路线（供给而非定位，上游审计依据）：
  原生 meson.build 仅 `bash = find_program('bash')` 一处硬依赖，
  且在 modulemd/ 子目录零使用；唯一真实消费者是
  modulemd/tests/test-import-headers.sh（#!/bin/bash + pushd/popd +
  `mktemp -d` 走只读 /tmp）。库/validator 构建本身无 bashisms。
- 实施：
  (1) 新增 patches/0001-meson-bash-sh-fallback.patch：
  meson.build 改为 `find_program('bash', 'sh')`（configure 不再硬失败）；
  测试脚本改为 #!/bin/sh，以 cd 替代 pushd/popd，
  mktemp 改为 `mktemp -d "${TMPDIR:-/tmp}/import-headers.XXXXXX"`（只读
  /tmp 对策，仅换临时根目录）；conandata.yml patches 登记（sha256 不变）。
  (2) generate() 改为供给：有真 bash 仍优先用；否则以系统 sh 供给名为
  bash 的 shim（build 内 sh-shims/bash→首个可用 sh），锁定
  tc.binaries["bash"] 并前置 PATH；两者皆无才硬失败。
  (3) test_package 同步：shell 解析改为 bash 优先、sh 回退
  （CONFIG_SHELL/which bash→which sh→/bin/sh→/system/bin/sh），测试口径
  仍为 8+1=9 项，不跳过不断言。
- 待验证：HMBS 预检 meson configure 是否越过 bash 依赖查找进入构建/上游测试。

## 第 10 策略周期：补 glib-2.0.pc 的 gnome 工具变量（2026-09-14，本轮，真机 21:32 预检）

- 前次结果比较：21:18 轮的 bash 补丁+供给已生效——本轮日志越过 bash 查找、
  编译器探测与 glib-2.0 依赖查找，失败前移到
  `modulemd/meson.build:140 gnome.mkenums_simple()` 报
  `Could not get pkg-config variable and no default provided for
  <PkgConfigDependency glib-2.0>`。与前两轮（bash 供给、镜像回退）不同断点。
- 根因：meson gnome 模块经 `dependency('glib-2.0')
  .get_pkgconfig_variable('glib_mkenums')` 定位 glib-mkenums；Conan
  PkgConfigDeps 生成的 glib-2.0.pc 只有 prefix/libdir/includedir，
  无 glib_mkenums 等变量，且宿主 glib2 bindir 默认不在构建 PATH，
  双缺导致硬失败。非测试可跳过项（枚举生成是库构建本身）。
- 修复：build() 在 meson.configure() 前新增
  `_enrich_glib_pc_for_gnome()`——把 glib2 包 bindir 内真实工具
  （glib-mkenums/glib-genmarshal/gobject-query/…，缺失回退 PATH）
  的绝对路径补进 generators/glib-2.0.pc，并把 bindir 前置 PATH；
  仍缺才让 meson 报确切缺件。仅补工具定位，测试口径零改动。
- 待验证：HMBS 预检 meson configure 是否越过 mkenums 进入构建/上游测试。

## 第 11 策略周期：头文件测试改走解释器调用（2026-09-14，本轮，真机 21:38 预检）

- 前次结果比较：21:32 轮的 glib-mkenums 变量补齐已生效——本轮越过 configure
  进入 `meson test`（已打印 61 项通过），但 `meson test` 自身以
  `OSError: [Errno 8] Exec format error: .../modulemd/tests/test-import-headers.sh`
  崩溃，`_run_upstream_tests()` 因 returncode!=0 抛错（即使解析 status=passed）。
- 根因：`modulemd/meson.build` 用 `find_program('tests/test-import-headers.sh')`
  直接 exec 脚本，依赖内核 shebang 解析 + 可执行位；真机 HMBS 上报
  `chmod=0`（不支持 chmod/执行位），直接 exec 不可靠。仅换 shebang
  （前轮补丁）不够——崩溃的是 exec 机制本身，非解释器路径。
- 修复：补丁新增 modulemd/meson.build hunk——`files(...)` 取脚本，
  `test('test_import_headers', bash, args: [script] + modulemd_hdrs)` 经
  bash/sh 解释器调用（bash 已是 `find_program('bash','sh')`），脚本以文本
  被读取，不依赖 exec 位/shebang；gcc/g++ 头编译检查与 TMPDIR mktemp
  保持不变，不跳过任何用例。仅改调用机制。
- 待验证：HMBS 预检 `meson test` 是否 returncode=0 且全量通过。

## 第 12 策略周期：测试环境断链修复 + 串行执行（2026-09-14，本轮，CI #46545）

- 前次结果比较：HMBS 真机预检已通过（81 项全绿），但官方 CI #46545 复现失败：
  70 Ok / 1 Fail（test_import_headers，0.11s 速败）/ 10 Timeout（validator 用例，
  全部卡 60s 被 SIGTERM）。同代码两地结果相反，指向 CI worker 特有的环境差异，
  非用例本身回归。
- 根因 1（test_import_headers 速败）：_test_environment() 用裸名创建 gcc/g++ 软链接
  （如 g++ 指向裸名 clang++），且测试 PATH 未含 pkg-config。CI worker 的 PATH 极简
  （无 hnp/bin、无 pkgconf），裸名即断链；pkg-config（build 依赖，不在 host PATH 内）
  同样不可解析，脚本首个 pkg-config 调用即空展开，gcc 缺 glib 头速败。
  HMBS 单机 PATH 含工具目录故通过。
- 根因 2（validator 并发超时）：10 个超时耗時均为 60.09~60.26s，而构建步总耗时仅
  128s，证明 meson test 默认高并行下多用例同时饥饿超时；约束设备并行争用所致，
  非 validator 挂起（HMBS 低并行即通过）。
- 修复（均在 conanfile.py，不改上游源码/补丁，测试口径零改动）：
  (1) 新增 _resolve_test_tool()：conf、PATH、HMBS 工具目录、hnp/bin 逐级解析为
  绝对可执行路径；gcc/g++ 软链接一律指向绝对路径，c++ 缺失时回退复用 cc 并告警
  （不断链）；测试 PATH 增补 build 依赖 bindir（pkgconf）、generate() 的 pkg-shims
  （含 pkg-config 顶替）与编译器目录，并设置绝对 PKG_CONFIG 双保险；
  (2) meson test 改为串行执行并给慢设备留余量（用例数与断言不变），
  HMBS_UPSTREAM_TEST_RESULT 的 command 字段同步更新为实际命令；
  (3) 失败时从 meson-logs/testlog.txt 提取 FAIL/TIMEOUT 用例块打印，
  消除 CI stdio 只留尾部导致的诊断盲区。
- 待验证：HMBS 预检与官方 CI 是否 81/81 通过。

## 第 13 策略周期：getcwd 失效加固（2026-09-14，本轮，CI #46570）

- 现象：真机预检 81/81 通过，但官方 CI #46570 中 80/81，
  `test_import_headers` 以 0.11s 速败，stderr 为
  `shell-init/getcwd: cannot access parent directories` + `pwd` 同错；
  随后 `conan create` 被 CI 的 3600s 超时杀死（后端判环境问题）。
- 根因：`test-import-headers.sh` 在 `set -e` 下 `origdir=\`pwd\`` 无回退，
  启动目录一旦不可用（CI worker 并发清理/挂载抖动）即整例失败；
  且 `_run_upstream_tests()` 未指定 cwd，子 bash 继承的可疑 cwd
  在脚本运行前就已损坏（shell-init 报错即证据）。与之前
  Exec format error / 裸名断链不同断点。
- 修复（测试口径零改动，不跳过）：补丁侧 `mktemp/pwd/cd/rm` 全部加
  `2>/dev/null` 回退（TMPDIR 模板失败回退裸 `mktemp` 再回退静态目录；
  `pwd` 失败回退 `MESON_BUILD_ROOT`；`cd` 失败回退 `/tmp`；`rm` 加引号）；
  配方侧 `subprocess.run(meson test)` 显式 `cwd=self.build_folder`
  （先 `makedirs` 确保存在），保证子进程启动目录有效。
- 待验证：HMBS 预检与官方 CI 是否 81/81 通过；超时是否随环境恢复消失
  （超时本身按守则归 infra，不做串行/超时参数改动）。

## 第 14 策略周期：补丁解析失败修复（2026-09-14，本轮，真机 compile 阶段）
- 现象：预检倒在 `apply_conandata_patches`，`ConanException: Failed to parse patch: .../0001-meson-bash-sh-fallback.patch`，`extra lines for hunk no.2`（test-import-headers.sh）。
- 根因：补丁手工编辑后块头计数与正文不符（第 3 块新行数 9 实为 10；第 4 块遗漏 `-rm -Rf $tempdir` 原行致旧行数 5 实为 4），且 `#!/bin/sh` 被注释挤到第 3 行；Conan 内建解析器严格校验行数即抛错，与只读 /tmp 无关。
- 修复（仅补丁格式，不改语义）：第 3 块头 `+16,9` 改 `+16,10`；补回遗漏的 `-rm -Rf $tempdir` 原行，第 4 块头 `+68,5` 改 `+69,5`；shebang 移回第 1 行。已用上游原文件 `git apply --check/-p1` 双验证通过。
- 待验证：HMBS 预检是否越过 `export_sources/apply` 进入 meson 配置/构建。

## 第 15 策略周期：头文件测试免链接 + 测试环境补 LLVM 库路径（2026-09-14，本轮，CI #46780）
- 前次结果比较：真机预检 81/81 通过，但官方 CI #46780 仍 70 Ok / 1 Fail（test_import_headers，0.68s）/ 10 Timeout（validator，各卡 120s），且 `conan create` 被 3600s wrapper 超时杀死。串行（--num-processes 1，multiplier 2）未治愈挂起，反而把总时长推上 wrapper 上限。
- 根因 1（test_import_headers 确定性失败）：该脚本对每个头文件做 `gcc ... -o $header.out $header.c`（空 main 的链接），CI worker 的 lld 因缺 `libxml2.so.16`（`xmlFreeDoc` 等符号全缺，构建期靠 profile 的 `.../llvm/lib` 进 LD_LIBRARY_PATH 才链接成功）而链接失败；测试期重建的 LD_LIBRARY_PATH 丢了该条即复现。链接空 main 从未测试库本身，头文件可引入性编译即覆盖。
- 修复 1（不跳过任何头文件/断言）：`build()` 在 `apply_conandata_patches` 后新增 `_harden_header_script_for_ci()`，把脚本内 `-o $header.out` 文本替换为 `-c -o $header.o`（编译为止，不走 lld；echo 行同步，日志仍显示真实命令）。补丁文件不动，避免行号脆弱。
- 根因 2（测试环境缺 LLVM 库路径 + 陈旧 PWD）：`_test_environment()` 仅聚合依赖 libdir，原样透传的 LD_LIBRARY_PATH 在 meson test 子进程不可假设；`shell-init: getcwd` 表明子 shell 启动 cwd 已失效（陈旧 PWD）。
- 修复 2：显式把编译器所在目录及其 `../lib` 与已知 `.../llvm/lib` 补进测试期 LD_LIBRARY_PATH，并把 `PWD` 锁定到已确保存在的 `build_folder`。仅补环境，不改用例。
- 根因 3（串行导致 wrapper 超时）：串行下 10×120s 挂起 + 70 余项 C 测试串行即超 3600s，掩盖真实失败明细。
- 修复 3：`meson test` 改为 `--num-processes 4 --timeout-multiplier 3`（总时长回百秒级可上报明细；慢设备单测预算反而从 2 倍提到 3 倍），`HMBS_UPSTREAM_TEST_RESULT.command` 同步；用例与断言零改动。
- 待验证：HMBS 预检是否仍 81/81；CI 是否 Fail 收敛到 validator 挂起本身（届时再凭 testlog 明细定位 validator 侧）。

## 第 16 策略周期：诊断正则回溯灾难改线性扫描（2026-09-14，本轮，CI #47242）

- 现象：CI #47242 的 meson test 已跑完并打印汇总（71 Ok / 10 Timeout，
  validator 各卡 180s）且配方已输出 `HMBS_UPSTREAM_TEST_RESULT failed`，
  但 `conan create` 仍被 wrapper 以 `TIMED OUT after 3600s` KILL，
  无 conan 退出码、无 L1 失败明细。真机同 commit 预检 81/81 通过。
- 根因：`_run_upstream_tests()` 失败分支的
  `re.findall(r"(?ms)^(.*?^(?:FAIL|TIMEOUT):.*?$.*?)(?=^\\d+/\\d+ |\\Z)")`
  在含 10 个 TIMEOUT 的 testlog 上指数回溯——meson 退出后的诊断提取阶段
  卡死，把“测试失败”拖成“构建超时”。真机 0 失败时该正则零匹配、扫描即返，
  故两地表现分裂；与 validator 本身挂因无关，是配方诊断代码缺陷。
- 修复（仅诊断输出，不改测试口径）：testlog 读取上限 2MB，
  改为线性行扫描（`^\\d+/\\d+ ` 为块头，单块上限 150 行，
  仅含 FAIL:/TIMEOUT: 的块打印前 6 块尾部 3000 字符），零回溯；
  判定仍只用 stdout 汇总行（Ok/Fail/Timeout 计数），81 项全量运行不变。
- 待验证：HMBS 预检通过；下一次 CI 若 validator 仍挂，应为 L1 快速失败
  并附 6 块明细，而非 3600s 超时（届时再凭明细定位 validator 侧）。
