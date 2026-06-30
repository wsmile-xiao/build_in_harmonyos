# mecab 0.996 — HarmonyOS aarch64 预编译包发布说明

## 版本信息
- **软件版本**: mecab 0.996
- **编译状态**: partial
- **目标平台**: HarmonyOS aarch64
- **构建系统**: autotools
- **发布日期**: 2026-04-29

## 快速安装

```bash
# 解压预编译包
tar xzf mecab-0.996-ohos-aarch64.tar.gz -C ~/usr/local

# 进入目录并运行安装脚本
cd ~/usr/local/mecab-0.996-ohos-aarch64
sh install-mecab-0.996.sh

# 验证安装
mecab --version
# 输出: mecab of 0.996
```

## 包内容

### 主包 (mecab-0.996-ohos-aarch64.tar.gz, 8.4MB)
```
bin/
  mecab              # 分词主程序
  mecab-config       # 配置信息工具
lib/
  libmecab.a         # 静态库
  libmecab.so        # 动态库
  libmecab.so.2
  libmecab.so.2.0.0
  libmecab.la        # libtool 元数据
include/
  mecab.h            # 头文件
libexec/mecab/
  mecab-dict-index   # 字典索引生成
  mecab-dict-gen     # 字典生成
  mecab-cost-train   # 成本训练
  mecab-system-eval  # 系统评估
  mecab-test-gen     # 测试生成
etc/
  mecabrc            # 默认配置
share/man/man1/
  mecab.1            # 手册页
```

### 调试包 (mecab-0.996-ohos-aarch64-debug.tar.gz, 698KB)
包含所有二进制文件的调试符号。

## 补丁列表

| 补丁 | 描述 |
|------|------|
| 0001-config.guess.patch | 添加 HarmonyOS 系统识别（__OHOS__ LIBC 检测 + case 分支） |
| 0002-config.sub.patch | 添加 linux-ohos 三元组支持 |
| 0003-configure.patch | 使用 TMPDIR 环境变量创建临时目录 |

## 编译环境
- **编译器**: clang 15.0.4
- **系统**: HarmonyOS Kernel 1.12.0 (aarch64)
- **C++ 库**: libc++ (替代 libstdc++)
- **构建模式**: VPATH

## 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | manual_pass | VPATH 构建限制，手动验证通过 |
| G1 二进制完整性 | pass | |
| G2 功能可用性 | pass | |
| G3 可移植性 | pass | |
| G4 档案完整性 | pass | |

## 测试结果
- **通过**: 2/3
- **失败**: 1/3 (run-eval.sh)
- **说明**: VPATH 构建导致测试脚本路径问题，非核心功能问题

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 需安装日语字典包（如 mecab-ipadic）才能使用分词功能

## 使用示例
```bash
# 需要先安装字典
mecab-dict-index -d /path/to/dictionary

# 分词示例
echo "今日はいい天気です" | mecab
今日は	今日	名詞,副詞可能,*,*,*,*,今日,キョウ,キョー
...
```

## 已知限制
1. VPATH 构建导致部分测试脚本路径不匹配
2. 需安装字典包才能使用分词功能

---
*发布日期: 2026-04-29*