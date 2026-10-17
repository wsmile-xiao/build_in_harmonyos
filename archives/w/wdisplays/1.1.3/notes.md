# wdisplays 1.1.3 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build；init-build 按 URL 误判为 autotools，已手写 meson 配方）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 / clang++（OHOS SDK，aarch64-linux-ohos，musl）
- 状态: built（W3 本地 `conan create` 通过 + `test_package` 9/9）
- 归档: archives/w/wdisplays/1.1.3
- 分支: feat/wdisplays-1.1.3（基于 upstream/main 4e3cc931cd）

## 软件说明

wdisplays 是 GTK+3 图形界面的 Wayland 显示器布局工具，通过
`wlr-output-management-unstable-v1` 读写 output 配置，并附带
`xdg-output` 定位、`wlr-layer-shell` 覆盖层、`wlr-screencopy` 截屏预览。
源码 6 个 .c + 3 个 .h，协议代码由 wayland-scanner 在构建期生成。

## 依赖核验（制品仓 ohpcd 实测）

| 依赖 | 上游要求 | 制品仓版本 | 结论 |
|---|---|---|---|
| wayland-client | >= 1.20 | wayland/1.22.0 | ✅（conan install --build=never 通过） |
| wayland-protocols | >= 1.17 | wayland-protocols/1.36 | ✅ |
| gtk+-3.0 / gdk-3.0 | >= 3.24 | gtk/3.24.43（broadway 后端） | ✅ |
| epoxy | 无版本要求 | libepoxy/1.5.10（经 gtk 传递，静态 .a） | ✅ |
| expat | wayland 传递 | 2.8.2 → override 2.8.2.1（与 gtk 链统一） | ✅ |

> 版本冲突：`wayland/1.22.0` requires `expat/2.8.2`，gtk 链用 `expat/2.8.2.1`，
> 配方用 `self.requires("expat/2.8.2.1", override=True)` 统一（hyprpicker 同族先例）。

## 编译步骤

```bash
# W3 本地验证（= CI 同源命令）
conan create archives/w/wdisplays/1.1.3 --version=1.1.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部：
1. `source()`：官方 GitHub tar.gz（sha256 校验）→ `apply_conandata_patches`（补丁 0001）
2. `generate()`：`PkgConfigDeps` + staging 构建工具（wayland-scanner /
   glib-compile-resources）+ pc 补全（gdk-3.0.pc / wayland-protocols.pc 的
   pkgdatadir / gio-2.0.pc 的 glib_compile_resources / glib-2.0.pc 的 -lintl）
   + `MesonToolchain` + machine file 注入 ar/ranlib/pkg-config/ninja
3. `build()`：`meson configure` + `meson build`
4. `package()`：`meson install` + OHOS ELF 自签名（bin/）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/main.c`/`overlay.c` 找不到 `<gdk/gdkwayland.h>`，`GDK_IS_WAYLAND_DISPLAY` 未定义（编译/链接失败） | OHOS gtk/3.24.43 只有 broadway 后端（`gdk-3.0.pc` targets=broadway），无 GDK Wayland 后端 | 补丁 0001 新增 `src/gdkwayland-compat.{c,h}`：wayland-client 实现 `gdk_wayland_display_get_wl_display`（真 `wl_display_connect`）/`gdk_wayland_monitor_get_wl_output`（registry 绑定）/`gdk_wayland_window_get_wl_surface`（Broadway 下返回 NULL）/`GDK_IS_WAYLAND_DISPLAY`；`main.c`/`overlay.c` 对 NULL 安全降级 |
| 2 | meson 断言 `assert(gdk targets contains 'wayland')` 直接 fail | 上游硬性要求 GDK Wayland 后端 | 补丁 0001 放宽为 “wayland 或 broadway 二者之一” |
| 3 | `wayland-scanner` 执行报 `Operation not permitted`（exit 126） | 制品仓 wayland 包的 OHOS ELF 未签名，HMFS 拒绝执行 | 配方 staging：拷贝 → 重签名 → wrapper 注入 LD_LIBRARY_PATH，并置于 PATH 最前 |
| 4 | 重签后 `Error loading shared library .../.cache/conan2/p/expat.../lib/libexpat.so` | wayland-scanner 的 `DT_NEEDED` 记录构建机缓存绝对路径，loader 不查 LD_LIBRARY_PATH | staging 时 `patchelf --replace-needed <绝对路径> <soname>`；**patchelf 会破坏签名，必须“拷贝→patchelf→重签名”**（先签后改会回到 EPERM） |
| 5 | `dependency('gdk-3.0')` 失败 | PkgConfigDeps 不生成 gdk-3.0.pc（gtk 配方未声明 gdk 组件） | 配方手工生成 `gdk-3.0.pc`（`targets=broadway`，`Requires: gtk+-3.0`；glade 同款） |
| 6 | `wayland_protos.get_pkgconfig_variable('pkgdatadir')` 取空 | PkgConfigDeps 生成的 wayland-protocols.pc 无 pkgdatadir | 配方向生成的 .pc 注入 `pkgdatadir=<pkg>/share/wayland-protocols` |
| 7 | `gnome.compile_resources` 找不到 glib-compile-resources | meson gnome 模块读 gio-2.0.pc 的 `glib_compile_resources` 变量 | staging glib-compile-resources（拷贝+重签名）并把 wrapper 路径写入 gio-2.0.pc |
| 8 | expat 版本冲突（wayland 2.8.2 vs gtk 链 2.8.2.1） | 两链条 pin 不同 patch 版 | `requires("expat/2.8.2.1", override=True)` |

