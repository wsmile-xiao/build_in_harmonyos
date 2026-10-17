# E670 — gengetopt 生成的命令行解析器只随 release tarball 发布

## 错误特征
```
make[…]: gengetopt: No such file or directory
make[…]: `src/shishi_cmd.c' is up to date.   （时间戳倒挂时的另一种表现：）
make[…]: gengetopt: inaccessible or not found
make *** [src/shishi_cmd.c] Error 127
```

## 触发条件
- 构建系统: autotools（`BUILT_SOURCES` 含 `*_cmd.c` / `*_cmd.h`）
- 阶段: make（编译前生成物阶段）
- 前提: 源来自 git 快照 / `/archive/` 归档（只有 `.ggo`），或 release tarball 解包后生成物 mtime 早于 `.ggo`

## 根因分析
GNU shishi 用 **gengetopt** 从 `*.ggo` 定义生成命令行解析器 `src/*_cmd.c`、`*_cmd.h`，
并在 `src/Makefile.am` 里登记为 `BUILT_SOURCES` + 显式规则（`shishi_cmd.c: $(srcdir)/shishi.ggo Makefile.am`）。
**release tarball 自带这些生成物**（shishi 1.0.3 实测 mtime 09:52 晚于 `.ggo` 08:02，make 不重算），
git 树只有 `.ggo`。设备与 CI worker 均无 `gengetopt`（`command -v gengetopt` 空，ohpcd 未发布该工具），
于是任何走 git 快照的源在 make 第一步就断链。

同族风险：gperf/bison/flex/autogen 生成物、gettext 的 `po/` 生成物——判据相同：
**生成物是否随源归档一起发布**。

## 解决方案

### 推荐方案
- conandata.yml `sources` 锚定**官方 release tarball** + sha256 实核（本例 `ftp.gnu.org/gnu/shishi/shishi-1.0.3.tar.gz`，sha256 `95798ffd…17e92`）。
- 打包/取源后核对生成物在位：`tar tzf <tarball> | grep -c "_cmd\.c"`。

### 禁止做法
- ❌ 用 git snapshot / GitHub `/archive/` 归档当源。
- ❌ 为了让 git 快照可构建而在设备/CI 上补装 gengetopt（设备 harmonybrew 有而 CI 没有 → 设备绿 CI 红，设备事实 §一.4）。
- ❌ `tool_requires("gengetopt/...")`——ohpcd 没有该包，会在 R36/W0 依赖闸断掉。

## 验证
```bash
command -v gengetopt || echo "gengetopt missing: source MUST be the release tarball"
tar tzf <release-tarball> | grep -c "_cmd\.c"   # >0 即生成物随包发布
```

## 关联条目
- 相邻: E676（同一包的 doc 时间戳链/makeinfo 断链）
- 同族工具缺失判据: 设备事实 §一.4（harmonybrew PATH 掩盖 CI 缺口）
