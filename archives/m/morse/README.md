# morse (Morse Classic)

Eric S. Raymond 的 Unix 莫尔斯电码训练工具。

- 官方主页： http://www.catb.org/~esr/morse-classic
- 官方仓库： https://gitlab.com/esr/morse-classic
- License： BSD-2-Clause

## 版本

| 版本 | 说明 |
|---|---|
| [2.7](./2.7/) | 2026-03-17 release "Raise the system quality bar"，零 patch，OHOS AArch64 |

## 工具

- **morse**：文本→莫尔斯电码（蜂鸣+屏幕点划）、随机练习、字母滚动
- **QSO**：模拟业余无线电 QSO 报文生成器（随机呼号/RST/交换）

上游自带 `make check` 自测（testmorse + testqso），适配中在
配方 build() 真实执行（详见 [2.7/notes.md](./2.7/notes.md)）。
