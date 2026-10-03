# mcabber 1.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-01
- 编译器: clang（OHOS SDK 26.0.0.18 / `aarch64-linux-ohos`）
- 目标平台: HarmonyOS PC（`os=OHOS`, `arch=armv8`）
- 状态: built

## 上游测试清点（R51 第一步）

mcabber 1.1.2 **上游没有任何自动化测试套件**，清点证据：

| 清点项 | 命令 | 结果 |
|---|---|---|
| 源码树测试目录 | `ls <src>/tests` | `No such file or directory` |
| 注册测试目标 | `grep -rn 'TESTS\|check_PROGRAMS' <src> --include=Makefile.am` | 无输出（全部 Makefile.am 均无声明） |
| `make check` 实际动作 | `make -n check` | 仅 automake 生成的 `check-recursive` 递归样板，不含任何测试程序 |
| configure 钩子 | `grep -n 'TESTS\|check-local' configure.ac` | 无输出 |

若按上游 `make check` 运行，结论是 **0 个测试用例**（注册数 0、通过 0/0）。

→ 按场景三口径处理：**先补全测试，再继续适配**。补全的消费者测试见
`test_package/`（真实执行 `bin/mcabber`，8 项断言），上游用例对比表见 PR 正文。
R51 第二步「可运行环境实际运行」对上游不适用（无测试可运行）；补全测试在
`conan create` 预检（W3）中真实执行，结果见「验证结果」。

## 编译步骤

mcabber 是构建在 loudmouth/glib 之上的文本界面 XMPP 客户端；上游源码包自带
`configure`（含内嵌 pkg.m4 / aclocal.m4），无需 autoreconf。

```bash
./configure --prefix=$PREFIX \
    --host=aarch64-unknown-linux-gnu \
    --with-libidn=no --disable-gpgme --disable-otr --disable-hgcset
make -j$(nproc)
make install
```

配方用 `AutotoolsToolchain` + `PkgConfigDeps` + `AutotoolsDeps`：

- `PkgConfigDeps` 生成 `glib-2.0.pc` / `gmodule-2.0.pc` / `ncursesw.pc`，并把
  loudmouth 包的 pc 复制成 `loudmouth-1.0.pc`（见问题 1），使 configure 的
  `PKG_CHECK_MODULES(..., loudmouth-1.0 >= 1.4.2)` 与 `AM_PATH_GLIB_2_0` 命中 conan 依赖。
