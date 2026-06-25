# lolcat

## 简介

lolcat 是一个用 Ruby 编写的终端彩虹色输出工具，可以将文本以彩虹渐变的形式显示在终端中，为终端输出增添趣味性。

## OHOS 适配

lolcat 是一个 Ruby gem，不是传统的 C/C++ 程序，因此：

- **构建方式**：使用 `gem build lolcat.gemspec` 构建 gem 包
- **运行环境**：需要 Ruby 环境（OHOS 系统已提供 Ruby 3.4.5）
- **依赖**：运行时需要以下 gem 包：
  - paint ~> 2.1
  - optimist ~> 3.0.0
  - manpages ~> 0.6.1
- **安装**：使用 `gem install lolcat-100.0.1.gem` 安装

### OHOS兼容性问题 ⚠️

**已知问题**：
- 直接读取文件时可能出现 `copy_file_range` 系统调用错误
- 错误信息：`Bad file descriptor - copy_file_range (Errno::EBADF)`
- 影响场景：`lolcat file.txt`（直接文件读取）

**解决方案**：

1. **使用管道输入（推荐）**
   ```bash
   echo "Hello OHOS" | lolcat
   cat file.txt | lolcat
   ls -la | lolcat
   ```

2. **使用 -f 参数强制彩色输出**
   ```bash
   lolcat -f file.txt
   lolcat -f file1.txt file2.txt
   ```

**功能状态**：
- ✅ 管道输入正常工作
- ✅ 所有参数功能正常（-F, -s, -S, -p, -t, -i等）
- ✅ 强制彩色模式正常
- ✅ Unicode、中文、Emoji支持
- ❌ 直接文件读取需要变通方案

**测试通过率**：96.00%（24/25测试通过）

## 功能验证

```bash
# 基础测试（推荐方式）
echo "Hello OHOS" | lolcat
lolcat --version

# 文件处理（使用管道）
cat README.md | lolcat
grep 'pattern' file.txt | lolcat

# 强制彩色模式
lolcat -f file.txt

# 参数测试
echo "Test" | lolcat -F 0.5 -s 10.0 -S 100
echo "Test" | lolcat -t  # 24位真彩色
```

## 依赖

### 编译依赖
- Ruby 3.4.5（OHOS 系统已提供）
- gem（Ruby 包管理器）

### 运行时依赖
- paint ~> 2.1（终端颜色渲染）
- optimist ~> 3.0.0（命令行参数解析）
- manpages ~> 0.6.1（man 手册页）

## 使用说明

```bash
# 方式一：使用管道（最佳兼容性）
cat file.txt | lolcat
echo "Hello World" | lolcat
ls -la | lolcat
fortune | lolcat

# 方式二：使用强制彩色模式
lolcat -f file.txt

# 常用参数
echo "Test" | lolcat -F 0.5    # 频率
echo "Test" | lolcat -s 10.0   # 速度
echo "Test" | lolcat -S 100    # 种子
echo "Test" | lolcat -p 5.0    # spread
echo "Test" | lolcat -t        # 真彩色
echo "Test" | lolcat -a        # 动画模式

# 组合使用
ls -la | lolcat -t -F 0.5
ps aux | lolcat -f
```

## 参考

- 项目主页：https://github.com/busyloop/lolcat
- RubyGems：https://rubygems.org/gems/lolcat
- OHOS测试报告：`archives/l/lolcat/100.0.1/reports/test-report-final.txt`