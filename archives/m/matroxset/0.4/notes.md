# matroxset 0.4 — OHOS 适配笔记

## 软件概况
- 上游：matroxset 0.4（2004-05-19），单文件 C 程序 `matroxset.c`（392 行），许可证
  GPL-2（随包 `COPYING`）。
  作者归属**以 Debian `debian/copyright` 为准**：`Copyright: 2004 Petr Vandrovec
  <petr@vandrovec.name>`；tarball 内文件属主 `vana/vana`、上传目录 `root/src`
  （SourceForge 惯例）亦指向同一人。**tarball 内的 `matroxset.c` 本身没有作者
  头注释**，所以不从源码里认领作者。
- 用途：驱动 Matrox 显示卡的 fbdev 私有 ioctl——切换输出模式（显示器 / PAL TV /
  NTSC TV / DFP）、把 CRTC 映射到输出、报告消隐（blanking）信息、以及读写卡上
  TV-out 控制寄存器块（TVOCTRL / TVOCONTROL / TVOREG_{A,B,C}）。
- **不是 X11 工具**（这点容易误判：包名像 Matrox 的 X 扩展，实际只做 fbdev ioctl）。
  唯一依赖是 ncurses，用于 `-e` 交互式控制项编辑器；与 libX11 无关。

## 源码来源与 PF7/R39
- matroxset **没有上游发布站**：Debian `debian/watch` 写的是
  `FakeWatchNoUpstreamSiteForThisPackage`，唯一项目页
  `https://www.bglug.ca/matrox_tvout` 只有说明文字、没有下载链接。
- 因此以 Debian 归档池的**原生 orig tarball**（非 +dfsg、非 .debian.tar.*）为权威
  分发点，sha256 `7f160b45...9003` 记录在 PGP 签名的 `matroxset_0.4-13.dsc` 中。
- URL 用 `ftp.debian.org`（Debian ftp-master 的公开名，**不是第三方镜像**）而不是
  `deb.debian.org`：仓库 PF7 源URL闸（`scripts/ohc/preflight.py::_pf7_classify`）把
  `deb.debian.org` / `snapshot.debian.org` / `security.debian.org` /
  `archive.debian.org` 四个主机字面量一律归为「Debian 下游重打包源」硬拦；实测两者
  返回逐字节相同的 24996 字节 tarball。仓库内已有先例：`i/installation-locale`、
  `a/aldo`、`c/ca-certificates`。

