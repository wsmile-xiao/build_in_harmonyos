# intltool

## 简介
intltool 是一组用于国际化的工具，可以从多种文件格式（如 .desktop、XML、PO 文件）中提取和合并可翻译字符串。由纯 Perl 脚本组成，无需原生编译。

## OHOS 适配
- 纯 Perl 脚本集合，无需原生编译
- XML::Parser Perl XS 模块因 HMDFS dlopen 限制无法加载，需 configure 补丁跳过检查
- 并行构建可能因 HMDFS mkfifo 问题失败，建议使用 -j1
- Perl regex 警告（未转义花括号）为非致命，仅影响外观
- 测试套件 selftest 因 HMDFS 执行限制失败（非阻塞）

## 排除与替代
无

## 依赖
- 编译依赖：perl, autotools
- 运行依赖：perl 5.8+

## 功能验证
```bash
intltool-update --version  # → intltool-update (intltool) 0.51.0
intltoolize --version      # → intltoolize (GNU intltool) 0.51.0
```

## 参考
- 官网：https://launchpad.net/intltool
