# mednaffe 0.9.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，GTK+ 3 GUI 应用）
- 编译日期: 2026-09-28（探索与配方首稿，前任窗口）；2026-09-30（W3 复验与收尾，接力窗口）
- 编译器: clang/clang++（OHOS aarch64，conan profile `ohos-aarch64`）
- 状态: built（以 `reports/conan-verify-report.md` 与 `.ci-result.json` 读数为准）

## 编译步骤

配方全托管（`conan create` 一条链），不走手工作业：

1. `source()`：官方 GitHub 发布件 `mednaffe-0.9.3.tar.gz`（sha256 430572c8…，与 manifest 一致；池址仅作版本/哈希核验，PF7 首选路径 (a)）。
2. `generate()` 三件事（GTK3 全图 pkg-config 修复）：
   - 把全依赖图 `lib/pkgconfig|share/pkgconfig/*.pc` 拷入 generators_folder，并把首行 `prefix=` 改写为该包真实绝对前缀 —— OHOS 制品 `.pc` 的 prefix 为空/错误，直接用会展开成 `-I//include/...`（E355 ②家族症状）；
   - `PKG_CONFIG_PATH` 以 generators_folder 打头、追加各依赖包 pkgconfig 目录；
   - 为「被静态捆绑、图内无独立包也无 .pc」的传递依赖补写空壳 `.pc`（libffi / libpcre2-8 / liblzma），让 `Requires:` 可解析（运行时不需要：readelf 实证 gobject-2.0 NEEDED 只有 libglib + libc；E348 同构手法）。
3. `build()`（源内改写全部内联在配方运行时完成，**不产补丁**，`patches/` 为空）：
   - `--build/--host=aarch64-unknown-linux-gnu`：tarball 自带的老 config.guess 不识 OHOS 三元组；
   - configure 脚本内联 `umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX"` → `umask 022 && mktemp -d ...`（E011）；
   - **两段式 config.status**：`configure --no-create` → 改生成的 config.status（umask 行 + `confXXXXXX` 改为私有 csdir 绝对路径）→ 再执行 config.status（E011 方法 1 / J1）；
   - 全程 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 内联重断言（E386/E232：profile 钉的 hnp bash 在 HarmonyOS 挂载上 getcwd 坏）；
   - `make -j1`（设备沙盒并行度限制）。
4. `package()`：`make install DESTDIR=<package_folder>` + 删 `lib/*.la`。
5. `test_package/`（K0 消费者断言，conan create 内真机执行）：`--version` rc=0 且含 0.9.3；`--help` rc=0 且输出非空 —— 4 条断言。

> 临时目录（TMPDIR/csdir）落 `build_folder` 子目录：机器无关（CI clean worker 无 `/storage/...` 树），符合 R49 work-dir 私有前缀口径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure/config.status 在 `confXXXXXX`、`subs*.awk` 上 `Permission denied` | HMDFS 上 umask 077 建出的 0700 临时目录对进程不可写（E011） | 两段式：`--no-create` → 改 config.status 的 umask/mktemp → 补跑（E011 方法 1） |
| 2 | `working directory cannot be determined`（CONFIG_SHELL 指 hnp bash） | profile 钉的 hnp bash 5.3 在 HarmonyOS 挂载上 getcwd 坏（E386/E232） | 内联 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 重断言 |
| 3 | pkg-config `--cflags` 展开 `-I//include/...`，configure 找不到 gtk+-3.0 头 | 依赖制品 `.pc` 的 `prefix=` 空/错（E355 ②家族） | generate() 全图改写 `prefix=` 到真实包前缀 |
| 4 | `Requires: libffi/libpcre2-8/liblzma` 解析失败 | 这些传递依赖被静态捆绑进 glib/libtiff 制品，图内无独立包也无 .pc | generate() 补写空壳 .pc（E348 同构手法） |
| 5 | `NameError: name 'src' is not defined`（package() line 158） | 配方首稿 package() 漏定义 src | 已修：`src = self.source_folder`（2026-09-28 05:35） |
| 6 | 配方曾硬编码本机绝对路径作 TMPDIR/csdir（CI clean worker 上不可复现） | 探索期临时写法被带进配方 | 改为 `build_folder` 子目录（2026-09-30 接力窗口） |
| 7 | conandata.yml 一度残留 `ghfast.top` 镜像串 | 上轮 G2 镜像注入进程被 Signal 9 杀掉、未走到恢复 | 恢复官方 GitHub URL，镜像串清零（每次 finish/W3 后复核） |
| 8 | 首版 K0 断言 `mednaffe --version/--help` 在真机**挂起**（FUTEX 阻塞，timeout rc=124） | 上游 main() 只有 `g_application_run()`，**无任何 CLI 参数处理**：`--version` 不被识别，桌面会话直接进入 GUI 主循环阻塞（headless worker 则在 display/D-Bus 初始化处退出） | 断言改写为消费者分层探针（A1 存在+可执行 / A2 ELF64-AArch64 / A3 DT_NEEDED 含 gtk-3·gdk-3·glib-2.0 / A4 3s 启动加载器冒烟——仅 `Error loading shared library` 判失败），策略同 klavaro/3.14 |

