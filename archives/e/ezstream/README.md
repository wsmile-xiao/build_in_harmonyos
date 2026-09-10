# ezstream

[ezstream](https://icecast.org/ezstream/) 是 Xiph.Org 官方维护的 Icecast 流媒体
源客户端（命令行工具）：读取本地音频文件或外部程序输出，可选地调用外部
解码器/编码器转码，然后通过 libshout 将流推送到 Icecast 流媒体服务器。
支持 Ogg Vorbis/FLAC/Theora/WebM/Matroska，MP3/AAC（外部编码器），
XML 配置文件，以及通过 taglib 读取媒体元数据（歌名/艺术家）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.2 | published | 2021-02-12 上游稳定版，HarmonyOS PC (aarch64) 适配 |

## 构建

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=~/.conan2/profiles/ohos-aarch64 \
  -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```

产物：`bin/ezstream`、`bin/ezstream-cfgmigrate`、`bin/ezstream-file.sh`

## 依赖

- libshout/2.4.6（REQUIRED）
- libxml2/2.15.3（REQUIRED）
- taglib/1.13.1（REQUIRED，C bindings）
- check/0.15.2（仅上游测试）

## 适配说明

见 [1.0.2/notes.md](1.0.2/notes.md)。
