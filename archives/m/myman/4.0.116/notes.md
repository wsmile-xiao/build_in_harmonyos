# myman 4.0.116 适配笔记

## 编译环境

- 构建系统：manual（simple.mk 编译单元手写命令 + vendored autotools X11 栈）
- 编译日期：2026-09-12
- 编译器：clang（HarmonyOS PC 真机 /data/service/hnp 工具链，经 HMBS 注入的 compiler_executables 绝对路径获取，不裸用 shell 环境变量）
- 状态：built（PR 阶段尚未 release upload，真机预检待 HMBS 后台执行）
- 任务分支：feat/myman-4.0.116（基于 upstream/main a675263b9 切出）

## 版本说明

- 任务版本 4.0.116 在上游 myman 仓库中无对应 tag。经审计上游最新发布仍为 2009-10-30 快照（myman-wip-2009-10-30.tar.gz，包内 VERSION 为 0.7.1），SourceForge 文件列表与 Repology 版本表均无 4.x 系列。
- 本配方遵循任务目录要求取版本号 4.0.116，源码复用官方 2009-10-30 快照（与已合入的 archives/m/myman/2009-10-30 同源同 sha256），构建逻辑与已验证配方一致。
- 上游主页：https://myman.sourceforge.io/；源码：https://downloads.sourceforge.net/project/myman/myman-cvs/myman-cvs-2009-10-30/myman-wip-2009-10-30.tar.gz；sha256：bf69607eabe4c373862c81bf56756f2a96eecb8eaa8c911bb2abda78b40c6d73（与 Homebrew 公开值一致）。

## 编译步骤

1. 同步上游 main 并创建分支 feat/myman-4.0.116；复制已合入的 2009-10-30 配方为 4.0.116，仅改配方版本号与文档，源码 URL 与 sha256 保持官方值不变。
2. 构建流程（与 2009-10-30 完全一致，复用其已过门禁的路径）：
   - source() 下载 myman 主包 + PDCurses 3.4 + 7 个 X11 库（xtrans 1.6.0、libICE 1.1.1、libSM 1.2.4、libXt 1.2.1、libXmu 1.1.4、libXpm 3.5.19、libXaw 1.0.16），整理 xtrans 的 X11/Xtrans 子目录结构。
   - build() 先改写各 configure 的 pwd 判定与 umask（HMDFS getcwd 兜底）及 libXt RAWCPP 探针；按依赖序 vendored 构建 6 个 X11 库到 staging 前缀（--build/--host 取相同三元组跳过平台检测，PKG_CHECK_MODULES 逃逸跳过 pkg-config），物化 .so 实体文件；构建 PDCurses 静态库 libXCurses.a（拷贝 curses.h 为 xcurses.h）；按 simple.mk 编译单元手写编译 src/myman.c + src/utils.c + src/logic.c + mygetopt/mygetopt.c（-DXCURSES -DMYGETOPT，不定义 HAVE_CONFIG_H），链接 -lXCurses -lXaw -lXmu -lXt -lXpm -lSM -lICE -lXext -lX11 -lm，rpath $ORIGIN。
   - package() 安装 myman 到 bin/、vendored 6 库 SONAME 命名随包、chr/spr/lvl 数据到 share/myman/，全部 ELF 经 binary-sign-tool 自签。
3. 补丁 patches/0001-myman.c-fix-xcurses-argc-argv-undeclared.patch（与 2009-10-30 同文件）：修复上游 XCurses 路径 myman(void) 引用未声明 argc/argv 的编译错误，改用 main() 存入的文件级全局；无平台宏，R8 合规。
4. 真机验证交由 HMBS 后台统一执行；本轮不 commit、不 push。

## 上游测试审计

