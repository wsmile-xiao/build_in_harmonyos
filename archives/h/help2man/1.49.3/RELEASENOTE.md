# help2man 1.49.3 发布说明

## 版本信息
- 软件名称: GNU help2man
- 版本: 1.49.3
- 发布日期: 2026-04-30
- 预编译包状态: ready

## 主要特性
- 从 `--help` 和 `--version` 输出生成 man 页面
- 纯 Perl 实现，无需编译
- 自动检测并嵌入正确的 perl 路径
- 支持多语言 man 页面生成

## 鸿蒙适配说明
- 已验证 perl 5.42.0 兼容性
- shebang 自动使用鸿蒙 perl 路径
- 首次执行需要用户确认（安全机制）
- 无 ELF 签名要求（纯脚本文件）

## 安装要求
- Perl 5.8+
- GNU sed（推荐使用预编译包）

## 文件列表
```
help2man-1.49.3-ohos-aarch64.tar.gz
├── bin/help2man
├── share/man/man1/help2man.1
└── share/info/help2man.info
```

## 使用方法
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- help2man 1.49.3

# 验证安装
help2man --version

# 为程序生成 man 页面
help2man --name="program description" /path/to/program > program.1
```

## 依赖关系
- 运行依赖: perl (系统预装)
- 推荐依赖: GNU sed (预编译包)

## 更新历史
| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-04-30 | 1.49.3 | 首次预编译包发布 |