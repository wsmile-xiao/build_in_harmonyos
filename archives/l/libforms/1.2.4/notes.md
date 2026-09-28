# libforms 1.2.4 适配笔记

## 编译环境
- 构建系统: autotools（configure 2.68 + libtool；树内构建 source=build=.，见问题 2）
- 编译日期: 2026-09-28
- 编译器: clang 15（conan profile ci/conan/profiles/ohos-aarch64，OHOS SDK /data/service/hnp/bin 工具链）
- 依赖: libjpeg/10、libx11/6.4.0、libxpm/3.5.17、xorgproto/2025.1（全部 ohpcd 已发布，preflight W0 全 OK）
- 状态: built（conan create EXIT=0 + test_package 2/2；conan-verify G0-G3 全绿；W3 本地 CI 模拟通过，待 CI）

## 编译步骤
```bash
# B 机独立 worktree
git worktree add ~/qzy/主理-74-libforms-1.2.4 -b feat/libforms-1.2.4 origin/main
export CONAN_HOME=$HOME/tmp/ch/home-libforms SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH

# 带构建槽与资源门（gate 6000MB，本包编译轻、实测 16GB 空闲）
conan create archives/l/libforms/1.2.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package 8d9ef4e61b71d7eadb8ebb1af0686664ac46c8b3 created；test_package 两可执行随 create 编译+自签+运行通过
#   日志: 本地 ~/tmp/uc2/z74-libforms/final-create3.log（不入库）；入库证据为 reports/ 下 conan-verify-report.md 与 w3-local-ci.log
```
recipe 要点：树内构建；configure 由 recipe 生成 OHOS 副本经 /system/bin/sh 执行（umask 077→022 归一）；configure 后先 `make -C lib/include forms.h` 预生成拼接头并断言非空；`make -j2`；`make install DESTDIR=` 后 package() 断言 6 件交付物（include/forms.h、include/flimage.h、lib/libforms.so、lib/libflimage.so、bin/fdesign、bin/fd2ps）+ licenses。

## 上游测试

**上游无任何自动化测试**（审计证据见 manifest.yaml upstream_test_audit）：configure.ac 与 20 个 Makefile.am 清点 TESTS=0、无 check 目标、无 gtest/pytest/criterion 绑定；demos/ 94 个 .c 为需 X server 的交互演示程序，不构成测试。

test_package 按 **E530**（无 X server 平台的消费者测试口径）实装为两个可执行、不宣称任何 GUI 可用：
- `libforms_api_surface`：32 个探针（22 libforms + 10 libflimage），`__typeof__(&name)` 强制编译期类型检查 + 链接期活重定位，probes=32 assertions=0；
- `libforms_abi_contract`：_Static_assert 钉死 FL_PUP_ENTRY 布局（32B）/FL_COLOR 宽度/FL_VERSION=1/FL_REVISION=2，共 static=8；运行期 runtime=2（sizeof 复核 + 断言 XOpenDisplay(NULL) 按实测失败）。

统计口径：上游测试 发现 0、执行 0、通过 0、失败 0、跳过 0。test_package 消费者用例 发现 2、执行 2、通过 2、失败 0、跳过 0（api_surface 静默退出 rc=0；abi_contract 输出 ok 两行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | create #1 链接 fdesign 失败 `ld.lld: error: duplicate symbol: curobj`（sp_spinner.o 与 sp_twheel.o 各定义一份） | 两文件各自非 static 定义 `FL_OBJECT *curobj`，仅靠 pre-Clang-10 「common symbols 合并」隐式语义链接；clang 15/lld 缺省 -fno-common | CFLAGS 加 `-fcommon`（extra_cflags），按上游书写方言构建的最小修复；先离线探针复现再验证修复，后入 recipe（E491） |
| 2 | create #1 前置失败 `lib/fd/cmdbr.h:28: fatal error: ../include/forms.h file not found` | forms.h 是 stamp-forms 生成的 nodist 拼接头且列 CLEANFILES，out-of-tree 下落在构建树，而 cmdbr.h 的 quoted include 按源码树解析 | layout 改树内构建（source=build=.，generators=.conan），configure 后先 `make -C lib/include forms.h` 预生成并断言非空，package() 断言 6 件交付物 |
| 3 | create（-fcommon 修复后首轮）test_package 编译失败：api_surface.c 9 个符号 `use of undeclared identifier`/未导出（fl_run、fl_define_colormap、fl_get_colormap、fl_get_visual、fl_get_depth、fl_get_screen、fl_get_window、fl_init_RGBdatabase、fl_lookup_RGBcolor） | 草稿符号表按 nm 导出挑选，未对「头文件已声明」做交叉校验：7 个 .so 未导出、2 个（fl_init_RGBdatabase/fl_lookup_RGBcolor）已导出但安装头未声明（前窗校验脚本正则不含大写致漏报） | 以安装头 + nm 双重交叉校验重选：fl_run→fl_free_form、fl_define_colormap→fl_create_colormap、fl_get_colormap→fl_get_canvas_colormap、fl_get_visual→fl_get_visual_depth、fl_get_depth→fl_get_canvas_depth、fl_get_screen→fl_XEventsQueued、fl_get_window→fl_get_real_object_window（fl_init_RGBdatabase/fl_lookup_RGBcolor 复核后确实已声明，保留）；复跑 32/32 全绿 |
| 4 | configure 的 X11 探测在交叉环境不可靠 | AC_PATH_XTRA 不走 pkg-config、不吃继承的 CPPFLAGS/LDFLAGS | `--x-includes/--x-libraries` 直指 libx11 包目录 + `X_PRE_LIBS= X_EXTRA_LIBS=` 清宿主残留；LDFLAGS 用 linker-view |
| 5 | libtool .la 在 DESTDIR 安装后残留绝对构建路径，消费者 `-lforms` 解析不到 | libtool relink 语义与 conan 包目录迁移冲突 | recipe 建 linker-view 并重写 .la（libdir→view、dependency_libs 归一 `-l` 前缀） |

