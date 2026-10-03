# lexd 1.3.5 — HarmonyOS PC 适配说明（软件级）

`lexd` 是 Apertium 平台的词典编译器：把 `.lexd` 规则文件编译为 ATT 有限状态
转换器（替代 `hfst-twolc` 步骤），支持前缀、可选成分、sieve、filter、tag 等
非后缀化形态学机制。

- 上游：https://github.com/apertium/lexd
- 形态：autotools（发布包无生成的 `configure`）
- 许可证：GPL-3.0-or-later
- 产物：`bin/lexd`、`share/man/man1/lexd.1`、`lib/pkgconfig/lexd.pc`

## 版本

| 版本 | 状态 | 依赖 | 说明 |
|------|------|------|------|
| 1.3.5 | built | lttoolbox/3.7.6、icu4c/77、utf8cpp/4.1.1 | 上游负例 12/12 + 消费者 12/12 + 上游 gold 798 断言（216 组合） |

详细适配记录见 `1.3.5/notes.md`。