## 源码修改

`patches/0001-ohos-gdkwayland-compat.patch`（唯一补丁，端口性 portability）：
- 新增 `src/gdkwayland-compat.h` / `src/gdkwayland-compat.c`：GDK Wayland
  访问器兼容层（wayland-client 实现，Broadway 下如实返回 NULL 而非空壳）
- `src/main.c`：`#include <gdk/gdkwayland.h>` → `#include "gdkwayland-compat.h"`；
  `activate()` 中 wl_display 为 NULL 时给出明确致命错误（不再段错误）
- `src/overlay.c`：同上换头；`resize()` 对 NULL surface/display 安全跳过，
  `window_map()` 在无 wl_surface 时跳过 layer surface 创建
- `src/meson.build`：放宽 GDK 后端断言；把 `gdkwayland-compat.c` 加入可执行源

> 补丁不含平台宏（`__OHOS__` 等），见 R8/PF5。

## 上游测试入口核验（R51 三步法 · 第 1 步：清点）

对 1.1.3 的 pristine 源码树（`wdisplays-1.1.3.orig`，33 个文件）逐项核验：

| 核验项 | 命令 | 结果 |
|---|---|---|
| tests/ 目录 | `ls -d tests test` | 不存在 |
| meson test 注册 | `grep -rn "test(" --include=meson.build .` | 0 处 |
| meson 文件内 "test" 字样 | `grep -rn "test" --include=meson.build .` | 0 处（退出码 1） |
| benchmark 注册 | `grep -rn "benchmark(" --include=meson.build .` | 0 处 |
| CI/测试 workflow | `ls .github .gitlab-ci.yml .travis.yml` | 均不存在 |
| 构建文件规模 | `wc -l meson.build */meson.build` | 17+48+50+34 = 149 行（无测试目标） |
| 源码规模 | `find . -name "*.c"` / `"*.h"` | 6 / 3 |

**结论：上游确无自动化测试入口**（既无测试套件也无 CI 测试流水线）。
构建产物即唯一验证手段；本适配另加鸿蒙特有测试（见下）。
`build()` 输出机器可读标记 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`。

## 鸿蒙特有测试（新增，test_package/test.sh）

`conan test`（W3 内嵌）实测 9/9 通过，退出码 0：

```
[test] wdisplays package content: .../p/bin
  [PASS] bin/wdisplays present and executable
  [PASS] ELF machine is AArch64
  [PASS] ELF carries a .codesign section (OHOS self-signed)
  [PASS] links libwayland-client (OHOS repository dependency)
  [PASS] links libgtk-3 (OHOS repository dependency)
  [PASS] libepoxy linked statically (epoxy symbols present in binary)
  [PASS] OHOS gdkwayland compat layer symbol present (patch 0001 linked)
  [PASS] GResource bundle wdisplays-resources embedded
  [PASS] binary runs on device: 'wdisplays --help' exit 0 with usage output
[test] RESULT: pass=9 fail=0 skip=0 (total=9)
```

其中 3/4/5/6/9 为鸿蒙平台特有断言（签名 ELF、OHOS 仓依赖链接形态、
适配补丁确已编入、真机可执行）。

## 依赖版本
- gtk/3.24.43（broadway 后端）
- wayland/1.22.0
- wayland-protocols/1.36
- libepoxy/1.5.10（静态）
- expat/2.8.2.1（override 统一）
- meson/1.11.0（tool_requires）

## 验证结果（真实命令 / 退出码 / 日志路径）

```bash
# 1. 依赖可消费核验（R35，禁止 conan list 判 binary）
conan download "gtk/3.24.43" -r=ohpcd --only-recipe                       # rc=0
conan install --requires="gtk/3.24.43" -pr:h=.../ohos-aarch64 \
  -pr:b=.../ohos-aarch64 --build=never                                   # rc=0（binary 命中）
# 同法验 wayland/1.22.0、wayland-protocols/1.36、libepoxy/1.5.10.1

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight wdisplays 1.1.3 --src <work>     # rc=0
#   {"detected_language": "c", "evidence": meson 构建系统 / project(...,'c') / c:6 100%}

