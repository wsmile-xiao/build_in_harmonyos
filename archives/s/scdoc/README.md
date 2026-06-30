# scdoc

## 软件简介
scdoc 是一个简单的 man page 生成工具，使用自定义的标记语言编写，可以生成标准的 roff 格式 man pages。

## 主要功能
- 简洁的标记语法：比 roff 更易读易写
- 自动生成标准 man page 格式
- 支持表格、列表、代码块等格式
- 静态编译，无外部依赖

## OHOS 适配
- 构建系统：Makefile（无 configure）
- 编译器：Clang 15.0.4
- 适配补丁：
  - 修复 install 命令参数格式（toybox 兼容）
  - 修复函数原型警告（strict-prototypes）

## 依赖关系
- 无外部依赖（静态编译）

## 安装方法
```bash
# 通过预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- scdoc 1.11.0
```

## 使用示例
```bash
# 生成 man page
scdoc < myprogram.scd > myprogram.1

# 或直接处理文件
scdoc myprogram.scd.1.in > myprogram.1
```

## 版本历史
| 版本 | 状态 | 备注 |
|------|------|------|
| 1.11.0 | built | 首次适配 |

## 许可证
MIT License