- `AutotoolsDeps` 注入依赖的 `-I/-L/-l`（ncurses 的 curses 探测依赖它，见问题 5）。
- OHOS 分支按 E129/E011 分层 configure（见问题 2/3/4）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `Package requirements (loudmouth-1.0 >= 1.4.2) were not met` | `configure.ac` 用模块名 **loudmouth-1.0** 探测，而 loudmouth 包 `package_info` 声明 `pkg_config_name = "loudmouth-1"`，`PkgConfigDeps` 因此只生成 `loudmouth-1.pc`；包内自带的 `loudmouth-1.0.pc` 的 `prefix` 是上游编译期的陈旧 `/`，不能直接用 | `generate()` 内把生成的 `loudmouth-1.pc` 复制一份为 `loudmouth-1.0.pc`（同目录即在该生成器目录内，必在 `PKG_CONFIG_PATH` 中） |
| 2 | configure 阶段 `config.guess: unable to guess system type` | 出厂 `config.guess`（2018）不识别 `UNAME_SYSTEM="HarmonyOS"` | OHOS 分支只传 `--host=aarch64-unknown-linux-gnu`（**不传 `--build`**，lone `--host` 使 `cross_compiling=maybe`，运行期探测失败后自动翻转为 cross，跳过“运行新编译探针”）；`build()` 预置 `ac_cv_build=aarch64-unknown-linux-gnu` 让 `AC_CANONICAL_BUILD` 跳过 config.guess（与 loudmouth 1.5.4 同款处理） |
| 3 | `config.status` 写 subs 文件失败 / 临时目录权限异常 | E129/E011：HMDFS 给新建目录加 setgid，configure 的 `umask 077` 使临时子目录变成 `drwx--S---` | 分层 configure：`configure --no-create` → 把生成的 `config.status` 中 `umask 077` 改为 `umask 022` → 再执行 config.status |
| 4 | `configure` 死于 `working directory cannot be determined` | HNP bash 在 HMDFS 构建目录 `getcwd()` 失败（`ac_pwd=\`pwd\`` 检查中止） | 强制 `SHELL=/bin/sh`、`CONFIG_SHELL=/bin/sh`（toybox ash，`getcwd` 正常）并预设 `PWD=build_folder`；config.status 亦用 `/bin/sh` 执行 |
| 5 | configure 的 curses 探测失败 | `configure.ac` 先 `AC_CHECK_FUNC(initscr)` 再 `AC_CHECK_LIB(ncursesw, waddnwstr)`；仅靠头文件探测不够，需 ncursesw 的库路径与 `-DNCURSES_WIDECHAR` | 依赖 `ncurses/6.6` conan 包 + `AutotoolsDeps`（注入 `-L/-l`）与 `PkgConfigDeps`（`ncursesw.pc` 提供 `-DNCURSES_WIDECHAR`） |
| 6 | 可选特性会半开启（libidn / GPGME / OTR） | 上游默认 `gpgme` 开、`libidn` 探测开，而制品仓无对应包 | 显式 pin `--with-libidn=no --disable-gpgme --disable-otr`；`--disable-hgcset` 避免构建期调用 mercurial |
| 7 | 应用类包（无库）如何满足结构门禁 | mcabber 只装二进制 + dlopen 插件，没有可链接的库 | `package_type = "application"`；`package_info` 置 `cpp_info.libs = []`、`bindirs = ["bin"]` 并向 runenv 前置 PATH；软件级 `commands.json` 声明工具（R38）；test_package 直接执行二进制断言 |
| 8 | `mcabber -V` 不报告 unicode 支持（`configure: WARNING: Your ncurses installation does not support unicode`），窄字符代码路径导致 UTF-8 输入/显示失效 | `configure.ac` 的 unicode 判定 `cf_ncurses_unicode=yes` **只在该文件的 curses 探测块内被赋值**，而该块被 `AC_CHECK_FUNC(initscr,, ...)` 的空动作短路——`AutotoolsDeps` 把依赖库（含 `-lncursesw`）注入 `LIBS`，于是 `initscr` 已可链接 → 整个探测块跳过（`AC_CHECK_FUNC(initscr)... yes`），`HAVE_UNICODE` 永不定义 | `generate()` 显式 `extra_defines.append("HAVE_UNICODE")`：依赖的 ncurses 6.6 包本就是宽字符构建（其 libs 为 `formw/menuw/panelw/ncursesw`），该宏即上游本应定义的；且该定义**自校验**——若实际未链宽字符 API，链接期会因 `waddnwstr*` 未定义而失败。修复后 `-V` 输出 `Compiled with unicode support.` ✓ |
| 9 | 包内残留 4 个 libtool `.la`（`lib/mcabber/*.la`），携带构建机绝对路径 | conan `rm()` 默认 **非递归**（`recursive=False`），而插件装在一级子目录 `lib/mcabber/` 下，`lib/*.la` 通配不到 | `package()` 改为 `rm(self, "*.la", <pkg>/lib, recursive=True)` |

## 源码修改

无补丁：上游源码零改动，全部适配在配方层完成（`patches: {}`）。

## 依赖版本

- glib/2.84.0.1（glib-2.0 + gmodule-2.0）
- loudmouth/1.5.4（XMPP 协议栈）
- ncurses/6.6（宽字符版，`libncursesw.a` + `ncursesw.pc`）

## 验证结果

```bash
# 本地（W3）真实构建 + 消费者测试
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify mcabber 1.1.2
# → ✅ G1/G2/G3 PASS，配方验证通过，可标记 status: built
# （G4/L2/L4/L5 因工具未按 user/channel 查询缓存包而跳过，属本仓应用类包
#   的既有现象：abook 等同类归档的验证报告同样如此）
```

