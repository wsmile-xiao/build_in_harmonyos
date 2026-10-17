# pianobar

`pianobar` 是 Pandora 个性化在线电台的免费开源控制台客户端，支持站点管理、
歌曲评分、播放历史、自定义快捷键、remote/eventcmd 接口与代理。

- 上游项目：<https://6xq.net/projects/pianobar/>（镜像 <https://github.com/PromyLOPh/pianobar>）
- 许可证：MIT
- 构建系统：raw Makefile
- Conan 包：`pianobar/2024.12.21`

## 包含的命令

| 命令 | 用途 |
| --- | --- |
| `pianobar` | Pandora 控制台播放器主程序 |

同时交付 `libpiano` C API（静态库 `lib/libpiano.a` 与头文件 `include/piano.h`），
供第三方 Pandora 客户端复用。

## HarmonyOS 适配

HarmonyOS 版本使用官方 2024.12.21 发布包与 Conan 构建：pkg-config 发现
Conan 依赖（libao/curl/json-c/libgcrypt/ffmpeg），源码树内 `make -j1`，
手工归档 `libpiano.a`，最终二进制按需自签名。上游无测试套件，
`test_package` 以 18 个消费者断言补位（14 个 libpiano C API + 4 个 CLI 行为）。

具体构建和测试结果见 `2024.12.21/notes.md`。
