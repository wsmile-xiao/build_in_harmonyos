# nettoe 1.5.1 适配笔记

## 编译环境
- 构建系统: Autotools (configure.ac + Makefile.am)
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4
- 目标平台: HarmonyOS PC (aarch64-unknown-linux-ohos)
- 状态: built (conan create 验证通过 + finish 完成；未上传制品仓，故为 built 而非 published)

## 软件信息
- 名称: nettoe (netToe)
- 版本: 1.5.1
- 描述: 文本界面的井字棋游戏，支持网络对战
- 许可证: GPL-2.0
- 上游仓库: https://github.com/RobertBerger/nettoe (GitHub 官方仓库)
- SourceForge: http://nettoe.sourceforge.net
- 源码文件: nettoe.c, ai.c, board.c, matrices.c, misc.c, network.c, terminal.c
- 依赖: ncurses (静态链接, R26)

## 源码 URL 决策（R39 官方源，缺陷5修复说明）⭐

**结论：上游无 tag，保留官方 master 快照。**

经 GitHub API 实测确认（2026-09-08）：
- `GET /repos/RobertBerger/nettoe/tags` → `[]`（空列表，无任何版本 tag）
- `GET /repos/RobertBerger/nettoe/releases` → 0 个 release
- 仓库 default_branch = master，最后 push 时间 2021-01-23

`configure.ac` 中声明的版本号 `1.5.1` 仅存在于源码内部，上游从未以
`v1.5.1` 或 `1.5.1` 打过 tag。因此 conandata.yml 使用官方 master 快照：

```
https://github.com/RobertBerger/nettoe/archive/refs/heads/master.tar.gz
sha256: a0f0089b59e8a7b1cc825557fcb31308ccf58bac450e156297334230707d1838
```

sha256 已实测验证（直连 GitHub 下载 154307 字节，与镜像 ghfast.top 下载
一致）。依据 R39「源码 URL 必须为官方源」——GitHub 官方仓库即官方源，
符合要求。

## R49 依赖注入决策（缺陷6修复说明）⭐

**结论：已改为 build_folder 私有 prefix 模式。**

初版 conanfile.py 的 `generate()` 直接拼接 ncurses package_folder 路径到
CPPFLAGS/LDFLAGS：

```python
ncurses_cpp = os.path.join(self.dependencies["ncurses"].package_folder, "include")
ncurses_lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
tc.configure_args.append(f"CPPFLAGS=-I{ncurses_cpp}")
tc.configure_args.append(f"LDFLAGS=-L{ncurses_lib}")
```

该实现存在以下问题（按 R49/E524 审查）：
1. **直接依赖 package_folder 布局**：依赖包 package_folder 的 include/lib
   目录布局由 ncurses 配方决定，若布局变化或含多架构子目录则不可靠。
2. **未提供 configure 所需的库名**：nettoe configure.ac 用
   `AC_CHECK_LIB([ncurses], [setupterm])` 与 `AC_CHECK_LIB([tinfo],
   [setupterm])` 检测，但 Conan ncurses/6.5 包只提供 `libncursesw.a`
   （wide-char 版），无 `libncurses.a`/`libtinfo.a`——直接指 package_folder
   会导致 `-lncurses`/`-ltinfo` 链接失败。
3. **未遵循 R49 推荐模式**：R49 要求依赖注入目标 =
   `os.path.join(self.build_folder, "prefix")`，CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH
   全指向 build_folder 私有 prefix，禁止注入共享 /usr/local（E524：19 轮
   CI 全挂根因）。

**修复方案**（参考 archives/a/asterisk-srtp/22.10.1/conanfile.py）：
- `generate()` 中创建 `build_folder/prefix` 私有 prefix
- 将 ncurses include 头文件复制到 `prefix/include`
- 将 `libncursesw.a` 复制为 `prefix/lib/libncurses.a`、`prefix/lib/libtinfo.a`
  （实体副本，非软链接——HMDFS 上软链接不可靠），满足 configure 的
  `-lncurses`/`-ltinfo` 检测
- CPPFLAGS/LDFLAGS 指向 `prefix/include`、`prefix/lib`（私有 prefix，隔离干净）
- `--enable-static --disable-shared`（R26：ncurses 系统同名库必须静态链接）

这样每个 CI worker 的构建完全隔离，不污染共享 SYS_PREFIX，与 asterisk-srtp
的成熟做法一致。

## 编译步骤

```bash
# 1. configure（conanfile.py generate() 注入私有 prefix + ncurses 副本）
./configure --prefix=/usr/local \
    CPPFLAGS="-I<build_folder>/prefix/include" \
    LDFLAGS="-L<build_folder>/prefix/lib"

# 2. 编译
make -j1

# 3. 安装
make install DESTDIR=$TEST_PREFIX

# 4. 测试
make check  # 1 test passed (terminfo)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | config.guess 2012 版本无 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 补丁 + 手动添加 `echo GUESS; exit` 提前退出 |
| 2 | config.sub 不支持 ohos 三元组 | config.sub 缺少 linux-ohos 条目 | 手动在 config.sub 中添加 linux-ohos* 到匹配列表 |
| 3 | config.status 创建临时目录失败 | HMDFS 上 `umask 077` 创建的目录权限为 `drwx--S---`，文件写入被拒绝 | 修改 config.status/configure 中 `umask 077` 为 `umask 022` |
| 4 | ncurses.h 头文件编译检测失败 | ncurses 头文件缺少 ncurses_dll.h | 复制 ncurses 所有头文件到 include/ |
| 5 | ncurses 库只有 libncursesw.a | conan ncurses/6.5 使用 --enable-widec 编译宽字符版 | 在 build_folder 私有 prefix 中创建 libncurses.a 和 libtinfo.a 副本（R49） |
| 6 | 官方仓库 URL 404 | 任务给出的 oppenheimer/nettoe 不存在 | 搜索确认 RobertBerger/nettoe 是唯一可用仓库，使用该 URL |
| 7 | ghfast.top 镜像下载超时 | 首次 conan-verify 时 ghfast.top 网络瞬时不可达 | 重试 conan-verify（镜像现可达，sha256 与直连一致） |

## 源码修改

无补丁 (patches/ 为空)。编译前需修改:
- `build-aux/config.guess`: 添加 HarmonyOS 识别 + 早期退出
- `build-aux/config.sub`: 添加 linux-ohos 支持
- `config.status`/`configure`: umask 077 → umask 022 (HMDFS 兼容)

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| ncurses | 6.5 | static (.a) | 终端界面库，宽字符版 libncursesw.a |
| clang | 15.0.4 | 编译器 | LLVM/Clang |

## 验证结果

```bash
$ ./src/nettoe --version
netToe 1.5.1 the enhanced, and networked, Tic Tac Toe game.

$ make check
1 test passed (terminfo)
```

## 配方说明
- package_type: application (可执行文件，非库)
- ncurses 通过 Conan 依赖，静态链接 (R26)
- 依赖注入使用 build_folder 私有 prefix 模式 (R49/E524)
- commands.json 声明 nettoe 可执行文件 (R38)
- conandata.yml URL 使用官方 GitHub 仓库 master 快照 (R39，上游无 tag)
- test_package 含 src/example.c 实质测试（R34：编译 example.c 并执行
  nettoe --version 验证输出 netToe 1.5.1）
---

**编译结束**: 2026-09-08 20:07
**最终状态**: built
