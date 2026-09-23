# libsmf

> BSD 许可的 Standard MIDI File (`.mid`) 编解码 C 库。

## 简介

libsmf 用于读写 Standard MIDI File 文件, 透明处理脉冲与时间换算、
tempo map 管理, 不关心具体 MIDI 负载语义 (实时消息、SysEx 均可)。
典型用法: `smf_load()` 载入歌曲 → `smf_get_next_event()` 顺序取事件 →
按 `event->time_seconds` 回放; 写文件则 `smf_new()` → 建 track →
`smf_track_add_event_seconds()` 加事件 → `smf_save()` 落盘。
库本身无全局变量, 同一 `smf_t` 加锁即线程安全。

## OHOS 适配要点

- 构建为 Autotools (2010 年版脚本): 必须显式
  `--build/--host=aarch64-unknown-linux-gnu`, 否则旧 `config.sub`
  拒识 ohos/musl 三元组, `config.guess` 在 HMDFS 上亦无法探测。
- `smfsh` 的 readline 行编辑支持已用 `--with-readline=no` 关闭,
  运行时依赖只有 glib。
- 上游无测试套件, `make check` 为空目标; 适配验证走
  `test_package/test_smf.c` 的 SMF 落盘/回读往返。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.0.1 | 唯一上游依赖 (`smf.h` 含 `<glib.h>`, GPtrArray 等; 用已发布版本, 内建 libffi 子项目, 免外部 libffi 构建) |
| libm | 系统库 | `pow` 等数学函数 |

## 功能验证

```bash
smfsh -V            # 期望输出 libsmf 版本信息
pkg-config --modversion smf   # 期望输出: 1.3
```

## 参考

- [SourceForge 项目页](https://sourceforge.net/projects/libsmf/)
- [API 文档](https://libsmf.sourceforge.net/api/)
- [GitHub 开发镜像](https://github.com/nilsgey/libsmf)