- 根 Makefile 与 simple.mk 均无 test/check 目标（grep 确认），源码树无 tests/ 目录：上游无自动化测试套件。
- test_package/MANIFEST.yml 已写入 upstream_tests_exist: false 与非空 upstream_test_audit；test_package/conanfile.py 的 test() 在真实执行后打印 status no_tests 的 HMBS_UPSTREAM_TEST_RESULT。
- test_package 采用无头真实执行被测二进制：myman -k（输出 keystroke commands 后 exit 0，不初始化显示后端）+ myman -L（版权信息）+ myman -h（Usage），discovered=3，由 test_myman.sh 真实计数并打印 HMBS_TEST_PACKAGE_RESULT。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务版本 4.0.116无上游 tag | 上游最新仍为 2009-10-30 快照 | 复用官方快照源码与校验值，版本号遵循任务要求，并在配方 docstring、manifest、notes 与 PR 补充说明中显式声明映射关系，不伪造 URL/sha256 |
| 2 | manifest.yaml 批量替换误改源码 URL | 全局字符串替换把 2009-10-30 改成 4.0.116 | 已回改 source.url 为官方 2009-10-30 地址并与 conandata.yml 交叉核对一致 |
| 3 | MANIFEST.yml 出现重复 upstream_test_audit 键 | 守则要求的新字段与既有详细审计块同名 | 详细块改名为 upstream_test_audit_detail，保留证据清单 |
| 4 | 真机 configure 报 /data/service/hnp/bin/bash inaccessible (exit 127) | profile buildenv 注入的 CONFIG_SHELL/SHELL 指向 OHOS 系统 bash，其在 HMDFS 上 getcwd 失败（DRAFT-6487 同根因） | build() 全局 + _build_vendored_lib/_build_pdcurses 内联覆盖 CONFIG_SHELL/SHELL=/bin/sh，并用 /bin/sh 显式解释 configure；make 调用同步加前缀 |
| 5 | X.Org 官方站抖动/不可达（CI 已知） | xorg.freedesktop.org 单源无回退 | conandata.yml 7 个 X11 库 url 改为有序列表：3 个 CI 同款镜像在前、官方源保留最后，sha256 不变；SourceForge 两项无可用镜像映射，保留原值 |
| 6 | 真机预检 compile 失败：vendored libXpm 处 `checking for pkg-config... no` + `configure: error: pkg-config not found`（libICE/libSM/libXt/libXmu 均已编过） | 真机/CI 无 pkg-config 二进制；libXpm 3.5.19 的 configure 由新版 xorg-macros 生成（XORG_DEFAULT_OPTIONS/XORG_ENABLE_UNIT_TESTS/XORG_WITH_GLIB），二进制缺失即硬失败，XPM_* 逃逸救不了；旧库 configure 无此硬性要求故此前未暴露。libXaw 1.0.16 同代，同样受影响 | conanfile 新增 `_ensure_pkg_config_shim()`（build() 最先调用）：在 build_folder 下写最小 `pkg-config` shim 并前置 PATH + 导出 PKG_CONFIG；shim 仅让存在性/版本探测通过，其余模块查询一律失败 → SXPM 演示工具与 glib 单元测试走文档化 fallback 自动关闭，必需 XPM 仍走 XPM_CFLAGS/XPM_LIBS 逃逸（结果真实不伪造）；libXpm 另加 `--disable-unit-tests`（configure.ac 含 XORG_ENABLE_UNIT_TESTS 的实证选项） |
| 7 | 真机预检 compile 失败：`can't create temporary file /tmp/shgsbfzj.tmp: Read-only file system`（平台诊断 readonly_tmp，configure 阶段） | OHOS /tmp 为只读挂载，autoconf/configure 的 mktemp 分支与 conan get() 的 tempfile 在 TMPDIR 未钉住时回退到 /tmp；本配方此前未设置 TMPDIR/TMP/TEMP（build/_build_vendored_lib/_build_pdcurses 均无覆盖） | conanfile 新增 `_writable_tmpdir()`（HMBS_AUTOCONF_MKTEMP_FALLBACK 路径优先，再 HMBS_TMPDIR/TMPDIR/TMP/TEMP，逐个 makedirs+mkstemp 可写探测，回退 build_folder/tmp；只换临时根，不动测试）与 `_pin_writable_tmpdir()`；source()/build() 入口先钉住并 export，_build_vendored_lib/_build_pdcurses 内联透传 `TMPDIR/TMP/TEMP` 到 configure/make 命令行（os.environ 继承双保险，c-kermit/courier-unicode 同款） |
| 8 | 真机预检 compile 失败：PDCurses 处 `checking for x86_64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang` 后 `configure: error: C compiler cannot create executables`（同 build 内 6 个 vendored 库已全部编过） | PDCurses 的 configure 命令行显式追加了 `CC=<conf 绝对路径>`，而 6 个 vendored 库均不传 CC、走 PATH 自动探测即通过；显式 CC 与旧 configure 的 host 前缀探测交互导致 conftest 链接失败（xeyes #27978 同类现象为工具链 PATH 缺失，本轮 PATH 已含 /data/service/hnp/bin，故锁定为多余的显式 CC 传参） | `_build_pdcurses()` 去掉 configure 命令行的 `CC=...` 传参，与 `_build_vendored_lib` 对齐走自动探测（`_prepend_toolchain_path` 的 PATH 前置 + profile buildenv 的 CC 保持不变）；另对 configure 加 try/except，失败时把 `config.log` 尾部 80 行打到日志便于下一轮直接定位；`_build_myman` 的直编仍用 `_cc()` 不变 |
| 9 | 真机预检 test_package 失败：test_myman.sh[20]/[23] 报 inaccessible or not found、[104] 报 unmatched if（build/package 已过，二进制已链接成功） | test_myman.sh 为 CRLF 换行（113 行全含 CR）：空行 CR 被 ash 当命令执行致 20/23 报错，then/fi 带 CR 致条件块无法闭合（104 行）。与 readonly_tmp 无关（构建期 TMPDIR 已钉住，6 vendored 库+PDCurses+myman 均编过） | test_myman.sh 转 LF（内容不变，if/fi 配平 11/11）；顶层 .gitattributes 加本文件 text eol=lf 防 Windows 检出回退（沿用 acpi-override 同款先例）；补丁不动（build 已证明可应用） |

