# debian-ports-archive 2026.02.04 适配笔记

## 编译环境
- 构建系统: custom（纯数据，无编译）
- 编译日期: 2026-09-10
- 编译器: 无
- 状态: built

## 编译步骤

纯数据包（上游源码包名 debian-ports-archive-keyring），无编译。打包时复制：

1. `active-keys/*.key` → `share/keyrings/debian-ports-archive/active-keys/`
2. `removed-keys/*.key` → `share/keyrings/debian-ports-archive/removed-keys/`
3. `README` → `share/doc/debian-ports-archive/`
4. `debian/copyright` → `licenses/`（GPL-2.0-or-later）

## 遇到的问题与解决方案

| # | 问题 | 根源 | 解决方案 |
|---|------|------|----------|
| 1 | 上游构建期用 gnupg 组装 keyring 并安装为 conffile | OHOS 不提供 apt/gnupg 装配流程 | 直接分发 ASCII-armored 密钥文件，消费侧自行导入 |
| 2 | 任务软件名与上游源码包名不一致 | 任务名 debian-ports-archive | conan 包名=debian-ports-archive，conandata 指向上游源码包 |

## 源码修改

无（纯数据打包）。

## 依赖版本

无编译依赖。

## 验证结果

```bash
$ python3 test_verify.py <prefix>
DEBIAN_PORTS_ARCHIVE_VALIDATION_PASS active=2 removed=19 assertions=...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| share/keyrings/debian-ports-archive/active-keys/*.key | 4.4KB 各 | debian-ports 有效归档签名密钥（2026/2027） |
| share/keyrings/debian-ports-archive/removed-keys/*.key | 多个 | 2007–2025 历史归档密钥 |

## 注意事项

- 有效密钥为 ASCII-armored 公钥块，但按键命名无固定前缀；消费侧可通过
  `DEBIAN_PORTS_ARCHIVE_KEYS`（runenv 注入）定位目录后导入。