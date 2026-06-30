# mecab-ko - 韩语形态分析器

## 软件简介
mecab-ko 是 MeCab（Yet Another Part-of-Speech and Morphological Analyzer）的韩语版本，用于韩语文本的形态分析和词性标注。

- **官方网站**: https://bitbucket.org/eunjeon/mecab-ko
- **构建系统**: autotools
- **编程语言**: C++
- **许可证**: GPL/LGPL/BSD

## 功能特性
- 韩语文本分词
- 词性标注
- 形态分析
- 支持自定义词典
- 高性能处理引擎

## 版本历史

### 0.996-ko-0.9.2 (2026-06-05)
- **状态**: built
- **编译平台**: HarmonyOS (aarch64-unknown-linux-ohos)
- **编译方式**: 静态链接
- **预编译包**: mecab-ko-0.996-ko-0.9.2-ohos-aarch64.tar.gz (9.1M)
- **注意事项**:
  - mecab 采用静态链接 libmecab.a，解决动态链接问题
  - 预编译包包含静态库和动态库，满足不同使用场景
  - ELF 未签名，需用户首次执行时确认安全弹窗

## 使用方法

### 安装预编译包
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- mecab-ko 0.996-ko-0.9.2
```

### 基本使用
```bash
# 查看版本
mecab --version

# 查看帮助
mecab --help

# 韩语文本分词（需要词典）
mecab -d /path/to/dictionary
```

### 安装词典
mecab-ko 需要韩语词典才能正常工作：
- mecab-ko-dic: 韩语词典（需单独编译安装）

## 技术说明

### 静态链接方案
由于鸿蒙动态链接器限制，mecab 采用静态链接：
- **编译命令**: `clang++ -o mecab mecab.cpp libmecab.a -lpthread -lc++`
- **优势**: 独立可执行，无动态链接依赖问题
- **劣势**: 文件较大（1.0M vs 动态版本 4.7K）

### 平台适配
- config.guess/config.sub 补丁识别 HarmonyOS
- configure.in 移除 -lstdc++ 检测（鸿蒙使用 libc++）
- 8个补丁文件固化平台适配修改

## 相关软件
- **mecab**: 日语形态分析器（原始版本）
- **mecab-ko-dic**: 韩语词典
- **mecab-ipadic**: 日语词典

## 参考资料
- MeCab 官方网站: https://taku910.github.io/mecab/
- mecab-ko 项目: https://bitbucket.org/eunjeon/mecab-ko
- 归档位置: archives/m/mecab-ko/0.996-ko-0.9.2/