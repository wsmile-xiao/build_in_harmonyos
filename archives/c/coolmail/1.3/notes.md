# coolmail 1.3 适配笔记

## 编译环境

- 构建系统: makefile（手写 GNU Makefile，无 configure 脚本）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，来自 OHOS profile 的 `tools.build:compiler_executables`）
- 目标: OHOS / aarch64（`archives/c/coolmail/1.3`，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

上游 Makefile 没有 configure 阶段，全部配置靠 make 变量；配方在 `build()` 里直接以
命令行变量覆盖 Makefile 内写死的路径（不改上游文件）：

```sh
make -j1 CC="<clang>" CFLAGS="-O2" \
     INCLUDES="-I<每个依赖包的 include>" \
     LIB_DIRS="-L<每个依赖包的 lib>" \
     LIBS="-L<每个依赖包的 lib> -lXt -lX11 -lm" \
     AUDIO= AUDIO_MODULE=
```

- 直接依赖只有 `libxt/1.3.1`（`<X11/Intrinsic.h>`、`<X11/StringDefs.h>` 来自它）；
  `libx11/1.8.13`、`libsm/1.2.6`、`libice/1.1.2`、`xorgproto/2025.1`、`libxcb/1.17.0`、
  `libxau/1.0.11`、`libxdmcp/1.1.5` 均由 libxt 传递。
- `package()` 不调用 `make install`：上游 `install` 目标先探测 `[ -w $(BINDIR) ]`，
  不可写时只打印 `ERROR: Unable to write to ...` 且不落任何文件（退出码仍为 0），
  在 HMDFS 权限语义下不可靠；改为等价的显式 `copy`（`bin/coolmail`、
  `share/man/man1/coolmail.1`、`share/X11/app-defaults/Coolmail`、`licenses/COPYRIGHT`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `coolmail.c:107` 报 `call to undeclared function 'cuserid'` + `incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（hard error） | `cuserid()` 在 POSIX.1-2001 已删除；OHOS musl 头文件保留 `L_cuserid` 宏（`stdio.h:173`）却不声明该函数，`libc.so` 也不导出（`nm -D` 为空），符号只在静态 `libc.a`（`cuserid.o`）。无声明即按 C89 隐式声明为返回 `int`，传给 `strcat` 的 `const char *` 形参直接报错 | `patches/0001`：删除 `char username[L_cuserid]` 与 `cuserid()` 调用，改为 `getpwuid(getuid())` → `getlogin()` → `getenv("LOGNAME")` → `getenv("USER")` → `"unknown"` 回退链（判空是必须的：OHOS 上 `getpwuid()` 可返回 NULL，见知识条目 E338） |
| 2 | `strcat` / `strcmp` / `strncpy` 全部报 `call to undeclared library function ...` | 上游把 `<string.h>` 放在 `#ifdef AUDIO` 内；无 AUDIO 构建时字符串函数全部走隐式声明（C99+ 为错误类别） | `patches/0001`：`<string.h>` 改为无条件包含；`patches/0002`：`render1.c` 同样补 `<string.h>` |
| 3 | `call to undeclared function 'disp_sync'`（未打补丁的上游源码在 `coolmail.c:469`；应用 `patches/0001` 后该调用位于第 484 行） | `coolmail.c` 只包含 `render1.h`/`mailbox.h`，`disp_sync()` 的声明在 `display_list.h` | `patches/0001`：补 `#include "display_list.h"` |
| 4 | 无法加入 `libxext`：`libxext/6.4.0.1` 的已发布 binary 与 `libx11/1.8.13` 图不匹配（`Missing binary ... package_id eab79208...`），`libxext/6.4.0` 又把 `libx11/6.4.0` 钉死 | 制品仓中 `libxext` 系列的 binary 都是按 `libx11/6.4.0` 计算的 package_id，与 `libxt/1.3.1` 所需的 `libx11/1.8.13` 冲突 | 先核对 `nm -D --undefined-only bin/coolmail`：产物**不含任何 Xext 符号**（源码只在注释里提到 Xmu/Xext），上游 Makefile 的 `-lXext` 是多余链接；从 `LIBS` 去掉该标志（不改上游 Makefile） |
| 5 | 上游 digitized audio 后端无法编译 | `audio.c` 的声音实现是 OSS：`#ifdef linux` + `<linux/soundcard.h>`、`/dev/mixer`、`/dev/dsp`；OHOS SDK 无该头文件，设备也无这些设备节点 | 采用上游 README 明确记载的配置：`AUDIO=`、`AUDIO_MODULE=` 置空（声音关闭）。代价：`-af`/`-vol` 两个选项在无 AUDIO 构建中不可用（上游固有行为） |
| 6 | 登录名相关代码在真机 `$HOME` 下无 `getpwuid()` 记录 | 设备 `/etc/passwd` 与 uid 映射不同于常规 Linux | 回退链已覆盖（`getenv("USER"/"LOGNAME")`），不会得到 NULL |

