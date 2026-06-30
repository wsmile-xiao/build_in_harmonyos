# bombardier

## 软件描述
bombardier 是一个高性能 HTTP 负载测试工具，用 Go 语言编写。它可以快速生成大量 HTTP 请求，用于测试 Web 服务器的性能和稳定性。

## 主要功能
- 高并发 HTTP 请求生成
- 支持 HTTP/1.1 和 HTTP/2
- 实时统计和报告
- 多种请求模式和配置选项

## 安装方式
通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- bombardier 2.0.2
```

## 使用示例
```bash
# 基本使用
bombardier -c 100 -n 1000 http://localhost:8080/

# 显示帮助
bombardier --help
```

## 版本信息
- 最新版本: 2.0.2
- 官方源码: https://github.com/codesenberg/bombardier

## 平台适配说明
- 已在 HarmonyOS (OpenHarmony) aarch64 平台编译验证
- 使用 CGO_ENABLED=1 和外部链接器绕过 HMDFS mmap 权限限制
- 版本号显示为 "unspecified"（链接器权限限制，无法注入版本信息）

## 依赖
- 无额外依赖（标准 C 库）

---
*OpenDesk Compile Agent*