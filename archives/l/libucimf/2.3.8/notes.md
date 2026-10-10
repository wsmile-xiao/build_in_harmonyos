# libucimf 2.3.8 适配笔记

## 编译环境
- 构建系统: autotools（上游预生成 configure，autoconf 2.59 时代）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（本机原生构建 host=build=OHOS/aarch64，profile: ci/conan/profiles/ohos-aarch64）
- 状态: built（conan create 本地复现通过）

## 编译步骤

走 Conan 驱动（模式 A 变体）：conanfile.py 直接声明依赖
（freetype/2.14.3 + fontconfig/2.18.1.1 + libltdl/2.6.0，全部
transitive_headers/transitive_libs），generate() 同时挂
AutotoolsToolchain + PkgConfigDeps + AutotoolsDeps 三个生成器：

- PkgConfigDeps 产出 freetype2.pc / fontconfig.pc 供 configure 的
  PKG_CHECK_MODULES 探测（PKG_CONFIG_PATH 经 conanbuild env 注入）；
- AutotoolsDeps 产出 CPPFLAGS/LDFLAGS 供 AC_CHECK_LIB(ltdl, lt_dlopen)
  链接探测命中 libltdl 包。

configure 参数仅 --enable-static --disable-shared（R26 静态默认），
`make -j1`（上游 2007 年代码，并行 make 有 depcomp 竞态风险）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 可研阶段（09-27 #40）误判依赖含 ncurses/libmagic | 仅凭发行版包依赖推断 | 审计 configure.ac 后确认硬依赖仅 libltdl（AC_CHECK_LIB）+ freetype2/fontconfig（PKG_CHECK_MODULES），与 ncurses/libmagic 无关 |
| 2 | src/ucimf.cpp 无条件 include linux/kd.h、linux/keyboard.h、linux/input.h | Linux 控制台 ioctl 常量 | 实测 OHOS SDK sysroot（ohos-sdk_26.0.0.18/native/sysroot/usr/include）三个头文件齐全，无需补丁 |
| 3 | display/lrmi.c 是 x86 实模式接口（asm/vm86.h），aarch64 必挂 | x86-only 代码 | 整文件被 `#ifdef USING_VGA` 包裹且工程从不定义 USING_VGA → 空编译单元，无需补丁；vgadev.cpp/fbvgaplanes.cpp 同理 |
| 4 | display/fbdev.cpp 的 `#if defined(linux)` 是否会引入 linux/fb.h | OHOS clang 对 aarch64-linux-ohos triple 预定义 linux/__linux__（`clang -dM -E` 实测） | sysroot 有 linux/fb.h，正常编译；运行期 TryOpen() 打不开 /dev/fb* 优雅返回 FAILURE，GraphPort 全部方法有 gdev==0 保护 |
| 5 | 测试设计：ucimf_init() 在无字体环境崩溃 | fontconfig 无字体时 FcFontSort 空集 → Font::instance()（DEFINE_INSTANCE 宏）返回 NULL → ucimf_init 内 `Font::instance()->height()` 空指针解引用；sample/console01 同样会崩 | test_package 改走无头确定性路径：ucimf_process_raw(KEY_LEFTCTRL)（完整 keycode→keysym→term-string 管线，ioctl 在管道环境以 ENOTTY 优雅失败）+ ucimf_switch 透传契约；均不触碰 cwm/imf 单例（对照 src/ucimf.cpp L326-420/L255-302 审计） |

## 源码修改

无补丁（patches: {}）。平台相关代码（linux/kd.h、linux/fb.h、USING_VGA
块）经审计在 OHOS sysroot 下天然可编译，无需任何 #ifdef __OHOS__ 改动。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| freetype | 2.14.3 | 字形光栅化（font/font.cpp，FT_New_Face/FT_Init_FreeType） |
| fontconfig | 2.18.1.1 | 字体发现（FcFontSort/FcFontRenderPrepare） |
| libltdl | 2.6.0 | IMF 输入法模块运行期 lt_dlopen（IMF_MODULE_DIR=libdir/ucimf/） |

## 上游测试清点（R51 三步法 第 1 步）

