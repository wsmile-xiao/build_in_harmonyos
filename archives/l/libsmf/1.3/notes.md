# libsmf 1.3 适配笔记

## 定位

libsmf 是 BSD-2-Clause 许可的 C 库, 用于读写 Standard MIDI File (`.mid`) 文件:
脉冲/时间透明换算、 tempo map 管理, 对外仅依赖 glib。上游由 Edward Tomasz
Napierala 维护, 1.3 发布于 2010-03-21, 官方发布页为 SourceForge
`libsmf/1.3/` (开发已迁移至 GitHub `nilsgey/libsmf` 镜像, 本次仍以官方
SourceForge 归档为唯一源码输入)。

产物: `lib/libsmf.a` (默认静态; `shared=True` 时为 `libsmf.so`)、
`include/smf.h`、`lib/pkgconfig/smf.pc`、`bin/smfsh` 交互式 MIDI shell。

## 关键适配

### 1. 显式 gnu 三元组绕过 2010 年版 config.sub (E007 家族)

实测 `config.sub` (30KB, 2010-03-21):
`aarch64-unknown-linux-gnu` 通过, `aarch64-linux-ohos` /
`aarch64-unknown-linux-musl` 均报 `machine not recognized`。
对策: `generate()` 显式传
`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。
副作用收益: 跳过 `config.guess` 探测 (E129 家族: HMDFS 上 mktemp
`dummy.c` 报 Permission denied), 且 `build == host` 让 configure 走原生
路径, 运行期探针可用。

### 2. `--with-readline=no` 关闭可选依赖

`configure.ac` 默认 `with_readline=check`, 会探测 `-lreadline -lncurses`
用于 `smfsh` 的花哨行编辑。本包显式关闭, 依赖闭包保持仅 glib,
避免为交互式 shell 装饰引入两条新依赖链。

### 3. E011 umask 与 HMDFS getcwd 双补丁 (代码内, 非 patches/)

- `build()` 把 `configure` 内 `umask 077` 改 `umask 022` (HMDFS 临时目录
  属主不可写, lame/鸡等包同法)。
- `build()` 前 `os.chdir(build_folder)` 并重设 `$PWD`, 规避 HMDFS
  `getcwd(2)` 失败导致 `ac_pwd` 校验 `working directory cannot be
  determined` (sipcalc/libclastfm 同法)。
- `make -j1` 单作业 (E074: 并行 make 撞 HMDFS jobserver fifo EPERM)。

### 4. 去 `.la` 文件

`package()` 删除 `lib/*.la`, Conan 自行管理链接, 与 lame 包一致。

## 上游测试审计

`libsmf-1.3.tar.gz` (545850 字节,
sha256 `d3549f15de94ac8905ad365639ac6a2689cb1b51fdfa02d77fa6640001b18099`):
顶层仅 `configure.ac / Makefile.am / src/ / man/`; `src/Makefile.am`
只定义 `libsmf.la` 与 `smfsh`, 无 `TESTS`/`check_PROGRAMS`/`check-local`;
`configure.ac` 无测试宏; 全树 `find -iname '*test*'` 仅命中 autoconf
生成脚本。`make check` 为 automake 空目标 (`check-am: all-am`),
执行 0 用例。结论 `upstream_tests_exist: false`, 真机输出
`HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0`。
详见 `test_package/MANIFEST.yml`。

## test_package 设计 (R34)

`test_smf.c` 8 断言, 全部调用真实 API, 覆盖创建→落盘→回读全链路:

1. `smf_get_version()` 非空
2. `smf_new()` 非空
3. `smf_track_new()` 非空
4. `smf_add_track()` 后 `number_of_tracks == 1`
5. `smf_event_new_from_bytes(0x90,60,100)` 非空且 `smf_event_is_valid`
6. `smf_track_add_event_seconds(track, ev, 1.0)` 后事件数 ≥ 1
7. `smf_save(smf, "hmbs_libsmf_test.mid") == 0`
8. `smf_load()` 回读非空且 `number_of_tracks == 1`, 附 `smf_decode()` 输出

编译期直链 `-lsmf` (非 dlopen), L1e 反向验证在编译/链接期即失败。
`test()` 另跑 `smfsh -V` 烟雾验证已安装 CLI。

## 依赖版本

- `glib/2.88.0.1` (`transitive_headers/libs`, 公开头 `smf.h` 含 `<glib.h>`)
  - 选用已发布版本而非 2.84 线: `2.84.0` 解析到 conancenter
    `pcre2/10.40` + `zlib/1.3.2` + `bzip2/1.0.8` CMake 链 (真机报
    `System is unknown to cmake` + 只读 `/tmp`); `2.84.0.1` 虽避开该链,
    其外部 `libffi/3.4.4` 旧 autotools 配方在预检 configure 报
    `/data/service/hnp/bin/bash: inaccessible or not found` (Error 127)。
    `2.88.0.1` 把 libffi 内建为 meson 子项目离线构建, 依赖闭包仅
    `pcre2/10.45` + `zlib/1.3.1.1.1.1`, 不再单独构建外部 libffi。
    先例: cassbeam 明确 `2.84.0` 仅 built 不可解析、`2.88.0` 已上传。
  - `generate()` 同时用 `PkgConfigDeps` 提供 `glib-2.0.pc`, 供
    `PKG_CHECK_MODULES` 发现; `test_package` 聚合顶层与 components 的
    include/lib, 兼容 2.88 组件式布局。
- 系统库 `m` (`pow`, Linux/OHOS 分支声明)

### 本轮真机失败修复 (2026-09-14, 第三轮, libsmf 自身 configure)

- 现象: 依赖已越过 libffi 断点 (`glib/2.88.0.1`), 本包 `configure` 仍失败:
  `.../b/configure: /data/service/hnp/bin/bash: inaccessible or not found`,
  `checking for aarch64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang`
  后 `configure: error: C compiler cannot create executables` (Error 77);
  平台诊断 `[readonly_tmp]`。
- 根因: `os.environ` 单通道被聚合 `conanbuild*.sh` 覆盖 (profile `[buildenv]`
  的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 与 `/tmp` 在 `self.run(env=conanbuild)`
  时胜出), 且 profile 钉死的 `/data/service/hnp/bin/clang` 在部分预检机缺失,
  conftest 链 (编译器临时文件回落只读 `/tmp`) 报 "cannot create executables"。
- 处理 (courier-unicode/2.6.0 已验证模式, 适配 libsmf): `generate()` 经
  `tc.environment()` 注入可写 TMPDIR/TMP/TEMP/TMP_DIR + 探测 shell
  (`_ohos_shell()` 文件存在性探测, HMBS `/bin/sh` 优先) 并落盘 `hmbs_shell`;
  `build()` 增加 `_patch_ohos_build_scripts()` (shebang 归一化 +
  烘焙 HNP bash 路径 scrub + `umask 077->022`), `_sanitize_ohos_env()` +
  `_override_conan_buildenv()` (改写磁盘 `conanbuild*.sh` 的 SHELL/TMPDIR 导出),
  `_ensure_ohos_compiler()` (conf 路径存在则零改动, 缺失则经 PATH 取
  `clang/clang++` 同目录兄弟, 仅覆盖 CC/CXX, 不碰 CFLAGS/LDFLAGS),
  另加 `$CC --version` 探针与 `config.log` 尾部转储供下轮诊断。
  gnu `--build/--host`、readline 关闭、`PkgConfigDeps`、静态/共享分支保持不变。

## 验证结果

- 现象: 切到 `glib/2.84.0.1` 后, 依赖 `libffi/3.4.4` 构建期失败
  (`src/configure[139]: /data/service/hnp/bin/bash: inaccessible or not
  found`, `autotools.configure()` Error 127); `readonly_tmp` 仍提示。
- 处理 (与首轮不同策略): `requirements()` 改到 `glib/2.88.0.1`
  (内建 libffi, 消除该外部构建节点); `build()` 沿用 TMPDIR 复用并把
  `SHELL/CONFIG_SHELL` 收敛到 HMBS 注入值 (默认 `/bin/sh`), 不再硬编码
  HNP bash; `test_package` 的 CC/shell 改经 PATH 解析, 同样不硬编码 HNP
  绝对路径; 另补 `PkgConfigDeps` 与 components 聚合以适配 2.88。
- 首轮修复 (bzip2/CMake 链) 回顾: `glib/2.84.0` -> `2.84.0.1` +
  TMPDIR 复用, 已使预检越过 bzip2 断点, 本轮在其基础上换线, 非重复修改。

### 本轮真机失败修复 (2026-09-14, 第四轮, 缺 pkg-config)

- 现象: 第三轮 shell/tmpdir/编译器修复已生效 (日志见 OHOS patch applied、
  shell=/bin/sh、clang 回退到 harmonybrew 且 PIC 检查全过), 新断点为
  `checking for pkg-config... no` 后
  `configure: error: The pkg-config script could not be found` (Error 1)。
- 处理 (与上轮不同策略, 非重复): 新增
  `build_requirements()` 声明 `tool_requires("pkgconf/3.0.5")`
  (gulkan/0.15.1、fcft/3.3.3、ekg2/0.3.1 先例; HMBS 仅注入
  cmake/make/ninja/python3, 真机 PATH 无系统 pkg-config); 保留
  `PkgConfigDeps` 继续提供 `glib-2.0.pc`, 由 pkgconf 提供可执行文件后
  `PKG_CHECK_MODULES(GLIB)` 即可发现。

### 本轮真机失败修复 (2026-09-14, 第五轮, PKG_CONFIG 接线)

- 现象: 第四轮 `tool_requires(pkgconf/3.0.5)` 已进依赖图
  (`pkgconf/3.0.5: Checking remote ohpcd`), 但 `configure` 仍报
  `checking for pkg-config... no` + `PKG_CHECK_MODULES(GLIB)` Error 1。
- 根因 (与上轮不同策略): ohpcd pkgconf 包只装 `bin/pkgconf`
  (配方显式断言无 `pkg-config` 别名), 而 2010 年版 `configure`
  只找 `aarch64-...-pkg-config` / `pkg-config` 文件名, PATH 上有
  `pkgconf` 也命中不了; 但 `pkg.m4` 支持 `$PKG_CONFIG` 覆盖
  (`ac_cv_path_PKG_CONFIG="$PKG_CONFIG"`)。
- 处理: 新增 `_resolve_pkg_config()` (conf `tools.gnu:pkg_config` 为文件
  则用, 否则取 build 域 pkgconf 包 `bin/pkgconf|pkg-config`, 回落 PATH),
  `generate()` 经 `tc.environment()` + `hmbs_shell` 存档导出 `PKG_CONFIG`,
  `build()/package()` 经 `_sanitize_ohos_env()` + `_override_conan_buildenv()`
  同步 `os.environ` 并改写磁盘 `conanbuild*.sh` 的 `export PKG_CONFIG`。
  仅新增构建域接线, 不改运行时闭包与测试口径。

### 本轮真机失败修复 (2026-09-14, 第六轮, E236 毒 .la)

- 现象: 第五轮 PKG_CONFIG 接线已生效 (PIC 检查全过, 编译 `smf_decode.c`
  等目标文件成功), 新断点在 `src/` 链接期:
  `sed: can't read //lib/libpcre2-8.la` +
  `libtool: link: '//lib/libpcre2-8.la' is not a valid libtool archive` +
  `make[2]: *** [Makefile:279: libsmf.la] Error 1`。
- 根因 (与上轮不同策略): 已发布 pcre2/glib/zlib 包内 `*.la` 的
  `libdir='//lib'` (打包时 `--prefix=/` 烤死); libtool 对每个 `-L` 目录
  优先探 `lib<name>.la` 再探 `lib<name>.a`, `PKG_CHECK_MODULES` 带入的
  `-L<conan pcre2 lib>` 命中毒 `.la` 后跟随烤死绝对路径, 与 E236 同源
  (bitlbee-facebook 笔记第 4 行同错, ezstream 注释 `libdir='//lib'` 同因)。
- 处理 (E236 scoped-la-free-static-archive-directory, 不删 conan 缓存,
  不走绝对 `.a` 进 LIBADD): 新增 `_prepare_la_free()` (复制全部 host 依赖
  `.a` 到构建私有 `la-free/`, 无 `.la`) + `_glib_la_free_flags()` (从实时
  依赖图聚合 `-I`/`-L`/`-l`, `-L<la-free>` 置首, 补 `-lm`), `generate()`
  经 `tc.environment()` + `hmbs_shell` 导出 `GLIB_CFLAGS/GLIB_LIBS`
  (pkg.m4 双变量齐置旁路, 毒 `-L` 永不到 libtool 命令行), `build()` 重建
  并同步 `os.environ` 兜底。`package()` 既有删自产 `*.la` 保持无 `.la` 出包。

### 本轮真机失败修复 (2026-09-14, 第七轮, LINK 顺序致旁路失效)

- 现象: 第六轮 la-free + `GLIB_CFLAGS/GLIB_LIBS` 旁路推送后, 真机复跑
  同错 (`sed: can't read //lib/libpcre2-8.la`, `Makefile:279 libsmf.la`
  Error 1, 构建目录哈希已变证明新配方已同步, 但断点未动)。
- 根因 (与上轮不同结论): automake 默认 LINK 把 `AM_LDFLAGS/LDFLAGS`
  排在 `LIBADD` (`$(GLIB_LIBS)`) 之前, 而 `AutotoolsDeps` 把全部依赖
  `-L` (含毒目录) 注入 `LDFLAGS`, 排在 `GLIB_LIBS` 的 `-L<la-free>`
  之前; libtool 按命令行 `-L` 顺序先探毒 `.la`, 故单靠 `GLIB_LIBS`
  旁路够不着。此外 la-free 只拷 `.a`, 而 glib 默认 shared,
  `-lglib-2.0` 在 la-free 无影子时同样回落毒目录。
- 处理 (与上轮不同策略, bookloupe/2.0 + cyrus-sasl/2.1.28 已合入先例):
  新增 `_sanitize_dependency_la()`, `build()` 中 configure/make 前删除
  host 依赖 `lib/` 下 stale `*.la` (仅元数据, 不碰 `.a/.so`, 逐文件打
  日志; 链接信息已由 `.pc` + `cpp_info` 提供); 此举与 `-L` 顺序无关,
  libtool 无 `.la` 可探即回落兄弟 `.a/.so`。配套收紧 la-free: 同步拷贝
  `.so*` (保留符号链接) 且 `GLIB_LIBS` 只带 `-L<la-free>`, 不再把毒
  目录作为回退 `-L` 追加。

### 本轮真机失败修复 (2026-09-14, 第八轮, package 期 install 垫片)

- 现象: 第七轮 `.la` 清理推送后, 真机编译链接已通过 (`.libs/libsmf.a`
  已生成), 断点推进到 `package()` (`autotools.install()`, line 513):
  `libtool: install: <runtime>/bin/install -c .libs/libsmf.a
  <pkg>//lib/libsmf.a` 后 `libtool: install: chmod 644 <pkg>//lib/libsmf.a`
  报 `chmod: cannot access ...: No such file or directory` +
  `Makefile:254 install-libLTLIBRARIES Error 1`。前两轮 (la-free 旁路、
  毒 `.la` 清理) 均针对 compile/link，已被本轮日志证实生效，不再重复。
- 根因 (新阶段新结论): `AC_PROG_INSTALL` 把 HMBS install 垫片绝对路径
  烤进各 Makefile 的 `INSTALL`；该垫片装不好 libtool 静态归档
  (拷贝未落盘即返回)，随后 libtool 固定执行的 `chmod 644` 因文件缺失
  ENOENT。同平台能力 (`install_shim=true, chmod=0`) 下 aircrack/1.7
  第四、五轮已踩过同类坑并合入 (`install -c -m 644` 遭 EX_USAGE 64 拒；
  多词 INSTALL 首词非 `/bin/sh` 会被 ltmain 误解析)。
- 处理 (与前两轮不同策略, 逐字复用 aircrack/1.7 已合入模式):
  新增配方内 `_INSTALL_SHIM` (POSIX sh, 忽略模式位, 文件走 `cp -f`,
  目录走 `mkdir -p`, 支持 `-d/-D/多源/单文件`)；OHOS `package()` 改走
  `make install DESTDIR=<pkg> INSTALL="/bin/sh <shim>"
  INSTALL_DATA='$(INSTALL)'` (`env=conanbuild`, 首词字面 `/bin/sh`
  命中 ltmain 特判；经 `sh` 调用故无需执行位，适配 chmod=0)。
  libtool 装完静态归档后的系统 `chmod 644` 对已存在文件无碍
  (pcre2/10.48 同静态安装无垫片通过为证)。

## 验证结果

```bash
# 本轮为配方准备轮 (Windows 环境, 不跑 conan)。
# 待 HMBS 真机预检: conan create libsmf/1.3 + test_smf 8 断言 + smfsh -V。
```

## 状态

工作树草稿, 未提交。待 HMBS 真机全部门禁通过后统一提交推送。

### 本轮真机失败修复 (2026-09-14, 第九轮, test_package Requirement.name)

- 现象: 第八轮 install 垫片推送后, 真机 compile/package 已过
  (`.libs/libsmf.a` 生成, package 断点已越过), 新断点在
  `Testing the package: Building`: `test_package build() line 45
  if _ref.name == "libsmf": AttributeError: 'Requirement' object has no
  attribute 'name'` (conan 2.30)。
- 根因 (新阶段新结论, 与前八轮 compile/link/package 均不同):
  Conan 2 `self.dependencies.items()` 产出 `(Requirement, Dependency)`,
  包名在 `Requirement.ref.name` (及 `Dependency.ref.name`), Requirement
  本身无 `.name`。test_package 直接 `_ref.name` 故崩溃; 主配方三处
  `getattr(_ref, "name", "")` 未崩溃但恒返回空, 致 `pkgconf` 过滤永不命中。
- 处理 (与前轮不同策略): test_package 改经 `_ref.ref.name` /
  `_d.ref.name` 双探提取包名后再比对 `libsmf`; 主配方新增
  `_req_name()` 静态助手并在 `_prepare_la_free` /
  `_glib_la_free_flags` / `_sanitize_dependency_la` 三处复用, 恢复
  `pkgconf` 过滤。测试口径与标记不变 (8 断言 + no_tests/0)。

### 本轮真机失败修复 (2026-09-14, 第十轮, smfsh PATH)

- 现象: 第九轮 Requirement.name 修复已生效 (test_smf 8/8 通过,
  双标记均已输出 `passed:true` / `no_tests`), 新断点为额外烟雾项
  `RUN: smfsh -V` 报 `/bin/sh: smfsh: inaccessible or not found`
  (Error 127) 并经 `raise ConanException` 致整体失败。
- 根因 (新阶段新结论, 与上轮 Python 属性崩溃不同):
  裸 `smfsh` 依赖 conanrun PATH 接线, 但预检 runenv 未将其解析;
  文件本身已随 `make install` 落盘于包 `bin/` (前轮 install 垫片已证实)。
- 处理 (与上轮不同策略, 非重复): 主配方 `package_info` 显式声明
  `bindirs=["bin"]`; test_package 改经 `libsmf.package_folder/bin/smfsh`
  (+ 声明 bindirs + PATH 回落) 解析绝对路径后带引号执行
  `"<abs>" -V` (仍 `env=conanrun`, 缺失仍抛错, 非静默跳过)。
  8 断言与双标记口径不变。
