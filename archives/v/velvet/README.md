# velvet

Velvet：经典的 de Bruijn 图短读序列 de novo 组装器
（Zerbino & Birney, Genome Research 2008），产物为两个命令行工具
`velveth`（k-mer 哈希）与 `velvetg`（图组装）。

## OHOS 适配

- 上游为手写 Makefile（无 configure）；通过 make 命令行覆盖
  `CC`/`CFLAGS`/`LDFLAGS` 注入 OHOS 工具链与 Conan 依赖路径，
  覆盖同时剔除上游硬编码的 `-m64`，**无需任何源码补丁**。
- 显式构建 `velveth`/`velvetg` 目标，跳过 `doc`（需要 pdflatex）。
- 依赖 `zlib/1.3.1.1`（显式 `-fasta.gz`/`-fastq.gz` 输入经 zlib `gzopen`
  读取），不使用 `BUNDLEDZLIB`（third-party/zlib-1.2.3）。
- 上游官方测试套件 `tests/run-tests.sh`（5 个 `.t` 用例）已接入
  `conanfile.py build()`（`can_run` 守卫，OHOS worker 原生执行），并在
  test_package 中以消费者视角对安装产物完整重放。

## 构建产物

| 工具 | 用途 |
|------|------|
| `velveth` | 构建 k-mer 哈希表（Sequences/Roadmaps），组装第一步 |
| `velvetg` | de Bruijn 图组装，输出 contigs.fa |

## 验证

- 上游测试：5 个 `.t` 用例（runner 原生口径 NUMTESTS=5），全过
  （macOS 原生辅助验证 + OHOS CI worker 真机执行）。
- 鸿蒙特有测试：1 个端到端组装场景（velveth→velvetg 完整流程在
  HarmonyOS 上对安装产物执行并校验 contigs.fa）。

上游：https://github.com/dzerbino/velvet
