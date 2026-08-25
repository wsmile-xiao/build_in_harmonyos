# DRAFT-pico-sdk-cli-commands-json-r38：CLI 工具包需要软件级 commands.json

> Contributor: pico-sdk 2.2.0 适配 | Status: Draft | Updated: 2026-08-25
> Source: shadow CI r2 fail / r4 pass

## 现象

pico-sdk shadow CI r2 在 L0k 失败：

```text
L0k: CLI tool detected but commands.json missing (R38)
```

## 根因

pico-sdk recipe 声明 `package_type = "application"`，并打包 `bin/pioasm`。CI 会把它识别为 CLI 工具包，要求 `commands.json` 位于软件级目录：

```text
archives/p/pico-sdk/commands.json
```

不是：

```text
archives/p/pico-sdk/2.2.0/commands.json
```

## 推荐做法

新增软件级 `commands.json`：

```json
{
  "name": "pico-sdk",
  "type": "tool",
  "versions": {
    "2.2.0": {
      "ref": "pico-sdk/2.2.0",
      "binary": false
    }
  }
}
```

## 验证证据

pico-sdk 2.2.0 shadow CI r4 中 L0k 输出：`commands.json valid (type=tool)`。