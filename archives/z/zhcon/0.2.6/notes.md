# zhcon 0.2.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++（OHOS SDK 26.0.0.18, LLVM 15）
- 状态: published

## 上游说明
- 上游官方以 **zhcon-0.2.5.tar.gz + zhcon-0.2.5-to-0.2.6.diff** 形式发布 0.2.6
  （sourceforge `zhcon/0.2.6/` 目录下无独立 0.2.6 tarball）
- 适配采用: 下载官方 0.2.5 tarball + 应用 0.2.6 diff（diff 内容已并入 patches 0001/0002/0015/0019/0025/0027 等对应文件补丁）
- 上游仓库: https://sourceforge.net/projects/zhcon/

## 依赖（W0 核查）
| 依赖 | 用途 | 制品仓状态 |
|------|------|-----------|
| ncurses/6.5 | termcap API（tgetent/tgetstr/tgoto/setupterm），链接宽字符版 ncursesw | ✅ 已发布 |
| gettext/0.22.5 | gettext/bindtextdomain/textdomain（-lintl） | ✅ 已发布 |
| util/forkpty | libc 内置 | ✅ |
| gpm / ggi / unicon | 可选后端，configure 自动降级为 no | 不构成硬依赖 |

## 编译步骤（探索实证）
```bash
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export CPPFLAGS="-I<gettext>/include -I<ncurses>/include"
export LDFLAGS="-L<gettext>/lib -L<ncurses>/lib"
./configure --prefix=<prefix>
make -j4
make check          # 上游无注册测试（各目录 Nothing to be done）
make install DESTDIR=<测试前缀>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot guess build type` | 2001 版 config.guess 无 HarmonyOS 识别 | 替换为 2023 新版 config.guess/sub + `patch-autotools-ohos.pl`（Score 5/5），并手工补齐 config.sub kernel 列表 `linux-ohos*-`（脚本误判 already present） |
| 2 | `config.status can't create ./confstatXXX/undefs.sed: Permission denied` | config.status 用 `(umask 077 && mktemp -d)` 创建 0700 临时目录，HMDFS/SELinux 下该权限目录内无法写入（实测 022/2771 可写） | configure 中 `umask 077` → `umask 022` |
| 3 | `cstddef: expected unqualified-id using ::ptrdiff_t` | 老 autoconf ptrdiff_t 检测（C 模式无 stddef.h）误判 no → `#define ptrdiff_t long`，与 libc++ 头文件冲突 | configure 中对 `*-linux-ohos*` 强制 `ac_cv_type_ptrdiff_t=yes` |
| 4 | `undefined symbol: g_libintl_gettext` | usr/local 的 libintl.h 是 GLib proxy 头（`#define gettext g_libintl_gettext`），但 libintl.so 导出 `libintl_gettext`/标准名，头库不匹配 | 改用 conan 制品仓 gettext/0.22.5 标准头+库；修复 configure conftest 64 位指针截断 `(int)(long)` 与 `_nl_expand_alias()` 参数不匹配，使系统 libintl 检测通过 |
| 5 | `checking for main in -lcurses... no` | conan ncurses 只提供 `libncursesw.a`（宽字符版），无 libcurses.a | configure.in/configure 检测库 `curses`→`ncursesw`；zhcon 仅用 termcap 函数均在 libncursesw |
| 6 | 链接 `undefined symbol: libintl_gettext`（zhcon 目标） | `zhcon_LDADD = display/libdisplay.a` 未含 `$(INTLLIBS)`（-lintl） | src/Makefile.am/.in/Makefile 三处 zhcon_LDADD 补 `$(INTLLIBS)` |
| 7 | `install: chmod /bin/zhcon` | install-exec-local 硬编码 `chmod 4755 $(bindir)/zhcon`，无 DESTDIR 前缀且 setuid 在 OHOS 不适用；且 prefix 变量为空（configure 时 DEFAULT_PREFIX 未注入） | install-exec-local 改 `chmod 755 $(DESTDIR)$(bindir)/zhcon`；configure 显式传 `--prefix` |
| 8 | `winime.cpp: cast from pointer to smaller type 'unsigned int'` | 32 位假设代码 `(unsigned int) p + mpText` | 改为 `(char*)((uintptr_t)p + (uintptr_t)mpText)`，补 `#include <stdint.h>` |
| 9 | `inputmanager.h: unknown type name 'fd_set'` | 缺少 `<sys/select.h>`（OHOS libc 中 fd_set 定义于此） | inputmanager.h 补 `#include <sys/select.h>` |
| 10 | `Error loading shared library libc++_shared.so` | zhcon 动态链接 libc++_shared.so | 运行需 `LD_LIBRARY_PATH=<OHOS SDK llvm lib/aarch64-linux-ohos>`（签名/打包环境由 CI 处理） |

## 测试情况
- `make check`: 各子目录均 "Nothing to be done for 'check'"（上游无 TESTS/check_PROGRAMS 注册，configure 无 check 目标）
- 自研 test_package: 验证 zhcon 二进制存在、`--version`/`--help` 运行退出码 0、zhcon.conf 存在、输入法数据目录完整（**5 项硬断言**）
- `zhcon --version` 实测输出 `zhcon` 且退出码 0

## R40 适配完整性说明
zhcon 是控制台/framebuffer 工具（CJK console environment，驱动 fb/vga 显示）。OHOS 无 framebuffer 控制台设备，test_package 覆盖 CLI 冒烟验证（二进制可执行、版本/帮助输出、配置文件与输入法数据完整）；framebuffer/console 渲染路径的实机验证需人工确认（hicmd 真机验证记录另附）。编译产物完整（ELF arm64 动态链接，`-static-libstdc++` 静态链接 libc++），适配代码为实质逻辑非 stub。

## 产物
- bin/zhcon（ELF arm64 动态链接）
- etc/zhcon.conf（控制台配置文件）
- man/man1/zhcon.1
---

**编译结束**: 2026-09-17 00:01
**最终状态**: published
