# le 1.16.8 适配笔记

## 编译环境
- 构建系统: autotools（release tarball **自带生成好的 configure/Makefile.in**，无需 autoreconf）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）与 clang++（严格 `-std=c++17`）
- 状态: built

## 版本说明
- 上游: http://lav.yar.ru/programs.html （LE 编辑器），版本 `1.16.8`；Debian 源码包 `le`（1.16.8-1）
- 源码: `https://deb.debian.org/debian/pool/main/l/le/le_1.16.8.orig.tar.xz`，
  sha256 `4ab7fdb9ddf12d57a0a3f0452d7cc5be583df8a926ab9e443bbc9be452cc402f`
- 版本号沿用赛事清单 `1.16.8`（首次适配，R37）

## 编译步骤
```bash
# 运行依赖：ncurses/6.5（制品仓为宽字符静态库 libncursesw.a）
conan create archives/l/le/1.16.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `build-aux/config.guess: unable to guess system type`（伴随 `dummy.c: Permission denied`） | 鸿蒙只运行已签名二进制，config.guess 的探测程序无法执行 | 显式传 `--build/--host=aarch64-unknown-linux-gnu`，跳过猜测 |
| 2 | 找不到 curses | LE 自带的 `LE_PATH_CURSES_DIRECT` 宏只按**硬编码**的 `/usr/include*` 搜索，完全不走 CPPFLAGS | 传上游自带的 `--with-curses-include=<ncurses 包>/include`（配方里从 `self.dependencies["ncurses"].package_folder` 推导） |
| 3 | ncurses 制品只有**宽字符静态库**（`libncursesw.a`），担心 `-lncurses` 链接失败 | LE 自身带 `use_libcursesw` 探测；首轮误加了一条"把 `-lncurses` 改成 `-lncursesw`"的补丁，结果链接命令行出现 `-lncursesww` | 无需补丁：回退该补丁后，LE 自己探测到宽字符库并追加 "w"，链接正常（教训：先读上游探测逻辑，别抢着打补丁） |
| 4 | `config.status` 报 `./confXXXXXX/subs1.awk: Permission denied` | HMDFS 新建目录带 setgid 位，autoconf 用 `umask 077` 建的 `confXXXXXX` 目录不可用 | 补丁 0001：configure 内 config.status 模板的两处 `umask 077` 改 `022` |
| 5 | `src/signals.cc` 报 `use of undeclared identifier 'typeof'` | `SA_HANDLER_TYPE` 用了 GNU `typeof`，而 OHOS profile 的 cppstd=17 让 clang 走严格 `-std=c++17` | 补丁 0002：改用保留拼写 `__typeof__`（语义不变） |
| 6 | 构建目录作为进程工作目录时 `getcwd()` 失败 | HMDFS | `build()` 预置 `os.environ["PWD"]` |
| 7 | 上游没有测试套件 | 无 `tests/` 目录、无 `check_PROGRAMS`/`TESTS`/`check` 目标 | `build()` 内置 `grep`/`find` 审计留证（R51 N=0），补充消费者用例 |
| 8 | `le --help` 不能直接用于自动化冒烟 | 上游用法路径以 **1** 退出 | 冒烟改用返回 0 的 `--version`、`--dump-keymap`、`--dump-colors`，并各自校验输出内容 |

## 源码修改
- `patches/0001-configure-config-status-umask.patch` — config.status 临时目录 `umask 077 → 022`（HMDFS）
- `patches/0002-signals-strict-cxx-typeof.patch` — GNU `typeof` → `__typeof__`

## 依赖版本
- `ncurses/6.5`（宽字符静态库；制品仓已发布）。除此之外 LE 只依赖 libc/libm。

## 验证结果
```bash
conan create archives/l/le/1.16.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0
# 交付：bin/le、share/（keymap、颜色表、le.ini、图标、文档）

# 消费者用例（test_package/test_le.sh，7 个断言全部通过）
le --version      → rc=0，含 "1.16.8" 与 "Text editor LE"       ✓
le --dump-keymap  → rc=0，含 "backward-char" 且 ≥100 行         ✓
le --dump-colors  → rc=0，含 "default_colors" 且 ≥20 行          ✓
le --help         → rc=1（上游用法路径），含 "Usage: le"         ✓
LE_CONSUMER_CHECKS=7 FAILURES=0
```

上游测试：LE 1.16.8 **不含任何测试套件**（树里没有 tests 目录，Makefile 里没有 `check` 目标/`TESTS`），
因此按 TEST_QUALITY_SPEC 在 `build()` 内置审计命令留证，并用编辑器的非交互入口做消费者验证。
`test_package/` 含 `conanfile.py`（消费者配方）+ `test_le.sh`（真实二进制断言，满足 CI L0c 对测试源文件的要求）。

## 注意事项
- `le` 是交互式编辑器，自动化只能覆盖其非交互入口（版本、键位表、颜色表导出）；交互 TUI 行为需人工验证。
- `--help` 以 1 退出属于上游现状（用法路径），自动化脚本不要用它判断成功。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 在鸿蒙 PC 上完成 le 1.16.8 的适配，并同时贡献一条知识库草稿（路径 B），提交 PR。

**执行摘要**:
1. 依赖预检（W0/R36）：只需 `ncurses`（制品仓已发布 6.4/6.5/6.6）。
2. 构建链路：自带 configure → 显式 `--build/--host` + `--with-curses-include` → 两个小补丁
   （config.status umask、`typeof`→`__typeof__`）→ `conan create` rc=0。
3. 上游测试清点：无测试套件（N=0）→ `build()` 内置审计留证 + 三个非交互消费者检查。
4. 知识贡献（路径 B）：本轮在 trousers/tpm-tools 适配中发现的"**libc 族内变体入口缺失**"
   （utmp 族的 `getutid`、pwd 族的 `getpwent_r`，与已有 E121 的"utmpx 整族缺失"不同）
   写成 kv+md 草稿 `knowledge/drafts/DRAFT-ohos-libc-missing-family-variant-entrypoints.*`，
   含"先查 sysroot 符号再改"的判定方法与等价改写套路。
5. 质量门禁：conan-verify、W3 本地 CI 模拟、W4 独立审计（见 `reports/`）。

**产出文件**: `conanfile.py`、`conandata.yml`、`patches/`（2 个）、
`test_package/`（`conanfile.py`、`test_le.sh`、`MANIFEST.yml`）、
`notes.md`、`manifest.yaml`、`commands.json`、`README.md`、`reports/test-report.md`、
`knowledge/drafts/DRAFT-ohos-libc-missing-family-variant-entrypoints.{kv,md}`。
---

**编译结束**: 2026-10-04 11:25
**最终状态**: built
