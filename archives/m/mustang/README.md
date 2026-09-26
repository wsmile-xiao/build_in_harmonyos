# mustang 3.2.4 for HarmonyOS

## 概述

MUSTANG（MUltiple STuructural AligNment alGorithm）是蛋白质多重结构比对命令行工具，基于结构保守性对多个 PDB 蛋白质结构做逐步叠加比对，输出 MSF/FASTA/PIR/Clustal 等多重比对格式与叠合结构。

- 上游源码: https://deb.debian.org/debian/pool/main/m/mustang/mustang_3.2.4.orig.tar.gz（sha256 c05e91c955f491a1fddc404a36ef963b057fd725bcc6d22ef6df1c23b26ce237）
- 主页: http://lcb.infotech.monash.edu.au/mustang
- 许可证: BSD-3-Clause
- 适配路径: 裸 Makefile（无 configure），make 变量覆盖 `CPP=<clang++>`、`CPPFLAGS="-Wall -O3"` 适配 OHOS clang；零外部依赖；无补丁
- 产物: `bin/mustang`（命令行工具，详见软件级 commands.json）

## 构建（Conan）

```bash
python3 scripts/ohc-run.py build mustang 3.2.4
# 或分步: conan-init → conan-verify（8 闸）→ finish mustang 3.2.4 built
```

## 使用

```bash
mustang -i struct1.pdb struct2.pdb ... -F fasta -o out   # 多重结构比对
mustang -f description_file                              # 用描述文件批量输入
mustang --help                                           # 横幅与用法提示
```

## 测试

上游无自动化测试套件（Makefile 无 check 目标）；上游 README 手工冒烟
`-f data/test/test_zf-CCHH` 已在本平台复现通过。test_package 内置消费者冒烟：
两个合成聚丙氨酸螺旋真实比对，断言 FASTA 输出。详见 3.2.4/reports/test-report.md。
