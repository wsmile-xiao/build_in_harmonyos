# dejagnu

## 简介
GNU DejaGnu 是一个测试框架，用于运行其他软件工具的测试套件。它是许多 GNU 项目（如 GCC、GDB）的标准测试工具。

## OHOS 适配
- 主要产物是 Tcl 脚本（runtest、dejagnu），不是 ELF 二进制文件
- 依赖 expect，需要正确配置 Tcl 环境
- configure 需要应用 E011 umask 022 方案解决 HMDFS 临时文件限制
- G4 档案完整性检查需要特殊处理（非 ELF 文件）

## 依赖
- expect（预编译包可用）
- Tcl 8.6+

## 功能验证
```bash
runtest --version
```

## 参考
- 官网: https://www.gnu.org/software/dejagnu/
- 源码: https://ftp.gnu.org/gnu/dejagnu/