# MyThes 1.2.6 — HarmonyOS PC

官方 LibreOffice 源码归档 SHA-256 为 `97bd2ba5738aebdba1bc31f30f1be42f1404386c94105ad5990d839a1311c8a5`。上游 `Makefile.am` 声明 `check_PROGRAMS = example` 而没有 `TESTS`；`make check` 仅构建示例。配方保持上游测试源码不变，执行 README 列出的两组示例输入，并在安装后用 Conan 消费者测试查询 UTF-8 同义词。

目标机首次验证在编译示例时找不到 `hunspell.hxx`：已发布 Hunspell 包把头放在 `include/hunspell/`，生成元数据只给 `include/`。修复限定为上游构建变量 `HUNSPELL_CFLAGS`，不改全局 Conan 依赖元数据。第二次 `conan create` 实际成功，但冻结验证器未接受 Conan 日志前缀，事务仍记 FAIL；第三次使用明确的示例标记和前缀解析，完整 W3 12/12 PASS。失败事务均未重启或合并证据。

上游公共头使用 `FILE` 而未引入 `<stdio.h>`，仅在 Conan 构建源码副本中补入标准头以使安装后消费者可独立包含。上游安装的 Perl 索引脚本改为可移植的 `/usr/bin/env perl` shebang；软件级 `commands.json` 记录该工具。可选能力与测试范围记录在 PR 正文中。
