# bamclipper

BAMClipper 是一个按 BEDPE 引物坐标从 SAM/BAM 比对中移除 PCR 引物序列的软剪切工具。

## OpenHarmony 适配

- 纯 Bash/Perl 脚本，无本地编译产物。
- `bamclipper.sh` 是主入口，`clipprimer.pl` 和 `injectseparator.pl` 是辅助脚本。
- 运行时依赖 Conan 包 `bash/5.3`、`perl/5.42.2.1`、`samtools/1.21` 和 `parallel/20260522`。
- 配方将三个脚本安装到包内 `bin/`，并通过 Conan 运行环境导出入口目录。
- 上游 v1.0.0 没有独立测试目录、测试目标或测试样例，因此适配包补充真实的 BAM 工作流消费者测试。

## 使用

```bash
bamclipper.sh -b sample.bam -p primers.bedpe -n 1
```

输入 BAM 必须已经建立索引，BEDPE 文件提供引物对的基因组坐标。工具会生成
`sample.primerclipped.bam` 及其索引文件。

## 许可证

MIT License，版权归 Chun Hang Au 所有。

## 上游

- Homepage: https://github.com/tommyau/bamclipper
- Version: v1.0.0
