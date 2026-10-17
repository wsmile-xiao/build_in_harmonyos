# allelecount 4.3.0 适配 notes

## 包信息

- 类型：C 工具（application，make 构建）
- 上游：https://github.com/cancerit/alleleCount （AGPL-3.0）
- 简介：NGS 拷贝数分析辅助工具，从 BAM/CRAM 统计指定位置各等位基因（ACGT）的覆盖数
- 依赖：htslib（静态 libhts.a 链接）+ pthread/z/bz2/lzma/m/dl

## 适配要点

1. **源码获取**：GitHub release tarball（cancerit/alleleCount v4.3.0）
2. **构建方式**：上游 `c/Makefile`
   - `make` 产出 `c/bin/alleleCounter`
   - 需要 `HTSLIB` 环境变量指向 htslib 包目录（Makefile 用 `$(HTSLOC)/libhts.a` 强制静态链接 libhts.a）
   - 注入 htslib include/lib 路径（`-I$(HTSLOC)/` + `-L$(HTSTMP)` 指向 symlink 的 libhts.a）
   - 链接库：-lhts -lpthread -lz -lbz2 -llzma -lm -ldl
3. **打包**：`bin/alleleCounter` 可执行文件
4. **依赖**：htslib/1.24-r0（制品仓已发布）

## 测试用例

- test_cli：`alleleCounter --help`（或运行方式验证）确认可执行文件可用

## 已知限制

- alleleCounter 实际处理 BAM/CRAM 需要真实测序数据文件，test 仅验证可执行与基本 CLI
