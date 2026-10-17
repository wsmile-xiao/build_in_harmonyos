# xplc 0.3.13 适配笔记

## 编译环境
- 构建系统: autotools（Autoconf **2.59** 预生成 `configure` + 手写 `Makefile`/`*/rules.mk`，**不支持 VPATH ⇒ 必须 in-tree**）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 / clang++ 15.0.4（OHOS SDK，`Target: aarch64-unknown-linux-ohos`）
- profile: `ci/conan/profiles/ohos-aarch64`（`os=OHOS arch=armv8 compiler=clang 15 libcxx=libc++ cppstd=17 build_type=Release`）
- 状态: built

## 编译步骤

```bash
conan create archives/x/xplc/0.3.13 \
  -pr:h "$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b "$TARGET_REPO/ci/conan/profiles/ohos-aarch64" --build=missing
```

配方 `generate()` 注入三项：`AutotoolsDeps`（依赖 -I/-L）、`tc.configure_args.append("INSTALL=/bin/install")`、
`tc.extra_cxxflags.append("-Wno-c++11-narrowing")`；`build()` 顺序为
`apply_conandata_patches → _pin_autotools_timestamps → configure → 产物核对 → make(-j1) → 产物核对 → make tests`；
`package()` 为 `install → 产物核对 → SONAME 符号链接修复`。

