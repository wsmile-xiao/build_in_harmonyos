# salesforce-mcp

Salesforce MCP Server for interacting with Salesforce instances.

## 描述

Salesforce DX MCP Server 是一个 Model Context Protocol (MCP) 实现，
用于促进大语言模型 与 Salesforce 组织之间的无缝交互。

## 依赖

- Node.js >= 20.0.0

## 安装

```bash
tar -xzf salesforce-mcp-0.30.13-ohos-aarch64.tar.gz -C $HOME/usr/local --strip-components=2
$HOME/usr/local/bin/sf-mcp-server --version
```

## 使用

配置 MCP 客户端（如 VS Code Copilot）：
```json
{
  "servers": {
    "Salesforce DX": {
      "command": "$HOME/usr/local/bin/sf-mcp-server",
      "args": ["--orgs", "DEFAULT_TARGET_ORG"]
    }
  }
}
```

## 来源

- GitHub: https://github.com/salesforcecli/mcp
- npm: https://www.npmjs.com/package/@salesforce/mcp
- License: Apache-2.0
