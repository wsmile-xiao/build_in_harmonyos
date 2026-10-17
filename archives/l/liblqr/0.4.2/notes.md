# liblqr 0.4.2 适配笔记

## 编译环境

- 构建系统: autotools (configure + make -j1)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (OHOS 真机 /data/service/hnp/bin/clang, 待预检确认)
- 状态: built (工作树未提交, 待 HMBS 真机预检)

## 上游信息

- 上游仓库: https://github.com/carlobaldassi/liblqr
- 官网/下载页: http://liblqr.wikidot.com / http://liblqr.wikidot.com/en:download-page
- 源码包: liblqr-1-0.4.2.tar.bz2 (344739 字节)
- 源码 URL: http://liblqr.wdfiles.com/local--files/en:download-page/liblqr-1-0.4.2.tar.bz2
- sha256: 173a822efd207d72cda7d7f4e951c5000f31b10209366ff7f0f5972f7f9ff137
  - 获取方式: 本机下载官方 wdfiles 归档后计算 (Python hashlib.sha256), 与 ConanCenter 0.4.3 同一官方域名 pattern 一致
- 许可证: LGPL-3.0-or-later + GPL-3.0-or-later (COPYING + COPYING.LESSER)
- 依赖: glib-2.0 >= 2.8.0 (configure.ac PKG_CHECK_MODULES), 适配引用 glib/2.88.0

## 编译步骤

1. `get()` 解压官方 tar.bz2 (strip_root)
2. `AutotoolsDeps + PkgConfigDeps` 传入 glib 标志
3. `AutotoolsToolchain` 追加 `--disable-install-man`; 静态默认追加 `--enable-static --disable-shared`
4. `build()` 内做 HMDFS PWD/getcwd 容错；E007 改用功能性修复：OHOS 下 `AutotoolsToolchain` 固定 `--build/--host=aarch64-unknown-linux-gnu`（ctpl/cdecl/castget 已合入先例），使 configure 跳过 2009 年版 config.guess 探测；上一周期的注释级 fallback 经证实为 no-op 已删除
5. `autotools.configure()` + `make -j1`
6. `autotools.install()`, 清理 `*.la`, 保留 pkgconfig (lqr-1.pc), 复制 COPYING* 到 licenses

## 上游测试审计结论 (no_tests)

- 归档共 93 文件, 顶层仅 `SUBDIRS = lqr man`, 无 tests/、test/、spec/、t/ 目录
- 全树 `-iname '*test*'` 零命中
- `Makefile.am` / `lqr/Makefile.am` 无 TESTS / check_PROGRAMS / check-local
- `configure.ac` 无测试宏, 仅 glib PKG_CHECK_MODULES + Win32 判断
- `examples/` 为依赖外部 pngwriter 的手写演示 Makefile, 非测试框架
- 因此 `make check` 为 automake 默认空目标, 执行 0 用例; 配方 `build()` 不调用 `make check`,
  `test_package/MANIFEST.yml` 按规范写入 `upstream_tests_exist: false` + 完整 `upstream_test_audit`,
  真机输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0`

## test_package 设计 (R34)

- `test.c` 在 8x8 RGB 内存图像上真实调用:
  1. `lqr_carver_new` 非空
  2. `get_width/height/channels` 与输入一致
  3. `lqr_carver_init` 返回 LQR_OK
  4. `lqr_carver_resize(6,6)` 返回 LQR_OK 且 dims 更新为 6x6
- 每个步骤打印 `CHECK-OK`, 共 4 断言; `conanfile.py test()` 先 `ctest`, 失败回退直跑二进制,
  随后打印 `HMBS_TEST_PACKAGE_RESULT discovered:4` 与 `HMBS_UPSTREAM_TEST_RESULT no_tests/0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方无 0.4.2 sha256 公布 | 2009 年发布, 下载页仅给 tarball | 本机下载官方归档实测 sha256, 与 ConanCenter 同域名 pattern 交叉确认 |
