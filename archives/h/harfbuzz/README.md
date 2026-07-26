# harfbuzz

## 简介
HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。

## OHOS 适配
- 使用 Meson 和 Conan `shared=True/False` 构建
- 依赖 `freetype/2.14.3`；该 FreeType 配方禁用 HarfBuzz，因此依赖图无环
- 启用 core、subset、vector 和完整上游测试
- 禁用未纳入本配方的 glib、cairo、icu、graphite、gpu、文档和命令行工具
- 在 Linux/OHOS 上通过统一解析器从 Conan 配置的 clang 路径解析绝对 `llvm-ar`、`llvm-ranlib`、`llvm-nm` 和 `llvm-objdump`，并一致保留 `clang-15` 等版本后缀；Windows/MSVC 保持 Meson 原生工具处理
- `llvm-objcopy` 与 `binary-sign-tool` 同样解析为绝对路径，并以 POSIX shell quoting 保护工具和库路径；工具缺失时明确失败，不依赖固定 Worker 目录
- 不需要源码补丁或手工生成 `hb-features.h`

## 依赖
- Conan 依赖：`freetype/2.14.3`

## 功能验证
```bash
conan create archives/h/harfbuzz/14.2.0 -o 'harfbuzz/*:shared=True'
```

WSL Clang 15 近似验证中，上游 59/59 组测试与消费者 shaping 流程均通过；真实 HarmonyOS 结果以 CI 为准。

PR #2906 的首轮 Build #7523 已完成编译并执行上游套件，结果为 56 通过、2 个 LLVM 工具启动失败、1 跳过。配方改为向原测试注入工具绝对路径后，Build #7546 在对应 HEAD 上通过全部 CI 步骤；归档工具版本后缀统一后的 HEAD `6de3ea24626b8b0b00feebd494289aa8e039fa23` 又由 Build #7584 验证通过。第三轮 Review 要求的签名命令路径 quoting 已在本地落实，推送后仍须以新 HEAD 的正式 CI 为最终证据。

## 参考
- 官网：https://harfbuzz.github.io/
- 源码：https://github.com/harfbuzz/harfbuzz
