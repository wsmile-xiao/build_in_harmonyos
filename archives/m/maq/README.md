# maq

MAQ（Mapping and Assembly with Qualities）是短读比对 / 一致性序列组装 / SNP 检测套件，
作者 Heng Li（lh3），SourceForge 项目 [maq](https://maq.sourceforge.net/)。
本仓适配版本 **0.7.1**（上游 2008-09-26 发布，SVN r672）。

- 上游源码：`https://downloads.sourceforge.net/project/maq/maq/0.7.1/maq-0.7.1.tar.bz2`
- sha256：`e1671e0408b0895f5ab943839ee8f28747cf5f55dc64032c7469b133202b6de2`
- 许可证：GPL-3.0-or-later
- 包类型：`application`（CLI 工具，产物为 `bin/maq` + 4 个 perl 前端脚本）

## 构建

```bash
conan create archives/m/maq/0.7.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| `zlib/1.3.2` | 强制第三方 | `Makefile.am:8 maq_LDADD = -lm -lz`（链接 `-lz`，源码 21 处 `#include <zlib.h>`） |
| libm / libc / libc++ | 系统库 | 工具链 sysroot 自带 |
| perl | 运行期工具 | `bin/*.pl` 前端脚本需要（非 conan 包） |

## OHOS 适配要点

1. **config.guess / config.sub（2006 年版）**：不识别 HarmonyOS，`configure` 直接
   `cannot guess build type`。补丁 0001/0002 补 `aarch64-unknown-linux-ohos` 三元组
   （注意 `uname -v` 含冒号会使 `*:HarmonyOS:*:*` 模式失配）。
2. **HMDFS + `umask 077`**：`config.status` 临时目录不可写（E011）→ 补丁 0003 改 `umask 022`。
3. **clang 15 两阶段名字查找**：`stdhash.hh` 依赖基类成员 `direct_insert_aux` 需 `this->`
   限定 → 补丁 0013。
4. **perl shebang**：`#!/usr/bin/perl` 在 OHOS 不存在 → 补丁 0004-0012 改 `#!/usr/bin/env perl`。

## 使用示例（上游 maq.pod EXAMPLES）

```bash
maq fasta2bfa ref.fasta ref.bfa
maq fastq2bfq part1.fastq part1.bfq
maq fastq2bfq part2.fastq part2.bfq
maq map part1.map ref.bfa part1.bfq
maq map part2.map ref.bfa part2.bfq
maq mapmerge aln.map part1.map part2.map
maq assemble cns.cns ref.bfa aln.map
```

## 测试

- 上游 **无自动化测试套件**（无 `tests/`、无 `TESTS`/`check_PROGRAMS`）。
- 按 `maq.pod` 文档接口执行 45 项真实样例测试（45 PASS / 0 FAIL / 0 SKIP），
  含 5 项 OHOS 平台专项；详见 [0.7.1/reports/test-report.md](0.7.1/reports/test-report.md)。
- `test_package`：驱动安装后的 `maq` 跑通 fasta2bfa → fastq2bfq(PE) → map(PE) → assemble → mapstat。