## 依赖版本

- conan 依赖（ohpcd 已发布 OHOS armv8 binary）：libx11/6.4.0、libxext/6.4.0（transitive_headers/transitive_libs）、xorgproto/2025.1（transitive_headers）、libxcb/1.16（run=True）、libxau/1.0.11（run=True）。
- vendored（X.Org 官方源，配方内构建）：xtrans 1.6.0、libICE 1.1.1、libSM 1.2.4、libXt 1.2.1、libXmu 1.1.4、libXpm 3.5.19、libXaw 1.0.16、PDCurses 3.4（libXCurses.a）。
- HMBS 注入能力复用：SHELL/CONFIG_SHELL、TMPDIR、tools.build:jobs=1、HMBS_CMAKE/HMBS_MAKE/HMBS_NINJA/HMBS_PYTHON3、capability 诊断；不为本库重新发明环境探测。

## 验证结果

```bash
# 本轮为工作树准备轮，真机预检由 HMBS 后台统一执行，待下一轮回填
# 预期命令：conan create（经 HMBS 预检流水线，含 test_myman.sh 3 用例 + 上游 no_tests 声明）
# HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT 以真机日志为准，本轮不猜测数字
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/m/myman/4.0.116/conanfile.py | 主配方（version 4.0.116， manual 构建） |
| archives/m/myman/4.0.116/conandata.yml | 官方源码 URL + sha256 + 补丁声明 |
| archives/m/myman/4.0.116/manifest.yaml | 版本级元数据（status built） |
| archives/m/myman/4.0.116/notes.md | 本文件 |
| archives/m/myman/4.0.116/patches/0001-*.patch | XCurses argc/argv 修复 |
| archives/m/myman/4.0.116/test_package/ | conanfile.py + MANIFEST.yml + test_myman.sh |

## 注意事项

- 不要把真机地址、rsync/ssh 细节写入 PR 正文；正文统一写 HarmonyOS aarch64 环境实测。
- 本轮严禁 commit/push/创建 PR/调用 GitCode 写接口/写 .hmbs/pr.json；工作树保持未提交，等待 HMBS 真机预检。
