# cgvg

cg/vg — Code Grep / Vi Grepped 开发者工具对（纯 Perl，无 C/C++ 源码）：
`cg` 递归搜索源码并把匹配写入日志文件供回放，`vg` 用编辑器直接打开
搜索结果对应的文件与行号。上游 1.6.3（2014），官方站点 uzix.org 已失效，
本包源码取 Debian pool 的 pristine orig 包（与上游 1.6.3 逐位一致）。

## 功能
- `cg <pattern>`: 递归搜索（默认目标 Make*/\.c\.h\.s\.cc\.pl\.py\.java 等），
  输出 `序号 文件 行号 内容`，结果缓存于 ~/.cgvg 并在 ~/.cglast 留最近一次
- `cg`: 无参回放最近一次搜索结果；`cg -i` 忽略大小写；`cg -l` 强制回放
- `vg <n>`: 用 $EDITOR（默认 vi）打开第 n 条匹配的文件并定位到行号
- 支持 ~/.cgvgrc 自定义颜色/分页/编辑器

## HarmonyOS PC (arm64) 适配说明
- 纯 Perl 脚本包：autotools 壳只做 shebang/@VERSION@/路径替换与安装。
  配方采用**直接文件安装**，不做 configure（避免把构建机绝对 perl 路径与
  configure 期 datadir 烤进脚本，保证 Conan 包可重定位）。
- 脚本 shebang 为 `#!/usr/bin/env perl`：运行期从 PATH 解析解释器。
  HarmonyOS PC 系统自带 perl.org 5.42.0（`/data/service/hnp/bin/perl`）。
- `cgvg-common.pl`/`cgvgrc-example` 与脚本同目录安装（上游脚本首个 @INC
  项即 dirname($0)，语义兼容）。
- 运行时依赖：PATH 上有 perl 5 解释器（OHOS PC 预装，无需额外安装）。
- 注意：`vg` 会检查 $EDITOR（默认 vi）；OHOS 无 vi 时请先
  `export EDITOR=vim`（或其他已装编辑器）。`cg`/`vg` 无 --version/--help
  选项（上游如此），运行 `cg` 前目录中需有可搜索文本文件，HOME 需可写
  （用于 ~/.cgvg 日志）。

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cgvg 1.6.3
```

## 验证
```bash
cg hello            # 期望: 输出匹配序号/文件/行号, rc=0
cg -l               # 期望: 回放最近一次搜索
EDITOR=vi vg 0      # 期望: vi 打开匹配文件并定位到行号
```
