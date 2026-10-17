# tanidvr

TaniDVR —— 访问采用达智（Dahua）DVR-IP 协议（TCP 37777）的 DVR / 网络摄像机的
命令行工具集，上游主页 <https://tanidvr.sourceforge.net/>。

包内交付两个可执行文件：

| 命令 | 说明 |
|------|------|
| `tanidvr` | DVR / IP 摄像机客户端：实时监控、录像检索与下载 |
| `dhav2mkv` | 把 DVR 导出的 `.dhav` / `.dav` 录像转换为 Matroska（`.mkv`） |

许可证：GPL-3.0-or-later（上游 COPYING）。

## 用法速查

```bash
tanidvr -h          # 帮助（会打印版本与 GPL 声明）
dhav2mkv -h         # 帮助
dhav2mkv -i rec.dhav -o rec.mkv     # 文件转换
cat rec.dhav | dhav2mkv > rec.mkv   # 管道转换（与文件模式输出字节一致）
```

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.4.1 | built | 首个适配版本，零补丁，直接用 OHOS aarch64 clang 15 交叉编译 |

详细适配记录见 `1.4.1/notes.md`。