## 依赖（R35/R36 已用 conan download 验证可消费）
- `ncurses/6.6` —— `-e` 交互式控制项编辑器需要。已确认 recipe 与 OHOS armv8 二进制
  均已发布到制品仓（`--only-recipe` 与完整下载两次 rc=0），本地缓存命中 package id
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5`（binary revision `d9a448fa…`），
  故 `--build=missing` 不会去编译 ncurses。

## OHOS 适配要点
1. **构建系统是坏的，必须绕过 make（R1 的真实案例）**：上游 `Makefile` 的 `all` 目标
   依赖 `matroxset`，但文件里只有 `matroxset.o` 的编译规则、**没有链接规则**，
   直接 `make` 必然失败。Debian 的 `debian/rules` 同样绕过 make：
   `$(CC) $(CFLAGS) $(CPPFLAGS) $(LDFLAGS) -o matroxset matroxset.c $(LIBS)`。
   本配方沿用该做法，在 `build()` 里直接调编译器。
2. **编译器取自 conan conf（R33）**：`self.conf["tools.build:compiler_executables"]["c"]`，
   缺省 `/data/service/hnp/bin/clang`，不使用裸 shell 变量 `${CC}`（CI release worker
   上这些变量不存在）。`test_package/conanfile.py` 同样遵守。
3. **`-D_FORTIFY_SOURCE` 有意关闭——但原因不是「OHOS 缺符号」（本条是自我纠错，
   结论与第一轮正好相反）**：
   - 第一轮的判断是「OHOS musl 不提供 `__open_chk` 等 fortify 包装，启用
     `_FORTIFY_SOURCE=2` 后运行期报 `Error relocating: __open_chk: symbol not
     found`，所以必须关掉」。**这个判断是错的**，犯的是本仓记忆库 **T137**
     记录的那类错误：把本地运行环境的能力缺口当成平台能力缺口。
   - 按 T137 的取证纪律重做（**先做阳性对照，再看结论**）：

     | 取证步骤 | 结果 |
     |----------|------|
     | `nm --defined-only <真机 libc.a>` 阳性对照 | **24387** 个 defined 符号、stderr 0 字节 → 工具可用，输出可信 |
     | 真机 libc.a 中 `__[A-Za-z0-9_]*_chk` 去重计数 | **45** 个 |
     | `__open_chk` / `__read_chk` / `__fread_chk` / `__strlen_chk` / `__memcpy_chk` | **全部存在** |
     | 本地 FORTIFY 版二进制 `nm -u` 实际索取 | 仅 `__open_chk`（外加 `__stack_chk_fail`/`__stack_chk_guard`） |
     | `/opt/ohos-guest/lib/libc.so` 的 `_chk` 导出 | 仅 `__stack_chk_fail` / `__stack_chk_guard`，**零个** fortify 包装（共 1648 个动态符号） |

     取证对象是 DevEco SDK 里真实的 aarch64 libc
     （`.../sysroot/usr/lib/aarch64-linux-ohos/libc.a`，11,213,186 字节），
     **不是**同目录下 72,144 字节的 `libc.so` 链接桩（T137 明确要求）。
   - 结论：**真机 OHOS 上 `_FORTIFY_SOURCE=2` 是安全的**（与 T137 对 vfu 5.09
     的结论一致）；本地之所以跑不起来，是因为本机唯一可用的 aarch64 运行期
     `/opt/ohos-guest/lib/libc.so` 是 stock musl（BuildID
     `5933c076c6985fe4dcf9c8d9f0e87c37931afd4f`），不是 OHOS libc。
   - 因此本包**仍然关闭 FORTIFY**，但理由换成可评审的真理由：本包的
     test_package 必须在**所有能验证的环境里真执行**被测二进制（这是 R34 的
     核心，也是 L1e 破坏性反向测试的前提）。在 stock musl guest 上 FORTIFY 版
     直接 rc=127 起不来，测试套件将**无法验证**——「不可验证」比「少一个
     硬化标志」更糟。保留 `-fstack-protector-strong`（musl 与 OHOS 都提供
     `__stack_chk_fail`/`__stack_chk_guard`，实测生效）。
   - 这是一条**显式登记的取舍**，不是对平台能力的误判：只要有一个真 OHOS
     运行期（本仓 CI worker 若确为真机 aarch64 OHOS），就可以把
     `-D_FORTIFY_SOURCE=2` 加回。`/opt/ohos-guest/lib/` 里虽有
     `libchkfcnshim.so` / `libfdchkshim.so` 这类补符号 shim，但 **T137 明令
     不得依赖 `LD_PRELOAD` shim**，故未采用。
4. **ncurses 必须静态链接**：OHOS 的 ncurses 包只提供静态归档
   （`libformw.a` / `libmenuw.a` / `libpanelw.a` / `libncursesw.a`），且 OHOS 加载器
   **忽略 `LD_LIBRARY_PATH`**，所以任何动态链接的 ncurses 在纯净设备上都起不来。
   链接顺序按 ncurses 的消费者优先约定：`-lformw -lmenuw -lpanelw -lncursesw`
   （提供者 ncursesw 放最后）。实测 `readelf -d` 只剩 `libc.so` 一项 NEEDED。
   **与上游的差异（须知）**：上游 `Makefile` 的 `LDFLAGS` 和 Debian `debian/rules`
   的 `LIBS` 都是 `-lncurses`；本配方用 `-lncursesw` 是因为 Conan 的
   `ncurses/6.6` OHOS 包**根本没有 `libncurses.a`**，只有宽字符静态库。
   `cpp_info.libs` 的顺序与该包 `package_info()` 里的
   `["formw","menuw","panelw","ncursesw"]` 完全一致，不额外硬编码。
5. **旧版内核 UAPI 头无需打补丁**：源码自带的 `fb.h` / `matroxfb.h` / `videodev2.h`
   是 2004 年版，只额外需要 `<linux/tty.h>`（取 `tty_mode_t`）和 `<asm/types.h>`
   （取 `__u8`/`__kernel_ulong_t`）。这两个头 OHOS sysroot 都有，`asm/*` 经 NDK
   driver 追加的 `aarch64-linux-ohos` multiarch include 目录解析，**无冲突、无需 stub**。
6. **硬化与 PIE（R6/R7）**：`-O2 -Wall -Wformat -Werror=format-security
   -fstack-protector-strong -fPIE`，链接加 `-pie -Wl,-z,relro,-z,now`。

## 补丁 0001（唯一补丁，且非平台专属）
- 改 3 处 `printf()` 为 `printf("%s", ...)`：
  - `printf(ptr->msg)` ——**只有这一处**是真正的「非常量格式串」，
    `-Wformat-security` 只在它上面报错（实测：
    `matroxset.c:339:14: error: format string is not a string literal
    (potentially insecure) [-Werror,-Wformat-security]`，`error generated`）；
  - `printf(", ")` 与 `printf("none")` ——这两个是**字符串字面量**，从来不会触发
    `-Wformat-security`，改它们只是与上游 Debian `debian/patches/10-gcc.patch`
    （连 `printf("\n")` 一起改了共 4 处）保持形式统一。
- 因此措辞是「3 处 `printf()` 统一改成 `printf("%s", ...)`」，其中 1 处是必要的
  硬化修复、2 处是形式统一；输出**逐字节不变**，glibc/musl 行为一致。
- **这唯一的 1 处必要修复确实在本包生效**，不是空补丁：未打补丁的源码在
  `-Werror=format-security` 下硬报错（`1 error generated`），而带该标志的
  `conan create` 构建返回 rc=0 —— 说明 `source()` 里的
  `apply_conandata_patches()` 真的生效了（若写在 `build()` 里会改到导出树 `s/`
  而编译的是复制品 `b/<pid>/b`，补丁零作用却照样打印 "Apply patch"）。

## R8 平台宏排查
- 全程未引入 `__OHOS__` 或任何其它平台宏，无需条件编译分支。
  `grep -rn "__OHOS__\|OHOS" archives/m/matroxset/0.4/` 只命中注释与文档。

## R51 上游测试核验
- 上游源码树共 9 个文件（`matroxset.c` + 3 个头 + `COPYING` + `Makefile` +
  `normal`/`swapit`/`swapped` 三个示例配置），**没有任何测试入口**
  （无 `test`/`check` 目标，无 CUnit/CMocka，`matroxset.c` 里也没有 `main()` 之外的
  自测桩）。
- 结论：**upstream_tests = 0**，可行性完全由 test_package 的消费者测试承担。

## 消费者测试 (test_package) —— 14 项真实断言
- `test_matroxset.c` 编译成同目标 aarch64 二进制，然后**真的执行**被测包里的
  `matroxset` 11 次，每次同时断言真实退出码与真实 stdout/stderr 文本。
- 之所以不需要 Matrox 硬件：参数解析类分支全部在任何 ioctl 之前就定型；
  而需要触达 ioctl 的三条路径用 `/dev/null` 作 framebuffer——`open("/dev/null")`
  成功、`ioctl(MATROXFB_GET_OUTPUT_MODE)` 必然失败，工具应打印
  `ioctl failed: ...` 且**仍返回 0**。
- 已实测的真实行为（未臆测）：

  | 调用 | 退出码 | 关键输出 |
  |------|--------|----------|
  | `-h` | 98 | `usage: matroxset [-f fbdev] [-o output] [-m] [value]` |
  | `-h` | 98 | `(default /dev/fb1)` |
  | `-h` | 98 | `print information about blanking` |
  | `-h` | 98 | `For output mode, 128 means monitor, 1 = PAL TV, 2 = NTSC TV` |
  | `-Z` | 99 | `Bad commandline` |
  | `-p -m` | 95 | `You cannot use -p together with -m or -o` |
  | `-m -o 1` | 96 | `You cannot use -m and -o together` |
  | `-f /nonexistent/fb0` | 122 | `Cannot open /nonexistent/fb0: No such file or directory` |
  | `-f /dev/null` | 0 | `ioctl failed: ...` |
  | `-l -f /dev/null` | 0 | `\|Id      \|Curr \|Def. \|Min  \|Max  \|Name` |
  | `-c 1 -f /dev/null` | 0 | `ioctl failed: ...` |

- **OHOS 特有断言 3 项**（对 ELF 文件直接解析，不是装饰）：
  1. `e_machine == EM_AARCH64(183)`：包内二进制必须是 AArch64 ELF；
  2. `e_type == ET_DYN`：必须是 PIE（OHOS 硬化基线，R7）；
  3. 解析 `.dynamic` 的 `DT_NEEDED` 表，断言**不存在**任何含 `ncurses` 的条目——
     这是「静态链接 ncurses」这一 OHOS 关键决策的可执行证明（OHOS 加载器忽略
     `LD_LIBRARY_PATH`，动态链接会在纯净设备上直接起不来）。
- R34 证据：`test()` 先检查包内 `bin/matroxset` 与已编译的测试二进制存在，再 `self.run`
  真正执行；删掉 `bin/` 后 14 项全部失败（CI 的 L1e 破坏性反向测试即验证此点）。
- `test_package` 用 `generators = "VirtualRunEnv"` + `env="conanrun"`，并显式传
  `MATROXSET_BIN=<包内绝对路径>`，双保险定位被测二进制。

## 关键取证方法教训（可复用）
- 凡是要断言「平台缺某个符号」，必须先证明**取证工具自己可用**（`nm ... | wc -l`
  得到 0 时先怀疑工具，而不是断言「一个都没有」），并确认取的是**真实运行期/
  归档**而不是链接桩。本轮第一轮就因为「guest musl 缺 `__open_chk`」而误判成
  「OHOS 缺 `__open_chk`」，差点白丢一个硬化标志。
- 同源坑：本仓 T017（`arc4random`）、T137（`_FORTIFY_SOURCE`）都是
  「WSL/容器里的运行期 ≠ 真 OHOS」的同一族错误。

## 已知非阻塞项
- **L2 上游版本探测**：`matroxset` 没有 `-V` / `--version`，`-h` 打印 usage 后由
  `static int help(void)` **`return 98`**（源码里没有任何 `exit()` 调用），经
  `case 'h': return help();` 传出 → 退出码 98（非 0）。按规则「源码原生行为，不为了
  过门禁而添加上游不存在的 CLI」，此处预期为**非阻塞 warn**，已在 notes 中登记理由。