# PocketSphinx

## 简介

PocketSphinx 是一个轻量级语音识别引擎，适用于嵌入式设备和移动平台的语音识别应用。

## OHOS 适配

### 适配要点
- 构建系统为 CMake，无 autotools configure 脚本
- 使用标准 CMake 命令：`cmake -B build`、`cmake --build build`、`cmake --install build`
- 测试套件需要 sox 工具处理音频输入（可选，不影响核心功能）

### 已知问题
- 测试套件部分失败（3/105），原因是缺少 sox 工具
- 不影响核心语音识别功能
- CMake 检测到 "System unknown" 警告，但不阻塞编译

### 与 Linux 的差异
- Linux 上可运行完整测试套件
- OHOS 上需手动验证语音识别功能

## 排除与替代

无特殊排除项。

## 依赖

### 编译依赖
- CMake >= 3.25
- Clang 编译器
- Bison、Flex（用于 JSGF 解析器生成，源码已预生成）

### 运行依赖
- 无外部库依赖（纯 C 项目，静态库自包含）
- 可选：sox（用于音频输入处理）

## 功能验证

```bash
# 验证安装
pocketsphinx --help

# 主程序
pocketsphinx single input.wav

# 批处理模式
pocketsphinx_batch -hmm model -lm language_model -dict dictionary
```

### 可执行文件列表
| 文件 | 功能 |
|------|------|
| pocketsphinx | 主语音识别程序 |
| pocketsphinx_batch | 批处理模式 |
| pocketsphinx_jsgf2fsg | JSGF 到 FSG 转换 |
| pocketsphinx_lm_convert | 语言模型转换 |
| pocketsphinx_lm_eval | 语言模型评估 |
| pocketsphinx_mdef_convert | 模型定义转换 |
| pocketsphinx_pitch | 音调检测 |

### 库文件
- `libpocketsphinx.a` - 静态库，可用于其他项目链接

## 参考

- 官方仓库: https://github.com/cmusphinx/pocketsphinx
- 文档: https://cmusphinx.github.io/doc/pocketsphinx/
- API 文档: https://pocketsphinx.readthedocs.io/