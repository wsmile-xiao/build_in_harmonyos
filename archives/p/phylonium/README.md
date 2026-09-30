# phylonium

快速估算亲缘基因组之间进化距离的命令行工具，输出 PHYLIP 格式对称距离矩阵，可直接交给
`phylip neighbor` / mattools `mat nj` 等邻接法实现建树。

- 上游：https://github.com/EvolBioInf/phylonium
- 许可证：GPL-3.0-or-later
- 类型：命令行工具（tool）
- 论文：Klötzl & Haubold, *Bioinformatics* 36(7):2040–2046, 2020

## 用法

每个 FASTA 文件代表一个基因组（文件内多条序列视为同一基因组的 contigs），
输出行 ID 是去掉 `.fasta/.fa/.fas` 扩展名的文件名：

```sh
phylonium Seq1.fasta Seq2.fasta
2
Seq1  0.0000e+00  1.0000e-01
Seq2  1.0000e-01  0.0000e+00
```

距离为 0 表示两个输入相同；打印 `nan` 表示该对被判定为太短（<200bp）或太分散（K>0.5），
方法无法给出估计。常用选项：`-r` 指定参考基因组、`-2` 两趟算法、`-b N` bootstrap、
`-v` 打印覆盖率/比对信息、`--version`。

## OHOS 适配要点

- 关闭 x86 SIMD 与 AVX-512 两条代码路径（上游两个开关默认开启且不探测 CPU）。
- 构建期 `autoreconf -fi -Im4` 自举（官方 tag 件不含 `configure`，也不含
  `configure.ac` 所引用的 `config.hin` 模板）。
- 唯一硬依赖 `libdivsufsort64`，由 Conan 依赖 `libdivsufsort/2.0.1` 提供。
- 上游 2 个 automake 注册测试（`test/simple.sh`、`test/unittests`）在构建中真实执行；
  交付后的行为断言在 `test_package/`（真实调用 `bin/phylonium`）。
- 许可证文本随配方发布（上游仓库不提供许可证文件）。

## 依赖

- 构建：Autotools（autoconf/automake/libtool 由 `tool_requires` 提供）
- 链接：`libdivsufsort/2.0.1`（static 制品）
- 运行：无额外运行时依赖（OpenMP 在真机工具链上探测通过并已启用）

## 参考

- 源码仓库：https://github.com/EvolBioInf/phylonium
- 手册页：`share/man/man1/phylonium.1`；上游 `documentation/manual.pdf` 一并打包
- 版本细节见 `1.7/notes.md`
