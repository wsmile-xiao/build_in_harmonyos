# ispell

经典 Unix 交互式拼写检查程序，支持自定义词典和多语言。

## 工具列表

| 工具 | 功能 |
|------|------|
| `ispell` | 主程序：交互式拼写检查文件，或通过 `-a` 管道模式集成到其他程序（如 Emacs） |
| `buildhash` | 从词表构建 ispell 哈希字典文件（`.hash`） |
| `munchlist` | 最小化词表（减少存储，提高查找速度） |
| `findaffix` | 分析词表中的词缀模式 |
| `tryaffix` | 测试词缀规则 |
| `unsq` / `sq` | 词表压缩/解压工具 |

## 上游仓库

https://www.cs.hmc.edu/~geoff/ispell.html

## 许可证

BSD-4-Clause

## 状态

| 版本 | 状态 | 平台 | 备注 |
|------|------|------|------|
| 3.4.06 | adapting | OHOS aarch64 | 依赖 ncurses/6.5 |
