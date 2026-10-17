# E6403（草稿）：无 TESTS 的 check-only 示例依赖作用域与执行证据

## 现象与根因

某些 Autotools 库在 `Makefile.am` 声明 `check_PROGRAMS = example`，却没有 `TESTS`。`make check` 因而只保证示例被编译，不保证它曾运行。如果该示例独自使用一项外部依赖，而依赖包的头位于 `include/<component>/`、生成的 pkg-config Cflags 只有 `include/`，编译会报找不到头。把生成的依赖 `.pc` 或所有目标的 CFLAGS 一并改掉，作用域过大，且完全不能解决示例未执行的问题。

MyThes 1.2.6 提供实证：上游 `example` 需要 Hunspell，`mythes.cxx` 库本体不需要；已发布 Hunspell 包的 `hunspell.hxx` 位于 `include/hunspell/`，首次目标机 W3 在 `make check` 编译示例时失败。上游 `AM_CXXFLAGS` 已有 `$(HUNSPELL_CFLAGS)`，可只把该变量设置到已验证的包内目录。README 规定两组输入，而 `TESTS` 为空，必须分别运行才有 2/2 的测试证据。

## 可复用决策

1. 对照 `check_PROGRAMS`、`TESTS` 和上游文档，分清“构建了程序”与“实际派发用例”。逐条确定需要的输入与成功语义。
2. 检查真实依赖包中头文件和库文件的位置，不能仅凭 `pkg-config --exists` 判断编译契约完整。
3. 若缺失头只被 check-only 示例使用，并且上游提供该示例专用的依赖 CFLAGS 变量，使用该变量传入精确 `-I`，保留其余编译元数据。若公共库本体或多个消费者也使用它，则应修复 provider 组件的生成 `.pc`，不能套用本条狭义方案。
4. 完整执行 `make check` 后逐一运行文档示例，分别核对退出码与非空语义输出；另以安装后消费者检验公开库 API。测试数量按实际执行场景申报，不把 `make check` 成功冒充例子通过。

## 验证与边界

本例第三次全新 W3 为 12/12 阶段 PASS，`conan create` 返回 0，两个 README 场景 2/2 PASS，安装后公开 API 消费者 1/1 PASS；原始日志 SHA-256 为 `984b5ad2fd393977b0e0f2044e91955333d3f4eb01238c29b3fa522548b8663f`。第二次虽有测试成功，但冻结验证器未接受带 Conan 前缀的计数标记，按真实失败处理，未跨事务拼接。

与既有 `E589` 的区别：E589 解决“已注册数与 shell runner 实际派发数不一致”；本条针对 `TESTS` 完全为空、依赖仅供示例使用时的**头目录修复作用域**，并把文档场景执行作为必要证据。与通用 provider `.pc` 嵌套头修复不同，本条不改变公共 provider 元数据；若依赖为库本体所需，本条不适用。
