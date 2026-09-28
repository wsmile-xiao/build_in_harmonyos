# kdc2tiff

RFC2587 Directory String 转 TIFF/FAX 的小工具（CGI 时代产物），同时提供第二个入口名 `kdc2jpeg`。

- **上游**：https://kdc2tiff.sourceforge.net/ ；发布件 `https://downloads.sourceforge.net/project/kdc2tiff/kdc2tiff/0.35/kdc2tiff-0.35.tar.gz`（94618 B，sha256 `bde9e3ed41bf09ded586e0ac87c2fe6e48780e4e98f9927a31d1c19e192f51ec`，与 Debian sid 池件逐字节同值＝同一文件仅改名）
- **语言 / 构建系统**：C，autotools（`configure.in` + `Makefile.am`）；本包 tarball **不含** `config.guess`/`config.sub`
- **依赖**：`libtiff`、`libjpeg`、`libm`（`configure.in` 的 `AC_CHECK_LIB` 三项）
- **产物**：`bin/kdc2tiff` 与 `bin/kdc2jpeg` 两枚可执行文件（各 109184 B、同 sha256 `0ffecdb134d353ebfc0116926141a3560c5846c364bcc1075027a2d70cee1ba6`、不同 inode）；纯可执行包，无 `lib/`

## HarmonyOS PC 适配要点

逐条依据与复算命令见 `0.35/notes.md`。

1. **第二入口名靠 copy 而非 link**（既有知识 `knowledge/doc/E050.md`）：上游用 `ln -f kdc2tiff kdc2jpeg` 造第二入口名，而 HMDFS 上建硬链接被拒（实跑 `ln -f ha hb` ⇒ `Operation not permitted`）⇒ `patches/0002-Makefile-ln-f-to-cp-f.patch` 改为 `cp -f`。⚠ **补丁顺序是机制的一半**：`Makefile.am`（第 20-21 行）必须在前、`Makefile.in`（第 431-432 行）在后，否则 automake 会依较新 mtime 回头重生成 `Makefile.in` 并冲掉改动。
2. **`configure` 的安全临时目录写法**（**E114**，`umask 077`）：`configure` 内 2 处命中，由**单个 hunk** 覆盖（`@@ -4355,12 +4355,12 @@`）。⛔ 本包不归 E007——tarball 无 `config.guess`/`config.sub`，且 `configure` 实参无 `--build/--host`、无 `ac_cv_*` 缓存绕过。
3. **main 签名**（`0003`）：本工具链（clang，`aarch64-unknown-linux-ohos`）要求 `int main`。
4. **测试面**：上游**无成体系用例**（`add_test`/`TESTS` 全 0；`Makefile.in:354/355` 的 `check:`/`check-am:` 是 automake-1.4 生成的**空壳目标**）⇒ 适配侧由 `test_package` 补 **29 条**断言，运行时读数 `SUMMARY kdc2tiff consumer: total=29 passed=29 failed=0`（静态 `chk` 站点 21 枚 + 内联 ok/bad 8 枚，无循环展开）。
5. **配方修订分两档**：本地 W3 绿跑实际发生在 harness Pre-download 注入的 `file://` 件上（`4890466954cbc948e72e295ee3e5d8b5`），交付态（官方址）是 `c2cb7785e3654e9a2ae534d2cf1eb8cb`，`PKGID cc91ff87ca05a40e640fad0984a2654e990285c6` ⇒ 两档如实并列，不宣称同一 rev。

## 版本

- **0.35** → `archives/k/kdc2tiff/0.35/`（平台任务 12768）
