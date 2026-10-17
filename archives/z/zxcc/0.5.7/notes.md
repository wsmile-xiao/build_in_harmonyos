# zxcc 0.5.7 适配笔记

## 编译环境
- 构建系统: autotools（递归构建：顶层 + cpmio + cpmredir 子包）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（aarch64-linux-ohos，本机鸿蒙PC 真机）
- 状态: published
- 适配路径: A（认领库）

## 编译步骤

```bash
# 探索性编译（模式 B）
CC=clang CPPFLAGS="-I$ncurses_prefix/include" LDFLAGS="-L$ncurses_prefix/lib" \
  LIBS="-lncursesw" ./configure --prefix=<prefix>
make -j2 && make install DESTDIR=<staging>
```

固化后由 `conan create`（W3）在干净环境复现：configure → make → install，
ncurses/6.5 通过 Conan 依赖注入（AutotoolsToolchain 自动传递
CPPFLAGS/LDFLAGS/LIBS）。

## R51 上游测试三步法

1. **清点**：源码树无 tests/、无 ctest/pytest 注册、Makefile.am 未定义
   TESTS 变量（顶层/cpmio/cpmredir/Z80/bin 五个 Makefile 均无）→ 上游
   测试用例数 = 0。
2. **运行**：真机实测 `make check` → 五个子目录全部
   "Nothing to be done for 'check'"（exit 0）。证据：无任何测试目标可跑。
3. **回填**：上游 0 用例，通过率 N/A；按 R51 自行补齐测试——
   test_package 提供真实执行型冒烟测试（`zxcc` 无参运行 + `zxas` 经
   PATH 调 zxcc 包装器），conan create/test_package 自动执行，
   2/2 通过，通过率 100%。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 2009/2012 版 config.guess 无 HarmonyOS 分支（E007） | 补丁添加 `*:HarmonyOS:*:*` case 分支 → aarch64-unknown-linux-ohos；config.sub 增加 aarch64 与 linux-ohos 识别 |
| 2 | config.status 报 `can't create ./confXXXX/subs1.awk: Permission denied` | HMDFS 上 `umask 077` 创建的目录属主权限位丢失（drwx--S---） | 补丁去掉 configure（顶层+两个子包）内的私有 umask |
| 3 | cpmio.c 编译报 `stdscr` 未定义 | 上游实际依赖 ncurses 头/库，configure 只检测 `-lncurses`（非宽字符名） | 依赖 conan ncurses/6.5；AutotoolsToolchain 注入头/库路径（libncursesw） |
| 4 | `zxcc: Cannot locate bios.bin`（探索期冒烟） | bios.bin 安装在 `<prefix>/lib/cpm/bin80/`，探索期 DESTDIR staging 前缀与编译期前缀不一致 | 仅探索期现象；conan 包前缀自包含（BINDIR80 指向包内路径），test_package 实测正常 |
| 5 | conan get() sha256 校验失败 | seasip.info 对 gzip 响应带 Content-Encoding，requests 客户端自动解压后字节流与磁盘文件不一致 | 改用官方 GitHub 仓库 agn453/ZXCC 的 0.5.7 tag 源码包（字节稳定） |
| 6 | libtool 报 `syntax error near unexpected token }` | configure 在 mksh(/bin/sh) 下探测出 korn-shell 能力，生成的 libtool 含 mksh 才能解析的引号与 `print -r --` 内建 | configure/make 全程以 bash 运行 + 后处理生成 libtool（修 shebang、重引号 archive_expsym_cmds、print→printf） |
| 7 | libtool `Failed to create .libs`（目录名混入换行/引号） | ECHO 替换值含单引号，随变量无引号展开成字面量字符混入路径 | ECHO 用 libtool 自带回退形式 `printf %s\n` |

## 源码修改

- `patches/0001-autotools-ohos-support.patch`：
  - configure / cpmio/configure / cpmredir/configure：`umask 077 && mktemp` → `mktemp`、`(umask 077 && mkdir "$tmp")` → `mkdir "$tmp"`（平台可移植性修复，无宏注入）
  - config/config.guess 等 3 份：HarmonyOS 系统识别 case 分支（无 `__OHOS__` 宏）
  - config/config.sub 等 3 份：aarch64 CPU 识别 + `-linux-ohos*` OS 识别

## 依赖版本

- ncurses/6.5（ohpcd 制品仓已发布，conan download 实测拉取成功）

## 验证结果

```bash
conan create archives/z/zxcc/0.5.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → build/test_package 全绿，详见 reports/
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/zxcc | CP/M 模拟器驱动（Hi-Tech C / DResearch 工具包装器） |
| bin/zxc, zxas, zxlink, zxlibr | 交叉开发工具入口 |
| lib/libcpmio.a, lib/libcpmredir.a | 静态辅助库 |
| lib/cpm/bin80/*.bin | 运行期 CP/M BIOS 数据 |
| share/zxcc/zxcc.doc | 文档 |

## 注意事项

- zxcc 运行真正的编译需要用户额外安装 CP/M 侧 Hi-Tech C 编译器 .com
  文件（BINDIR80/LIBDIR80/INCDIR80）；包本身交付模拟器与工具骨架。
- 命令行工具 → 软件级 `commands.json` 已声明（R38/PF8）。
