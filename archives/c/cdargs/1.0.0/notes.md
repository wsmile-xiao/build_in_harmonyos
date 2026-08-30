# cdargs 1.0.0 HarmonyOS PC 适配说明

## 软件信息

- 软件：cdargs（软件包版本 1.0.0，对应当前任务 4063；上游发行版为 cdargs 1.35）
- 上游：http://www.skamphausen.de/cgi-bin/ska/CDargs
- 许可证：GPL-2.0-only
- 构建系统：直接 clang++ 编译单一翻译单元（弃用 autotools make，见下）
- 类型：应用（bin/cdargs），ncurses 终端 UI 工具

## 源码

Debian 源包 cdargs_1.35.orig.tar.gz（上游 1.35 官方 tarball）：

- URL: http://deb.debian.org/debian/pool/main/c/cdargs/cdargs_1.35.orig.tar.gz
- SHA256: ee35a8887c2379c9664b277eaed9b353887d89480d5749c9ad957adf9c57ed2c

## 依赖

- ncurses/6.6（OHOS 制品仓，宽字符静态库 libncursesw.a；头文件 include/ncurses.h、include/curses.h）

## HarmonyOS PC 适配

1. **E011 方案**（calcurse 同款实证）：源码复制到非 HMDFS `/data/storage/el2/base/cache/cdargs-src` 再编译，避免 HMDFS 执行位被剥导致二进制不可执行。
2. **直接 clang++ 编译**（弃用 autotools make）：`clang++ -DHAVE_NCURSES_H -I<ncurses>/include src/cdargs.cc -o src/cdargs -L<ncurses>/lib -lncursesw`。cdargs 无 config.h、无 configure 生成宏，单一翻译单元直接编译等价。
3. **弃用 autotools 的原因（CI 实证）**：cdargs 1.35 的 automake 1.4-p5 递归构建在 OHOS worker 上生成子 Makefile 时 `@top_srcdir@` 被环境污染成二进制乱码（`config.status` 替换出 `top_srcdir = '/\xef\xbf\xbd-v\x11...flag'`），make 进入 `contrib/`（SUBDIRS 首项）重建 `Makefile.in` 时对不存在的乱码路径报 `No rule to make target`——二进制在 `src/` 根本未构建。本地用假编译器复现 configure：正常环境 `top_srcdir = ..` 干净，乱码为 worker 环境特有。直接编译不依赖生成的 Makefile，确定性构建。
4. **编译器**：显式 `CXX=clang++`（OHOS 工具链，经 tools.build:compiler_executables 或 PATH 解析）。
5. **ncurses**：`-DHAVE_NCURSES_H` 走 `<ncurses.h>`（宽字符版，--enable-overwrite 顶层安装），`-lncursesw` 静态库。
6. **ELF 签名**：package() 用 binary-sign-tool self-sign（SHA256withECDSA），使二进制可在 OHOS 上执行。

## 产物

- bin/cdargs
- share/man/man1/cdargs.1
- licenses/COPYING

## 测试

上游 1.35 tarball 无测试套件。

test_package 提供消费者冒烟测试（test_cdargs.py）：

- 真实运行打包二进制：`cdargs -f <list> -a <absdir>` 非交互书签添加（源码中 -a/--add 分支在 init_curses() 之前 exit，无头可执行）
- 校验书签文件写入绝对路径（书签文件格式：每行 `<desc> <path>`）