上游入口：`./configure && make`（default 目标 = `libxplc.a libxplc_s.a libxplc.so libxplc-cxx.a uuid/bin/uuidgen`），
测试入口 **`make tests`**（上游**没有** `check` 目标）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **★uuid include 路径适配点**：档案 `uuid/2.40.1` 的 `uuid.pc` 报 `Cflags: -I${includedir}/uuid`，而 xplc 源码用 `<uuid/uuid.h>` | 档案 `package_info()` 是 `includedirs=["include"]`（conan 路径正确），但 `uuid.pc` 的 `Cflags` 多带一层 `/uuid` 子目录——两套口径不一致 | **必须走 conan cpp_info（`AutotoolsDeps` 注入 `-I<prefix>/include`），不得直接采信 `pkg-config --cflags`**。三路编译实证：形态A `-I<p>/include` rc=0 ✅ / 形态B `-I<p>/include/uuid` rc=1 `fatal error: 'uuid/uuid.h' file not found` ❌ / 形态C 形态A+`-luuid` rc=0 ✅ |
| 2 | config.guess `rc=1 unable to guess system type`；config.sub 对 `aarch64-unknown-linux-ohos` `rc=1 Invalid configuration` | 2005-04-22 版 config 脚本无 HarmonyOS/ohos 词表（族A，2 红） | 补丁 `0001`（主 case 首位注入 `*:HarmonyOS:*\|*:HongMeng:*` → 输出 ohos triplet，且在 `set_cc_for_build` 的 umask-077 临时目录**之前** exit）+ `0002`（`linux-ohos*` 三处 hunk）。形态B/D 双通 |
| 3 | configure `rc=1 cannot guess build type`（conan 默认路径必现） | conan `conanautotoolstoolchain.sh` **0 处** `--host/--build`，profile 也未设 `tools.gnu:*_triplet` → configure 落回 config.guess | 由 #2 补丁解决；**未**按 a52dec 先例强传 `--build/--host=...linux-gnu`（会与 conan OHOS triplet 打架，编排方已否决该方案） |
| 4 | configure `rc=0` 但 `include/autoconf.h`/`config/config.mk` **全缺**（假绿） | autoconf 2.59 `configure:7686/7691` 的 `(umask 077 && mktemp -d ./confstatXXXXXX)` 在 HMDFS 落成 `drwx--S---`，进程 euid 被映射后不可写（族B） | 补丁 `0003`（`umask 077 → 022`，a52dec `0002-configure-umask-022.patch` 逐字同款）。**并把「产物核对」写进配方 `_verify_configure_outputs()`：configure rc=0 ≠ 成功，autoconf.h/config.mk/config.status 三件非空才进 make** |
| 5 | `make rc=2`：`moduleloader.cpp:65 case value evaluates to -1, which cannot be narrowed to type 'unsigned int' [-Wc++11-narrowing]` | `switch(version_major)` 是 `unsigned`，`#ifdef UNSTABLE` 分支挂 `case -1:`；minor=3 奇数 → `-DUNSTABLE` 必注入 → 必触发。**窄化自 C++11 起即 error** | `tc.extra_cxxflags.append("-Wno-c++11-narrowing")` 保 `cppstd=17`。**bcp 先例的 `gnu++14` 对本错误无效**（最小复现四档：c++17 rc=1 / gnu++14 **rc=1** / c++17+豁免 rc=0 / gnu++98 rc=0）→ E705 草稿登记该边界。**注：`tc.cxxflags` 是 property，append 静默失效，必须 `extra_cxxflags`** |
| 6 | `make install rc=0` 但 **24 个头文件只装入 1 个**（第二重假绿） | ① 设备 PATH **不含 `/bin`** → configure 的 `for as_dir in $PATH` 探测落空；② 回退到 2000-01-28 版 `install-sh`，其第 57 行 `while [ x"$1" != x ]` **只是选项解析、无多源循环** → 只取首参；③ `find` 无匹配仍 rc=0 构成第三层假阳性 | `tc.configure_args.append("INSTALL=/bin/install")`（不带 `-c`，规避 conan `cmd_args_to_string` 的空格引号面；toybox `/bin/install` 多源实测 24/24）。**`_verify_install_outputs()` 把产物核对从 configure 扩到 install 阶段** |
| 7 | 消费者编译 `IObject.h:66 non-const static data member must be initialized out of line` | 上游把 `-DUNSTABLE` 只加进 `CFLAGS`（`configure.ac:211`），而 `dist/xplc.pc.in` 的 `Cflags: -I${includedir}` **不含**它 → 头里 `#ifndef UNSTABLE` 分支展开成 `static bool UNSTABLE_INTERFACE = true;`（C++11 非法） | `package_info()` 加 `self.cpp_info.defines = ["UNSTABLE"]`（conan 消费路径自动注入）。**pkg-config 旁路限制：裸 `pkg-config --cflags` 拿不到该宏，非 conan 消费者需自行补 `-DUNSTABLE`（上游真实缺陷，照实登记）** |
| 8 | 动态链接消费者 `Error loading shared library libxplc.so.0.3.13-unstable`（**带 `LD_LIBRARY_PATH` 也失败**） | minor=3 奇数 → `xplc/vars.mk` 设 `SONAME=libxplc.so.$(PACKAGE_VERSION)-unstable`，但 install 规则装出的实文件名是 `libxplc.so.$(PACKAGE_VERSION)`——上游 unstable 路径两条规则不一致 | `package()` 内补符号链接 `libxplc.so.0.3.13-unstable → libxplc.so.0.3.13`（`lib/` 与 `lib/xplc-0.3.13/` 各一）。补后动态消费者真实运行通过（服务管理器 + `getObject` 双 OK）。**不采「只交静态」——功能残缺（编排方裁决）** |
| 9 | `test_package/test.cpp` 首版 `rc=139 Segmentation fault` | `mutate()` **文档明说会 release 入参**（`utils.h:198` `aObj->release()`），我又对同一对象 release 一次 = 双重释放/UAF | 去掉多余的 `loader_obj->release()`，对齐上游 `tests/test004.cpp` 范式（`getObject` → `mutate<>` → 只释放 mutate 返回值）。修后 **11 passed, 0 failed** |
| 10 | **★链接变量族**：`conan create` 的 `make tests` 报 `make: *** No rule to make target '-luuid', needed by 'tests/testmain'`（主库与 test000–011 对象**全部编译成功**，败在链接阶段；族 A–F 六族之外的新族） | **手写 Makefile 的 lib 标志位置 vs AutotoolsDeps 注入面冲突**：conan `AutotoolsDeps` 按设计把每个依赖库写进 **`LIBS` 环境变量**（`tools/gnu/autotoolsdeps.py` → `env.append("LIBS", libs)`），configure 据此把 `LIBS:=-luuid` 替换进 `config.mk:50`；而上游是手写规则、把 **`$(LIBS)` 放在先决条件位**（`tests/rules.mk:32`：`tests/testmain: … libxplc.a libxplc-cxx.a $(LIBS)`）→ make 把裸 `-luuid` 当**文件目标**找规则，必然失败。原生三次对照（fixC2/fixI/cfgv2）`LIBS:=` **全为空**（本机 `AC_SEARCH_LIBS` 把 dlopen 解析进 libc），故原生从未触发 | `tc.configure_args.append("LIBS=")` 在 configure 期清空 → `config.mk` 恢复 `LIBS:=`（**与原生逐字一致**），且**保留 uuid 接线**：configure 仍记 `with_uuid:=-luuid`（uuidgen 走 `LDLIBS+=$(with_uuid)`）、AutotoolsDeps 仍供 `-I<uuid>/include`/`-L<uuid>/lib`。本地端到端实测 `make`+`make tests`+`make install` 三段 rc=0、**0 failed / 230 passed**、**24/24 头**、uuidgen 可运行。**优于备选**（每次 make 命令行传 `LIBS=`）：单点解决，后续 `make`/`make install` 自动继承、无需逐次覆盖 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `patches/0001-config.guess-harmonyos.patch` | `config.guess` | 主 case 首位注入 `*:HarmonyOS:*:* \| *:HongMeng:*:*`（MACHINE 归一化 → `${MACHINE}-unknown-linux-ohos`，`exit ;;`）；`set_cc_for_build` 的 3 处 `umask 077 → 022` |
| `patches/0002-config.sub-ohos.patch` | `config.sub` | 三处 hunk：`maybe_os` 白名单加 `linux-ohos*`；OS 基本类型大列表加 `-linux-ohos*`；`-linux-ohos*) os=-linux-ohos` 分支（**必须排在 `-linux*)` 之前**，否则被 `sed s\|linux\|linux-gnu\|` 改写成 `linux-gnu-ohos`） |
| `patches/0003-configure-umask-022.patch` | `configure` | `:7686/:7691` 两处 `umask 077 → 022`（a52dec 先例逐字同款） |