对 2.3.8 tarball 全部 Makefile.am（顶层/display/font/src/sample/man）grep
`check_PROGRAMS|TESTS|check-local` 均无命中 —— 上游没有注册任何测试目标，
`make check` 为空跑。sample/ 的 console01/console04 是 noinst 演示程序
（调用 ucimf_init()，见问题 #5，无法 headless 运行），不计为测试。
上游可运行测试数 = 0，通过率记 0/0。测试三步法第 2 步（实际运行）：
上游无测试可运行；第 3 步：PR 如实回填 0/0。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify libucimf 2.3.8
# conan create（OHOS/aarch64 profile）通过；test_package 消费者测试 6/6 断言全过
```

## 注意事项

- 本库运行语义是 Linux framebuffer 文字控制台的 CJK 输入法（fbterm/zhcon
  配套）。OHOS 无 framebuffer 控制台场景 → 能干净编译链接并被下游引用，
  但运行期无显示/输入后端（libucimf 同 yell 类：编出即交付，无本地消费者）。
- 包内容：libucimf.a/.so、ucimf.h + imf/*.h、libucimf.pc、
  ucimf.conf（sysconfdir）、ucimf_start/ucimf_keyboard（bin 下的 shell 脚本）。
- 下游若做 IMF 模块（如 ucimf-chewing/openvanilla），模块需安装到
  libdir/ucimf/ 才能被 lt_dlopen 扫描到。
- 消费者引用：`self.requires("libucimf/2.3.8")`，链接目标
  libucimf::libucimf（CMakeDeps）或 pkg-config libucimf。
---

**编译结束**: 2026-09-28 01:39
**最终状态**: built

## CI 修复记录（2026-09-28，PR #13388 build #63227）

CI（OpenHarmonyPCDeveloper-CI-005）在 conan-build-test 步骤失败：
`./config.status[1040]: can't create ./confoCfenm/subs1.awk: Permission denied`
→ `config.status: error: could not setup config files machinery`。

根因：autoconf 2.69 的 config.status 以
`(umask 077 && mktemp -d "./confXXXXXX")` 在 build 目录创建 **mode 700**
临时目录。CI worker 进程 uid=100，而 HMDFS /storage 卷上新文件的属主被映射为
20001006，uid 100 对该目录既无写权限、也无 chmod 权限（chmod 需属主身份），
且其 uid 不在属主位 → 目录内写文件 EACCES。
configure 阶段不写 $tmp 内文件所以能跑完，config.status 一写即炸。
依赖（libltdl/freetype2/fontconfig）在 CI 全部 check 通过，非依赖问题。

修复（v4）：补丁 0005-configure-tmpdir-group-perms.patch。历史：
v1（chmod 0770）在 build #63278 失败（属主映射下 chmod 也 EPERM）；
v2（改到 ${TMPDIR:-.}）在 build #63288 失败——CI 实际构建进程的 TMPDIR 是
/storage/Users/currentUser/.cache/tmp（HMDFS 卷）；
v3（候选探测，探针用 `: > .writable 2>/dev/null`）在 build #63314 失败——
两个新坑：① `:` 是特殊内建，mksh 下特殊内建重定向失败会整个 shell 退出，
fallback 无机会执行；② 重定向失败发生在 2>/dev/null 生效前，报错照样可见
（can't create /storage/.../.cache/tmp/confmCljEk/.writable: Permission denied）；
且 /data 候选目录对 buildbot worker（另一 app uid）很可能全不可写。
v4 方案：探针写入放进子 shell `(echo probe > .writable) 2>/dev/null`（失败只影响
子 shell），候选 ${TMPDIR} → /data/storage/el2/base/cache → /data/cache →
/data/local/tmp；全部失败后兜底在 build 目录用 `umask 000 && mkdir` 建出 0777
子目录——HMDFS 属主映射下 777 目录任何 uid 可写，必然成功。

环境教训：本地复现时 IDE safe-bin/rm 垫片（shebang=/bin/bash，OHOS 无此路径）
会混入 conan 构建的 PATH，conftest 清理失败造成 ltdl 检测假阴性——
需在 PATH 最前放 /system/bin/rm 真实包装器（conan-bin/rm）后再跑 conan create。
