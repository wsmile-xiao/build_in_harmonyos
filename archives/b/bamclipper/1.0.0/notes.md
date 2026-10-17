# bamclipper 1.0.0 适配笔记

## 上游信息

- 上游仓库: https://github.com/tommyau/bamclipper
- 上游版本: v1.0.0
- 源码归档: `https://codeload.github.com/tommyau/bamclipper/tar.gz/refs/tags/v1.0.0`
- SHA256: `aa43e4f9cf6b1fb58ac2c6329acc9870e9522e5ba20286b50312ccf89a18f2fc`
- 许可证: MIT
- 构建类型: custom / script-only

## 上游测试审计

上游 v1.0.0 归档只包含 `README.md`、`LICENSE`、`bamclipper.sh`、`clipprimer.pl` 和
`injectseparator.pl`，没有 `tests/`、`test/`、`testsuite/` 目录，也没有 Makefile、测试目标或测试样例。
因此不存在需要保留和执行的上游测试资源；适配测试全部作为消费者测试单独统计。

## 依赖

- `bash/5.3`: 执行主入口脚本，避免依赖 Worker 系统 Bash。
- `perl/5.42.2.1`: 执行 Perl 辅助脚本。
- `samtools/1.21`: 读取、排序、转换和索引 BAM。
- `parallel/20260522`: 并行处理 `clipprimer.pl` 输入流。

四个依赖均已先行合入并可从 `ohpcd` Conan 远端解析。

## 配方实现

1. `source()` 下载 SHA256 锁定的 GitHub v1.0.0 归档。
2. 应用最小可移植性补丁：初始化必需选项、修正 `getopts`、引用用户路径，并通过环境变量安全传递 GNU Parallel worker 参数。
3. `build()` 使用 Conan Bash 检查主脚本语法，并使用 Conan Perl 检查两个 Perl 辅助脚本。
4. `package()` 将三个上游脚本、README 和 LICENSE 安装到包内目录。
5. `package_info()` 导出包内 `bin/`，使消费者可直接调用 `bamclipper.sh`。
6. test_package 从 Conan 依赖对象获取精确的 bamclipper、Bash、samtools、parallel 和 Perl 路径，避免系统 PATH 混用。

## 适配测试

| 编号 | 类型 | 内容 |
|---|---|---|
| 1 | 包内容 | 验证三个入口脚本存在且可执行，并验证缺少必需参数时返回错误 |
| 2 | 消费者集成 | 创建真实 SAM/BEDPE 输入，转换为索引 BAM，运行 BAMClipper，断言正反向 CIGAR 分别由 `20M` 变为 `10S10M` 和 `10M10S`；同时验证输出索引和 `injectseparator.pl` 的配对分隔行为 |

测试不虚增计数：同一个 BAM 工作流中的版本、索引、记录数和字段检查属于同一消费者集成测试。

## 验证结果

- `conan create`: 通过。
- 包内容与参数错误测试：1/1 通过。
- BAM 文件消费者工作流：1/1 通过，正反向 CIGAR 分别验证为 `10S10M` 和 `10M10S`，输出 BAM/索引有效，并验证连续 read pair 分隔。
- W3: L0/L1/L2/L4/L5 全部通过，`Pass rate: 100.0% (1/1)`。
- L2 对 `bamclipper.sh` 和 `clipprimer.pl` 的 `--version/--help` 为非阻塞告警；上游没有实现这些选项，真实消费者工作流已通过。
---

**编译结束**: 2026-08-25 20:55
**最终状态**: built