## 源码修改

- `patches/0001-config.guess.patch`：config.guess 识别 HarmonyOS 三元组（E160）
- `patches/0002-config.sub.patch`：config.sub 接受 aarch64-linux-ohos 规范名（E072）
- conanfile.py：-fcommon、树内构建、OHOS configure 副本、forms.h 预生成断言、linker-view/.la 重写、`--disable-gl --disable-demos --disable-docs`、package() 交付物断言
- test_package/：E530 双可执行消费者（api_surface.c、abi_contract.c），不宣称 GUI 可用

## 依赖版本

libjpeg/10、libx11/6.4.0、libxpm/3.5.17、xorgproto/2025.1（conan 2.29.1；四依赖 preflight 全 [OK]）

## 验证结果

```bash
conan create … # Package 8d9ef4e61b71d7eadb8ebb1af0686664ac46c8b3 created；test_package 2/2 PASS
python3 scripts/ohc-run.py conan-verify libforms 1.2.4   # G0/G1/G2/G3 全 PASS，报告 reports/conan-verify-report.md
python3 scripts/ohc-run.py finish libforms 1.2.4 built   # W3 本地 CI 模拟通过（reports/w3-local-ci.log）
python3 scripts/ohc-run.py graph validate                # PASS（540 entries）
```

## 注意事项

- fd2ps 运行期硬编码读 `/usr/local/lib/X11/rgb.txt`（readxpm.c:348）：无该文件时该转换路径受限，不影响库本体与 fdesign（本平台无 X server，GUI 路径按 E530 不宣称可用）
- 本包 per-task 中间产物在 B 机 `~/tmp/uc2/z74-libforms/`（create/gate/探针日志、nm 符号表、check 脚本），不入库；入库证据以 reports/ 为准
## 对话记录

### 对话 #1 [2026-09-27]

- 问题: create #1 out-of-tree 构建报 `../include/forms.h file not found`；create #2/#3 资源门排队与 `duplicate symbol: curobj`（clang 15 缺省 -fno-common）
- 操作: layout 改树内构建 + forms.h 预生成；离线探针验证 -fcommon 后实装进 recipe（-fcommon + --disable-docs 等定案）
- 结果: 修复路径定案，但带 -fcommon 的真 create 未跑即交接（WIP 提交 9bbad15e64 保资产）

### 对话 #2 [2026-09-28]

- 问题: 本窗（收尾-1B）create 首轮主包建成，但 test_package 的 api_surface.c 9/32 符号无效（nm 有导出 ≠ 头文件已声明）
- 操作: 以安装头 + nm 双重交叉校验重选 7 个 libforms 探针符号并复核 2 个假阴性（fl_init_RGBdatabase/fl_lookup_RGBcolor 实为已声明，保留）
- 结果: 复跑 create EXIT=0，Package 8d9ef4e…created，test_package 2/2 PASS

### 对话 #3 [2026-09-28]

- 问题: finish 首轮 W3 L0k R38 卡 commands.json 缺失；次轮 finalize 报软件级 README.md、版本级 notes.md/manifest.yaml、packaging/ 缺失
- 操作: 补 commands.json（fdesign/fd2ps）、软件级 README.md、版本级 manifest.yaml + notes.md + packaging/ 目录
- 结果: W3 通过、close-archive 完成、conan-verify G0-G3 全绿、finish finish_success；release/debug tar.gz 属打包阶段遗留（打包产物 0，本阶段不做）
---

**编译结束**: 2026-09-28 01:14
**最终状态**: built