# 3. 真实构建 + test_package（W3 同源）
conan create archives/w/wdisplays/1.1.3 --version=1.1.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   rc=0；[32/32] Linking target src/wdisplays；Package '...' created
#   日志: .ci_logs/wdisplays-1.1.3-create-final.log
#   test_package: pass=9 fail=0 skip=0

# 4. conan-verify（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify wdisplays 1.1.3                     # rc=0
#   G1/G0/G2/G3/G4 全 PASS；报告: reports/conan-verify-report.md

# 5. finish（含 W2 结构 / R36 依赖 / W3 本地 CI 模拟）
JUNK_PR_DIFF=$TMPDIR/pr-wdisplays.diff \
  python3 scripts/ohc-run.py finish wdisplays 1.1.3 built
#   Step 4 conan-verify ✅  Step 5 W3 ✅（.ci-result.json exit_code=0）
#   Step 9 W2 PR 原子性 ✅  Step 10 submit 就绪 ✅（4/4）
#   日志: .ci_logs/wdisplays-1.1.3-finish-5.log；reports/w3-local-ci.log

# 6. 补丁复现性（补丁应用结果与适配工作树逐字节一致）
cp -r wdisplays-1.1.3.orig ptest2 && cd ptest2
for f in patches/0*.patch; do patch -p1 -s < "$f"; done
diff -rq --exclude=.edit-tracker.json . ../wdisplays-1.1.3.work         # 无差异
```

### 门禁中暴露的环境/工具问题（非本包缺陷，均已定位）

| # | 现象 | 首个错误/证据 | 根因 | 处置 |
|---|------|--------------|------|------|
| 1 | 本地 W3 结束后 `conandata.yml` 残留 `gh-proxy.com` 镜像条目 | PF7 报 `conandata.yml:7 镜像前缀 gh-proxy.com` | `ci/conan/build_and_test.sh` 预下载阶段改写 URL 后「退出还原」在本地未生效 | 提交前手工还原为官方源（已在文件头写明每次跑完 W3 需复查） |
| 2 | PF9 拦住软件级 `README.md`/`commands.json`/`manifest.yaml` | `变更路径缺版本目录层` | PF9 `len(f.split("/")) < 5` 未豁免 ARCHIVE-SPEC §6 规定的软件级文件（与 R38/PF8/W3-L0k 自相矛盾；仓库 feedback 中 noweb/norm/flac/libiio/kconfig 等 7+ 例同因） | 属工具误报；`commands.json` 已通过 W3 的 L0k 门禁与 PF8，本 PR 需按先例以 `--no-preflight` 或等 PF9 修复 |
| 3 | `finish` Step 3 G0 干净构建验证失败 `configure: exit 127` | `G0: configure 失败 (exit 127)` | clean_verify 走 autotools `configure`，本包是 meson（无 `configure` 脚本） | 该步骤按 SKILL 表为非阻塞；meson 真实构建由 Step 4 G2 / Step 5 W3 覆盖并已 PASS |
| 4 | `finish` Step 8 `gen_summary 失败: 'str' object has no attribute 'append'` | 同上 | 工具自身缺陷（非致命） | 未阻塞归档；SUMMARY.md 未生成 |
| 5 | `finish` step5b 报「知识图谱完整性检查发现 1 类问题」 | `E219/E253/E305.kv 字段为空` | 属他人已入库条目的字段空缺，非本包内容 | 不改动 `knowledge/graph/`（只读路径，由主编审核维护）；本包 `knowledge_gained` 已带 `knowledge_ref`，`unreferenced=0` |
| 6 | `submit`/`preflight` 内 `subprocess('git')` 抛 `FileNotFoundError` | `No such file or directory: 'git'` | OHOS musl 的 Python `posix_spawn` 不做 PATH 搜索（仓库 feedback 已记录，需 sitecustomize shim） | 环境级缺陷；本次 PF 闸以「显式传入变更文件清单」方式逐条执行（PF1/2/3/5/6/7/8 全 PASS） |

## 注意事项

1. **运行时限制**：OHOS 的 GDK 无 Wayland 后端，系统亦无
   wlr-output-management compositor——本包在 OHOS 上可编译/链接/加载/启动，
   完整交互功能需在具备该协议的 Wayland 会话中运行。兼容层对
   `wl_surface` 如实返回 NULL 并让调用方降级，未用“空壳 stub”掩盖。
2. `src/outputs.c` 使用 `shm_open`（screencopy 缓冲），OHOS musl 提供该接口，
   链接阶段无问题（运行时同样受制于 compositor 缺失）。
3. 上游 `main.c` 仍有 2 个既有告警（`GDK_IS_WAYLAND_DISPLAY` 隐式声明已由
   兼容层消除；`G_APPLICATION_FLAGS_NONE` 为 glib 2.74+ 弃用告警，属上游问题），
   不阻塞构建。
---

**编译结束**: 2026-09-24 19:22
**最终状态**: built