三补丁对 pristine orig 树 `-p1 --dry-run` rc=0、实打 rc=0，打完与设备实测树 `cmp` **逐字节一致**。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| uuid | `2.40.1`（ohpcd 档案） | configure 双路径的外部探测目标；`package_info.includedirs=["include"]` 导出 `include/uuid/uuid.h`，`nm` 见 `uuid_unparse`/`uuid_parse`/`uuid_generate`。**未注入 -I/-L 时 `AC_CHECK_LIB` 会假绿（E2186），故 AutotoolsDeps 必须 generate** |
| dl | OHOS sysroot | `AC_SEARCH_LIBS(dlopen, dl)`；`dlopen/dlsym` 符号在 `libc.so`，`package_info.system_libs=["dl"]` |
| clang/clang++ | 15.0.4 | profile 钉死 |

## 测试面与验证结果

### 上游测试（N = 12，不进「鸿蒙特有测试」行）

| 口径 | 取数命令 | 值 |
|---|---|---|
| 框架注册数（ADD_TEST） | `grep -cE '^\s*ADD_TEST\(test' tests/testmain.cpp` | **12** |
| 源码文件数 | `ls tests/test0*.cpp \| wc -l` | **12** |
| 函数定义数 | `grep -ho 'void test0[0-9][0-9](' tests/test0*.cpp \| sort -u \| wc -l` | **12** |
| 静态断言调用点 | `grep -hE '^\s*(ASSERT\|VERIFY)\(' tests/test0*.cpp \| wc -l` = 182；`tests/test.h` 辅助类 = 9 | **191** |
| **运行时实测（N′）** | `make tests` → `./testmain` | **0 failed / 230 passed** |

三口径（注册数=文件数=函数数）一致，无条件编译差额；运行时 230 > 静态 191 系 test001/005/010 等循环内重复触达。
上游入口 `make tests`（**无 `check` 目标**），`testmain` 无参跑全 12 项，任一失败即非零退出。
两次独立全量（变体 A / 变体 C2）读数一致。

### 鸿蒙特有测试（含 test_package 消费者用例，**不进上游分母**）

| 用例 | 断言数 | 实测 |
|---|---|---|
| `test_package/test.cpp`（C++ 消费者） | 11 | **11 passed, 0 failed**（静态与动态 SONAME 修复路径**双通**） |
| `test_package/test_uuidgen.sh`（CLI 消费者） | 4 | **4 passed, 0 failed** |
| **合计** | **15** | 适配后表 = 上游 12 + 鸿蒙行 15 |

