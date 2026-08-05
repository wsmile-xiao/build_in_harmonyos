# accrete

太阳系行星形成物理模拟器（Physical simulation of solar system planet formation）。

accrete 由 Joe Nowakowski 于 1991 年发布到 Usenet (comp.sources.unix)，属于公有领域软件
（FreeBSD ports 声明为 BSD-3-Clause；内嵌 Mersenne Twister RNG 为 BSD 风格许可）。
2003 年由 Charles Swiger 维护，改用 Mersenne Twister 随机数并清理了 Makefile。

运行 accrete 会模拟围绕类太阳恒星的尘埃盘吸积过程，生成行星系统，并将结果写入
`New.System` 文件（含恒星特征与每颗行星的轨道、质量、半径、大气、温度等参数）。

- 上游: https://sourceforge.net/projects/accrete/
- 版本: 1.0
- 构建: 纯 C + 单 Makefile，无外部依赖
- 产物: bin/accrete（命令行工具）

## 版本索引

| 版本 | 状态 | 适配日期 |
|------|------|----------|
| 1.0  | published | 2026-08-05 |