## 源码修改

`patches/0001-coolmail.c.patch`（`type: portability`，`platform_only: false`）：

1. `<string.h>` 从 `#ifdef AUDIO` 块内移出，与新增的 `<pwd.h>` 一起无条件包含；
2. 删除 `char username[L_cuserid];`；
3. `strcat(mailfile_str, cuserid(username));` 替换为 `getpwuid`/`getlogin`/环境变量回退链；
4. 补 `#include "display_list.h"`（`disp_sync()` 声明）。

`patches/0002-render1.c.patch`（`type: portability`，`platform_only: false`）：
`render1.c` 补 `#include <string.h>`（`rend_init()` 中的 `strcmp()`）。

两个补丁都不含 `__OHOS__` 条件编译，对 glibc 同样成立，可向上游提交。

## 依赖版本

- `libxt/1.3.1`（直接）
- 传递：`libx11/1.8.13`、`libsm/1.2.6`、`libice/1.1.2`、`xorgproto/2025.1`、`libxcb/1.17.0`、`libxau/1.0.11`、`libxdmcp/1.1.5`

运行期 DT_NEEDED：`libXt.so.6`、`libX11.so.6`、`libc.so`；libXt 再需要 `libSM.so.6`/`libICE.so.6`，
libX11 再需要 `libxcb.so.1`/`libXau.so.6`/`libXdmcp.so.6`。OHOS 不预装 X 库，消费方需保证这些
libdir 在 `LD_LIBRARY_PATH` 中（不带时实测 `rc=127` + `Error loading shared library libXt.so.6`）。

## 验证结果

```bash
# 1. 干净构建 + test_package（缓存已按工作流第 7.2 节四步清除）
conan create archives/c/coolmail/1.3 \
  -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<abs>/ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → EXIT=0；日志含 Uncompressing / Apply patch ×2 / Calling build() / RUN: make
#   test_package 7/7（脚本运行期累加计数，末行数字恒等于日志中 OK: 行数）：
#   OK: packaged binary present and executable / coolmail -h exited 0 / usage banner present /
#   documented options listed / headless run exited 1 after loading the X11/Xt chain /
#   man page installed / X11 app-defaults installed → "coolmail smoke test OK (7 checks)"

# 2. conan-verify（G0-G4 / L2 / L4 / L5）
python3 scripts/ohc-run.py conan-verify coolmail 1.3 --project-dir <worktree>
# → ✅ 配方验证通过；G1/G2/G3 PASS；G4 与 L2/L4/L5 打印「跳过（无 cache 路径）」
#   （application 型包已知工具缺陷），已人工补测：reports/conan-verify-supplement.md
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/coolmail` | 51648 字节 | ELF 64-bit LSB arm64，PIE + NX + RELRO + BIND_NOW，动态链接 `/lib/ld-musl-aarch64.so.1` |
| `share/man/man1/coolmail.1` | 2649 字节 | 上游 `coolmail.man` |
| `share/X11/app-defaults/Coolmail` | 277 字节 | 上游 `Coolmail.ad` 资源默认值 |
| `licenses/COPYRIGHT` | 1065 字节 | 上游许可证（GPL-1.0-or-later） |

## 注意事项

- **本包是 GUI 程序，但设备与 CI 都没有 X server**：镜像内无 `Xorg`/`Xvfb`/`Xwayland`
  可执行文件，制品仓也未发布 OHOS `xorg-server`，因此窗口、动画、邮箱轮询与点击
  启动邮件阅读器这几条路径无法在本环境运行；测试覆盖命令行路径（`-h`）与
  Xt 初始化失败路径（无 `DISPLAY` 时的 `Can't open display`）。这与先例
  `archives/x/xeyes/1.3.1`、`archives/n/ncview/2.1.11` 采用同一口径。
- 上游 Makefile 的 `all` 目标在结尾会执行注释行 `# Done.`，构建成功即打印 `# Done.`；
  失败判定看退出码，不要以输出文本为准。
- `coolmail -h` 是唯一不进入 Xt 初始化的路径，也是 L2 冒烟门禁能通过的路径
  （`--version` 不存在，`--help` 也不存在；上游只支持单横线选项）。