## 源码修改
- `patches/` 为空（`patches_applied: []`）：上述全部源内改写在 `build()` 运行时完成，不生成持久补丁。

## 依赖版本
- 直接: `glib/2.84.0.1`、`gtk/3.24.38`（preflight 实测均已发布到 ohpcd）
- 传递（conan 图解析）: pango / cairo / harfbuzz / atk / fribidi / libthai / gdk-pixbuf / libpng / libtiff / expat / zlib / webp / fontconfig / freetype 等

## 上游测试清点（R51 三步法）
- 清点: 上游 tarball 内 `find -iname "*test*"` 零命中；`Makefile.am` 无 `TESTS` / `check_PROGRAMS`；`configure.ac` 无测试入口 ⇒ 上游无成体系测试。
- 实际运行: 无上游测试可运行（非环境限制，是上游确实没有）。
- 交付面替代: `test_package/test.sh` 4 条真机断言（消费者分层探针 A1-A4，klavaro/3.14 同款策略），由 conan create 在设备上执行；回填口径见 manifest `upstream_tests.test_count: 0` + `assertion_count: 4`。

## 验证结果

- **preflight（W0）**: `bash ci/scripts/preflight_check.sh mednaffe/0.9.3` → rc=0（glib/2.84.0.1、gtk/3.24.38 已发布到 ohpcd；mednaffe/0.9.3 版本号未被占用）。
- **conan-verify（门禁④）**: rc=0，Verdict **PASS**（G0/G1/G2/G3/G4 全 PASS；L2/L4/L5 纯可执行包按规则跳过）。
- **W3 本地 CI 模拟（门禁⑤ finish 内）**: `.ci-result.json` `exit_code=0`、`integrity_hash=ee24fded2c88f2b3`、`log_sha256=d22e2de1a6cf5ac4094740d9251e3a4d7a88d04c6d439ede2bbb8d11d99606ac`；日志逐级读数：`G0_RESULT=pass`、`KC_RESULT=pass`、`JC_RESULT=pass`、`L0=pass`、`L1=pass (test_package executed)`、`L2=skip (mednaffe version/help failed — GUI 无 CLI 入口，按平台冒烟规则 skip)`、`L4=pass`、`L5=pass`、Build Summary `Total 1 / Success 1 / Failed 0 (100%)`。
- **消费者测试**: 4/4 断言通过（test_package/test.sh A1-A4；reports/test-report.md 有全文）。
- **质量门禁 verify-build**: PASS → reports/quality-report.md（G1 二进制完整性 ✅1；G2 ⚠1 `--version` 不适用；G3 ⚠2 无 RPATH 属 conan run env 设计；G4 ✅0）。
- **打包**: packaging/mednaffe-0.9.3-ohos-aarch64.tar.gz（3152KB）+ debug tar，打包流水线含 ELF 签名与执行权限修复。
- **收尾核对**: conandata 镜像串=0（官方 GitHub URL 单行）；补丁数 0 与 `patches_applied: []` 一致；`graph validate` rc=0（540 条目，169 条存量告警）。
---

**编译结束**: 2026-09-30 14:27
**最终状态**: built
