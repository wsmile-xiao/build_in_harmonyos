# SweeD — 选择性清除检测

`SweeD` 实现了基于**位点频率谱（SFS）**的极大似然方法，用于在基因组数据中检测
选择性清除（selective sweep）。它是对 Nielsen 等（2005）SweepFinder 工具的改进
重实现，支持顺序、多线程（PTHREADS）与 MPFR 等多种构建变体。

## 主要功能

- 从对齐文件（FASTA/MAF/VCF/MS/MACS 等）或输入 SFS 计算各位置的复合似然比（CLR）。
- 可用 `-grid` 指定网格点数，`-folded` 使用折叠 SFS，`-threads` 控制线程数。
- 输出报告、SFS、SF 与警告文件。

## OHOS 适配要点

- **纯 Makefile 构建**：上游只提供 GCC 专用 `Makefile*.gcc`；本配方用顺序版
  `make -f Makefile.gcc CC=<ohos clang>`，链接 `-lm`。
- **零三方依赖、零补丁**：无 configure，无外部库。
- 上游无 git tag，源码坐标以 Debian dfsg orig tarball（HTTPS）的 sha256 固定。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/SweeD` | 选择性清除检测程序（顺序版） |

## 参考资料

- 上游：<https://sco.h-its.org/exelixis/web/software/sweed/>
- 许可证：GPL-2.0-or-later
