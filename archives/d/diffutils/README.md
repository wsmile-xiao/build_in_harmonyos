# diffutils

GNU diffutils - 文件比较工具集

## 软件描述

diffutils 包含以下工具：
- **diff**: 比较两个文件，输出差异
- **diff3**: 比较三个文件
- **sdiff**: 并排显示两个文件的差异
- **cmp**: 逐字节比较两个文件

## 编译状态

**已编译版本**: 3.10
**状态**: built（预编译包已生成）
**平台**: OpenHarmony aarch64

## 关键修复

- **E011**: HMDFS umask 077 权限问题（修改 configure umask）
- **E007**: config.guess HarmonyOS 识别
- **E072**: config.sub 三元组验证

## 使用方式

预编译包可通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- diffutils 3.10
```