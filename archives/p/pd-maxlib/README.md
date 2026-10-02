# pd-maxlib — Pure Data 外部对象集合（maxlib）

`maxlib` 是 Pure Data（Pd）的一组经典外部对象，包含 58 个类：数学运算
（`plus`/`minus`/`divide`/`multi`/`divmod`）、随机分布（`gauss`/`beta`/`cauchy`/
`poisson`/`weibull`/`triang`/`linear`/`expo`/`arbran`/`bilex`/`urn`）、序列与节拍
（`step`/`fifo`/`lifo`/`listfifo`/`pulse`/`beat`/`rhythm`/`pitch`/`score`）、
列表与路由（`split`/`subst`/`nroute`/`unroute`/`listfunnel`/`match`）、自动机
（`mlife`）等。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 在补丁中直接使用 [divide]、[plus]、[mlife] 等
```

## OHOS 适配要点

- 上游用自带 `pd-lib-builder` 构建，每个类产出一个 `<class>.pd_linux`。
- `puredata/0.54.1`（application）**不装** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树取得 Pd API 头，并用 `PDINCLUDEDIR` 指向它。
- `pd-lib-builder` 依据 `$(CC) -dumpmachine` 选中 Linux 分支与 `pd_linux` 扩展名。
- 上游 Makefile 已排除依赖 Pd 内部头的 `net*` 类。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 58 个外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：GPL-2.0-or-later
