# pd-osc — Pure Data 的 OpenSoundControl 外部对象集合

`osc`（Pure Data 发行版里的 `pd-osc`）是在 Pd 内构造与解析 OSC 消息的外部对象
集合，从老的 `pd-mrpeach` 项目独立而来。它只负责 OSC 消息的打包/解包，
传输层（UDP/TCP/串口）需要另配 `pd-net`、`pd-comport`、`pd-slip` 等。

包含的类：

| 类 | 产物 | 作用 |
|----|------|------|
| `[packOSC]` | `packOSC.pd_linux` | Pd 消息 → OSC 字节列表 |
| `[unpackOSC]` | `unpackOSC.pd_linux` | OSC 字节列表 → Pd 消息 |
| `[routeOSC]` | `routeOSC.pd_linux` | 按路径首个元素路由 OSC 消息 |
| `[pipelist]` | `pipelist.pd_linux` | 按时间戳顺序投递列表 |
| `[packOSCstream]` / `[unpackOSCstream]` | 抽象补丁（`.pd`） | 面向流式传输的变体 |

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象目录加入搜索路径
# 四个类都按类名自动加载：[packOSC]、[unpackOSC]、[routeOSC]、[pipelist]
```

## OHOS 适配要点

- 上游用自带 `pd-lib-builder`（`Makefile` + `pd-lib-builder/Makefile.pdlibbuilder`）
  构建，共 4 个 `.pd_linux`。注意 `lib.name = osc` 并不产生合并的 `osc.pd_linux`
  库 blob：裸 `class.sources` 会被 pd-lib-builder 拆成每个源文件一个
  `<basename>.class.sources`，所以 [routeOSC] / [pipelist] 各自独立成对象。
- `puredata/0.54.1`（application）**不装** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树取得 Pd API 头，并用 `PDINCLUDEDIR` 指向它。
- `pd-lib-builder` 依据 `$(CC) -dumpmachine` 选中 Linux 分支与 `pd_linux` 扩展名。
- 源码只用公开的 `m_pd.h`，不碰 Pd 内部头（`m_imp.h`/`s_stuff.h`），无需打补丁。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 4 个外部对象 |
| `lib/pd-externals/*.pd` | `osc-meta.pd`、6 个帮助补丁、2 个 stream 抽象补丁 |
| `licenses/LICENSE.txt` | 许可证 |
| `share/doc/osc/README.md` | 上游 README |

## 参考资料

- 上游：<https://github.com/pd-externals/osc>
- 许可证：GPL-2.0-or-later