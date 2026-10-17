# pd-mjlib — Pure Data 外部对象集合（mjlib）

`mjlib` 是 Pure Data（Pd）的一组外部对象，共 8 个类：

- **`about`**：基于锚点值与百分比偏差的随机发生器。
- **`metroplus`**：多区间 metro。
- **`monorhythm`**：多区间多输出节奏发生器。
- **`morse`**：文本转摩尔斯电码。
- **`n2m`**：音名（如 `C5`）转 MIDI 音编号。
- **`pin~`**：基于随机的信号路由。
- **`prob`**：随机事件发生器。
- **`synapseA~`**：块平均/比较器。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中直接使用 [n2m]、[morse]、[prob] 等
```

## OHOS 适配要点

- 上游用自带 `pd-lib-builder` 构建，每个类产出一个 `<class>.pd_linux`。
- `puredata/0.54.1`（application）**不装** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树取得 Pd API 头，并用 `PDINCLUDEDIR` 指向它。
- `pd-lib-builder` 依据 `$(CC) -dumpmachine` 选中 Linux 分支与 `pd_linux` 扩展名。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 8 个外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：GPL-2.0-or-later
