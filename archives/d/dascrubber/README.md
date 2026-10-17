# dascrubber

> Dazzler 比对校正管线工具集：基于比对堆叠（alignment pile）对 PacBio 长读长做 scrubbing，产出连续、高质量的校正读长。

## 简介

dascrubber 由 Gene Myers 开发（Dazzler 套件 scrubbing 阶段），管线为
`DAScover → DASqv → DAStrim → DASpatch → DASedit`，另附 `DASmap`/`DASrealign`
与 `REPcover`/`REPqv`/`REPtrim` 三个报告工具。输入为 DAZZ_DB 数据库与
DALIGNER 产出的 `.las` 比对块，输出为去嵌合、去低质量片段的 scrubbed 数据库。

## OHOS 适配要点

- 纯 Makefile 构建的命令行工具包，仅发布 10 个二进制（application 包，R38）。
- 上游 Makefile 硬编码 `gcc`，portability 补丁改为 `$(CC)`，配方从 Conan
  `tools.build:compiler_executables:c` 注入 clang 绝对路径（R33）。
- 纯 C99 + `-lm`，无第三方依赖，无 configure 步骤，原生兼容 HarmonyOS aarch64。
- 上游无正式测试套件（无 check/ctest 入口），`test_package` 用二进制在位检查 +
  10 个工具逐一 `Usage:` 契约负向对照（共 11 项）做消费者功能验证兼上游等效验证（R34，精确匹配防 loader 误报）。

## 依赖

无外部依赖（仅系统数学库 `-lm`）。

## 功能验证

```bash
DAScover   # 空参数打印 Usage: DAScover [-v] ...（退出码非零）
DASqv      # 空参数打印 Usage 契约
DAStrim    # 空参数打印 Usage 契约
DASedit    # 空参数打印 Usage 契约
```

## 参考

- [源码仓库](https://github.com/thegenemyers/DASCRUBBER)
- [Debian 源码](https://sources.debian.org/src/dascrubber/1.1-4/)
- [Dazzler 博客 scrubbing 介绍](https://dazzlerblog.wordpress.com/2017/04/22/1344/)