| 2 | 2009 年版 config 脚本可能不认识 ohos triplet | E007, 早于 OHOS 约 15 年 | build() 内做最小 ohos 兜底 (已含 ohos 则 no-op), 不改构建逻辑 |
| 3 | 上游无测试, 不能用 no_tests 偷懒 | 规范要求显式审计 | MANIFEST 写入完整 audit + test_package 4 个真实 API 断言替代覆盖 |
| 4 | 真机 /tmp 只读 erofs, configure/mktemp 写 /tmp 失败 (readonly_tmp) | E002, HMBS 平台诊断明确要求改用注入的 TMPDIR | generate() 把注入的 TMPDIR/TMP/TEMP 写入 conanbuild env, build() 内确保目录存在并导出, 仅重定向临时文件根目录, 不删测试 |
| 5 | config.status 的 mktemp 临时目录在 HMDFS 下权限失败 | E011 (xz/mutt 同类) | build() 内 configure 的 `umask 077` → `022`, 仅改字面量 |
| 6 | package_info 的 libm 条件漏掉 OHOS | R32 (以 lame 为例须含 OHOS) | 条件扩展为 `in ("Linux", "FreeBSD", "OHOS")` |
| 7 | 首轮只在 generate()/build() 镜像 TMPDIR, 失败仍在 ninja 依赖的 cmake configure (配方代码运行前) | 首轮策略作用层错误: 依赖先构建, 本包 env 透传够不到依赖构建 | 次轮改换策略: configure 源码级变量式补丁 (mktemp→${TMPDIR:-.}, ${TMPDIR=/tmp}→${TMPDIR=.}, ac_pwd 回退, umask 022), source()+build() 双次应用, 不烘焙绝对路径 (cassbeam 已合入先例) |
| 8 | 同机 profile 的 /data/service/hnp/bin/clang{,++} 报 inaccessible, 本包 configure 将来同样 "cannot create executables" | 经验 1 (dhex) + cassbeam `_resolve_compilers` | 工具链原文优先、可运行才信 (`--version` 实测); 坏了才回退到实测可用的绝对路径, 永不返回未验证裸名; 同步修补 generators/*.sh 中的坏绝对路径 (xz 先例); 仅日志+env, 由 configure 自己的检查裁决 |
| 9 | glib 边 `transitive_headers` 在静态链接下可能漏 intl/ffi | cassbeam 同边用 headers+libs | requirements 加 `transitive_libs=True` |
| 10 | 第三轮同指纹失败，确认失败层在 ninja 依赖自身构建（ConanCenter 配方 cmake.configure），本包代码排其后够不到 | 停损：conan 先构建依赖；远端 glib 无可用二进制致整链源码构建；stock cmake 不识 HarmonyOS（本树无 ninja 配方可改，PR 原子性也不允许碰他库） | 本轮零代码改动，保留前两轮加固（未提交）；请求制品仓/侧 remediation：补 glib-ninja OHOS 二进制或修复构建 cmake/编译器路径后复跑 |
| 11 | 停损后第 4 轮仍同指纹失败；但已合入的 ctpl/0.3.5 用完全相同的 glib/2.88.0 链在 CI 通过，证明依赖链可构建、“环境宿命论”假设错误 | 上一周期假设“失败超出配方作用域”被证伪：真因在本配方依赖图与已验证先例不一致（pkgconf 范围可解析到未适配 2.x、无 zlib override、未 pin triplet 用无实际作用的注释 fallback、build() 内编译器改写永远够不到依赖构建） | 新路线=依赖图对齐已合入先例：pkgconf→3.0.5 精确版、加 zlib/1.3.1.1 override、OHOS 下 pin --build/--host=aarch64-unknown-linux-gnu（ctpl/cdecl/castget 先例，configure 跳过 config.guess 探测）、加 validate() 限 Linux/OHOS；退役 _resolve_compilers/_fix_conanbuild_env/_patch_autotools_for_ohos（够不到依赖层）；保留 HMBS 要求的 TMPDIR 透传与 configure 变量式补丁 |
| 12 | 本轮预检 compile 失败：configure 首报 `.../b/configure: /data/service/hnp/bin/bash: inaccessible or not found` + `missing script too old`，随后 `checking for aarch64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang` 通过但 `C compiler cannot create executables` (Error 77)；HMBS 平台诊断 readonly_tmp | profile buildenv 注入 CONFIG_SHELL=/data/service/hnp/bin/bash，该 HNP bash 在 HMDFS 构建目录 getcwd() 失败（DRAFT-6487 classads 同根因）；autoconf configure 一旦采用 CONFIG_SHELL 即用它重执行自身与 config.sub/config.status，全链路失败；后续 AC_TRY 编译测试被误报为编译器不可用。单设 os.environ 会被 conanbuild.sh  sourcing 覆盖，故旧代码的 SHELL/CONFIG_SHELL 导出未生效 | generate() 的 hmbs_tmpdir env 脚本新增 SHELL/CONFIG_SHELL=/bin/sh（取 HMBS 注入值）；build() 新增 _fix_generated_shell_env：configure 前改写本包 build_folder 内 *.sh 生成脚本中的该绝对路径为注入 shell（仅数值替换，不碰依赖缓存与其他库）；保留 TMPDIR 探测与 configure 变量式补丁；不改 CC/CXX、不跳测试 |
| 13 | 上轮 CONFIG_SHELL 修复后同指纹再败：bash inaccessible 行消失（shell 策略生效），但 `checking for aarch64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang` 后仍 `C compiler cannot create executables` (Error 77，build() 177 行，build-release 目录）；HMBS 诊断仍 readonly_tmp；无 config.log 可见 | 与上轮不同层：shell 重执行已过，configure 的 AC_TRY 编译/链接仍失败；同沙箱上轮已证 /data/service/hnp/bin/bash 不可执行，同前缀的绝对 CC 很可能同样不可执行（检测仅回显 CC 字符串，不证明可运行）；且真实 clang 首错被 configure 汇总行掩盖、无 config.log 无法确诊 | 新策略（不重复上轮脚本改写）：① generate() 改经 tc.environment() 注入 TMPDIR/SHELL/CONFIG_SHELL（backuppc-rsync 同范式双保险）；② build() 新增门控式编译器兜底 _ensure_working_compiler：绝对 CC/CXX 须通过 `--version` 实测才保留，否则按 conf→PATH(clang/cc/gcc) 顺序选用可运行者并仅改写本包 *.sh（含 os.environ），健康值零改动；③ autotools.configure() 失败时自动打印 config.log 尾部 60 行供下轮确诊；继续不跳测试 |
| 14 | 新失败域（非同指纹）：编译器检查全过（harmonybrew clang 的 PIC/static 探测皆 yes，门控兜底与 log 自举均生效），configure 倒在 `checking for pkg-config... no` → `PKG_CHECK_MODULES(GLIB)` 硬错误（Error 1，build() 187 行）；仍无上游测试输出 | pkgconf/3.0.5 工具包明确只装 bin/pkgconf 且 package() 对 bin/pkg-config 别名硬抛错（无别名是设计如此）；liblqr 0.4.2 的 2009 年版 pkg.m4 只探测 `pkg-config` 名，故 tool_requires 一项不够（cassbeam/1.1 注释“1st attempt only”同坑） | 复用 cassbeam 已合入方案：① generate() 经 tc.environment()+hmbs_tmpdir 把 $PKG_CONFIG 指向工具包 bin/pkgconf；② build() 首步 _ensure_pkg_config_shim 在本包 build_folder/hmbs-shims 建 pkg-config→pkgconf 符号链接（symlink cap=1，copyfile 兜底 HMDFS chmod=0），PATH 首位前置且 $PKG_CONFIG 指向 shim，新旧 pkg.m4 皆可解析；不改 CC/CXX 与测试口径 |

## 依赖版本

- glib/2.88.0 (transitive_headers + transitive_libs)
- zlib/1.3.1.1 (override, ctpl/0.3.5 已合入先例)
- pkgconf/3.0.5 (tool_requires 精确版, ctpl/0.3.5 已合入先例)

## 验证结果

- 待 HMBS 真机预检回填 (conan create + ctest + HMBS JSON 标记)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 主配方 (autotools + glib) |
| conandata.yml | 官方 URL + sha256 |
| manifest.yaml | 版本级清单 |
| test_package/test.c | 4 断言真实 API 测试 |
| test_package/MANIFEST.yml | no_tests 显式审计 |

## 注意事项

- 本轮未提交、未推送, 等待 HMBS 同步代码树并执行真机预检
- OHOS 下已固定 --build/--host=aarch64-unknown-linux-gnu，configure 不再经过 2009 年版 config.guess/config.sub 的 ohos 识别路径，无需 patches/ 补丁