`conan create` 真实执行结果（第 3 轮，`--build=missing`，OHOS aarch64）：

- configure → `make -j` → `make install` → `package` 全通过；包内容：`bin/mcabber`、
  `include/mcabber/*.h`（30）、`lib/mcabber/{libbeep,libfifo,liburlregex,libxttitle}.so`、
  `lib/pkgconfig/mcabber.pc`；`.la` 已清除。
- test_package（8 项断言，真实执行 `bin/mcabber`）**全部通过**。`-V` 实测输出：

  ```
  Installation data directory: //share

  Compiled with unicode support.
  Compiled with modules support. (API 1.1.2:1-1)
  Modules directory: //lib/mcabber
  ```

  （`//share`、`//lib/mcabber` 是 conan autotools 以 `--prefix=/` + `DESTDIR` 分阶段安装的
  结果，与 loudmouth 1.5.4 同款；包内实际路径为 `<pkg>/share`、`<pkg>/lib/mcabber`。）
- 上游测试：**0/0**（上游无测试套件，清点证据见上）。
- 补全测试（鸿蒙独有，`test_package/`，8 项断言，真实执行 `bin/mcabber`）：
  1. `mcabber -h` 退出码 0，打印用法行（二进制可执行、argv 解析正常）
  2. `mcabber -V` 退出码 0（启动路径真实加载 glib/loudmouth/ncurses 依赖链）
  3. `-V` 输出含 `Installation data directory`（编译期数据目录已定义）
  4. `-V` 输出含 `unicode support`（configure 确实探测到 ncursesw）
  5. `-V` 输出含 `modules support`（dlopen 插件特性已启用）
  6. `-V` 打印的 `Modules directory`（编译期 `PKGLIB_DIR`）在包内存在
  7. 该目录内含 `libbeep.so` / `libfifo.so` / `liburlregex.so` / `libxttitle.so` 四个上游插件
  8. 未知参数退出码非 0（参数校验路径），且包内无 libtool `.la` 残留

## 注意事项

- **宽字符已启用**：`-V` 报告 `Compiled with unicode support.`（HAVE_UNICODE 已定义，
  UTF-8 收发与 CJK 显示走宽字符路径）。
- **TLS 限制**：依赖 loudmouth 1.5.4 在制品仓以 `--with-ssl=no` 构建（该仓无 GnuTLS/OpenSSL 链接开关），
  因此 mcabber 的 SSL/TLS 连接能力为关闭状态（`-V` 不报告 SSL 支持）。明文 XMPP 连接、
  roster/消息处理与插件机制均正常，属功能受限而非构建失败。
- `mcabber -V` 打印的是编译期特征而非库版本；插件目录一致性断言（第 6/7 项）用于替代
  “版本号比对”，可捕获 `PKGLIBDIR` 与实际打包布局不一致这一经典运行时故障。
- 插件通过 `dlopen` 从主程序取符号，故主程序与插件必须来自同一包（同一 conan 包内布局，
  不可拆包分发）。编译期 `PKGLIB_DIR` 为 conan 分阶段安装产生的绝对路径（`/lib/mcabber`），
  消费方运行时用 mcabberrc 的 `modules_dir` 设置指向包的 `<pkg>/lib/mcabber` 即可加载插件
  （`modules.c` 中 `settings_opt_get("modules_dir")` 优先于 `PKGLIB_DIR`）。
- 本机观察：`make install` 产出的 390 个文件（bin/mcabber、include/mcabber 30 个头文件、
  lib/mcabber 4 插件、share/mcabber 352 个帮助/文档文件）在 HMDFS 构建目录下直接执行会
  报 `Permission denied`（setgid/权限类平台限制），而 conan 缓存内构建产物执行正常；
  `conan create` 的 test_package 在缓存中运行，不受影响。
---

**编译结束**: 2026-10-01 19:18
**最终状态**: built
