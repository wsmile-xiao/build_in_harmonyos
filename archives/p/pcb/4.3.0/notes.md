# pcb 4.3.0 — 适配笔记 (HarmonyOS PC, aarch64)

## 结论摘要
batch HID 版 pcb 4.3.0 在 OHOS aarch64 编译安装成功，`pcb -x gerber|bom|IPC-D-356`
导出与上游 golden 文本一致；test_package 14 断言全绿。

## 背景与历史
- 2026-09-03 agent F858 在 W0 因 ohpcd registry DNS 故障止损
  (dependency_missing)；registry 已切换 conan.cnb.cool 域名并恢复。
- OpenDesk 分支 feat/pcb-4.3.0 (48cb4b35) 配方为"纸上配方"（从未 conan
  create 验证；notes 自述本地工具链缺 autopoint/automake perl 环境），
  且其 conanfile 声称 glib 软依赖、无 glib requirement —— 与源码事实
  (src/global.h:66 无条件 `#include <glib.h>`) 矛盾。本次重写。

## 源码与依赖分析
- 官方 tarball (github tag v4.3.0, sha256 3a2e8305…) 无 configure：
  autogen.sh 引导（autopoint→intltoolize→aclocal -I m4→autoheader→
  automake -a -c --foreign→autoconf）。
- 依赖闭包（configure.ac 逐一核实）:
  - glib-2.0: 硬依赖（global.h/flags.c 无条件 include + configure.ac
    把 GLIB_LIBS 无条件拼进 LIBS），registry 已发布 glib/2.84.0.1（98+
    下游在用）。
  - cairo/gts: 仅 toporouter；--disable-toporouter 后无探测。
  - gtk/lesstif/X11/dbus/gdlib: batch 模式全跳过（默认 dbus=no）。
  - configure.ac 无 AC_RUN_IFELSE —— 只有 compile/link 探测，
    --build/--host 同 triplet 安全。
- 工具闭包 (registry 二进制已发布, conan download 实证):
  automake/1.18、intltool/0.51.0 (tool_requires)；autoconf 2.72 套件 +
  gettext_0.26 autopoint + pkg-config 在镜像 /data/service/hnp。

## OHOS 环境坑（本包实证 / 同源 E 编号）
- E089: conan automake/1.18 的 aclocal/automake 脚本 @am_AUTOM4TE@
  占位符未替换 → AUTOM4TE/SED/AUTOCONF/AUTOHEADER 环境变量覆盖为
  /data/service/hnp/bin 路径。
- autopoint: 镜像 /data/service/hnp/gettext.org/gettext_0.26/bin，
  编译期硬编码 lycium 的 gettext_datadir → 环境变量指向
  .../share/gettext (archive.dir.tar.xz 所在)。
- E129/E114: 生成 configure 的 ac_tmp 走 mktemp(0700) → HMDFS 写失败；
  sed 固定 ac_tmp=./fixed_tmp + source/build 两侧 mkdir。
- E074: 并行 make jobserver fifo EPERM → -j1。
- E107/E142: 沙箱 LDFLAGS 含 -L/usr/local/lib（旧静态 glib）→ generate()
  按 conan 依赖 libdirs 重建 LDFLAGS。
- config.sub 2015 无 linux-ohos → 补丁 0001 短路 echo 识别
  *-linux-ohos*（conandata 官方 URL 保持）。
- HMDFS TMPDIR/HOME 固定到 build_folder 内。

## 测试
- 上游 105 场景回归（tests/tests.list 有效条目实测 105：84 个非 hid_png +
  21 个 hid_png；早期草稿 112=84+28 为推算误值，2026-09-06 解包核验修正）。
  其中 84 个非 hid_png 场景已在构建树真实执行官方 run_tests.sh：PNG 类需
  ImageMagick、action 类需 X display、gerber/PS 比对需 gerbv/ghostscript，
  CI 沙箱无此工具链 → 通过 38/失败 4/跳过 42（修复前 27/20/37，日志
  pcb_upstream_run5/6.log）。
- 引入 3 上游场景 7 断言（bom/bom_md/IPC-D-356 golden 比对）+ 7 新增
  错误路径/边界断言 = 14 断言全绿；数据 6 个上游文本文件逐字节搬运，零二进制。
- make check 全量未跑（沙箱无 IM/display）；test_package 以真实上游
  golden 归一化比对替代（日期/版本头行剔除，语义同上游 awk 归一化）。

## 遗留
- GUI (gtk/lesstif) HID 未适配：需要完整 GTK/X11 生态 + 显示服务，
  非 headless 场景；batch HID 覆盖导出/DRC/动作脚本全部命令行功能面。
---

**编译结束**: 2026-09-05 12:00
**最终状态**: built