`test.cpp` 覆盖：`sizeof(UUID)`、`UuidFromString` 无花括号/花括号/半开括号拒绝、`UuidToString` 花括号形态、
往返、`==`/`!=`、`XPLC_getServiceManager()` 非空、`getObject(XPLC_moduleLoader)` + `mutate<IModuleLoader>`
（走 `xplc/loader.cpp` 的 **dlopen/dlsym**，即鸿蒙目标的动态加载验证）。
`UuidToString` 输出**带花括号** `{...}`——按上游 `tests/test007.cpp` 断言口径，不套头文件注释（注释称不带花括号，与实现不符）。

### 关键验证命令与读数

```bash
# 双 profile 真实安装（W0 关②）
conan install <depcheck> -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
#   → uuid/2.40.1#e05bc8e1...:21b17f8b... Cache; Install finished successfully; rc=0

# configure 形态B（conan 默认无参）+ 形态D（--host=...linux-ohos）
#   → checking build system type... aarch64-unknown-linux-ohos; 两态 rc=0，
#     autoconf.h 3416B / config.mk / xplc.pc / uuid_types.h 全在，无 confstat 残留

# 注入 -I/-L 后 uuid 分支切换
#   → checking for uuid/uuid.h... yes ; checking for uuid_unparse in -luuid... yes ; with_uuid:=-luuid

# 全量 make + 上游测试
make -j1   → rc=0, errors=0；libxplc.a 227382B / libxplc-cxx.a / libxplc.so
make tests → rc=0；./testmain: 0 failed, 230 passed

# 消费者（静态 / 动态）
./test_xplc → 11 passed, 0 failed （两条路径均 rc=0）
./test_uuidgen.sh <bin>/uuidgen → 4 passed, 0 failed
```

## 交付物

| 文件 | 大小/数量 | 说明 |
|------|------|------|
| `lib/libxplc.so.0.3.13` + SONAME 链接 | 121280 B | 含 `libxplc.so.0.3.13-unstable` 修复链接 |
| `lib/xplc-0.3.13/libxplc.a` | 227382 B | 静态主库 |
| `lib/xplc-0.3.13/libxplc-cxx.a` | 53370 B | C++ 绑定 |
| `lib/xplc-0.3.13/libxplc.so` → `../libxplc.so.0.3.13` | symlink | 上游版本化 dev 链接 |
| `lib/xplc-0.3.13/libxplc_s.a` → `libxplc.a` | symlink | 上游别名 |
| `include/xplc-0.3.13/xplc/*.h` | **24 / 24** | 版本化 include 根 |
| `lib/pkgconfig/xplc-0.3.13.pc` | 1 | `Libs: -L${libdir} -lxplc -lxplc-cxx -ldl` |
| `bin/uuidgen` + `bin/uuidcdef` | 2 | 上游 CLI（uuidcdef 为符号链接） |

## 注意事项

1. **`configure rc=0 ≠ 成功`、`make install rc=0 ≠ 成功`**——本包实测踩到**两处**假绿（autoconf.h 全缺、24 头只装 1 个）。
   配方已把产物核对写成硬闸（`_verify_configure_outputs` / `_verify_build_outputs` / `_verify_install_outputs`），
   **采信轮与每轮构建后都必须核产物存在性**，不能只看 rc。
2. **`find` 无匹配仍 rc=0**——查产物时不能只用 `find ... && echo OK`，必须断言**计数**（本包头文件 24 是硬下界）。
3. `tc.cxxflags` 是 property（append 静默失效），`tc.extra_env` 在本 conan 版本不存在；两者都须用别的注入面。
4. pkg-config 旁路拿不到 `-DUNSTABLE`（`xplc.pc` 不带），非 conan 消费者需自行补。
5. `uuid.pc` 的 `Cflags` 与源码 include 形态不匹配（见问题表 #1），**不要用 `pkg-config --cflags` 喂给 xplc 的 uuid 探测**。
6. 手写 `Makefile` 用 `wildcard xplc/*.cpp` 解析源，**不支持 out-of-tree**，layout 必须 `src_folder="."` + `folders.build="."`。
7. 上游无 `shared/static` 开关（`default` 恒产 `.a`+`.so`），故配方**不声明 `shared` 选项**（声明了也不生效=误导）。
8. 知识增量 E705（C++11 窄化 vs C++17 移除特性的降档适用边界），见 `knowledge/drafts/DRAFT-E705-*`。
