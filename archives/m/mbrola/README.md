# mbrola

MBROLA 语音合成引擎（基于双音素拼接的便携式合成器），上游版本 3.3。

## 上游信息

- 上游仓库：https://github.com/numediart/MBROLA
- 版本：`3.3`（tag `3.3`，commit `6176f70`）
- 许可证：AGPL-3.0-or-later
- 源码包：`https://codeload.github.com/numediart/MBROLA/tar.gz/refs/tags/3.3`
  （GitHub 官方下载端点，与 archive 链接同一实体）
  SHA256 `c01ded2c0a05667e6df2439c1c02b011a5df2bfdf49e24a524630686aea2b558`

## 功能

MBROLA 接受音素序列（`.pho`，含音素时长与基频曲线）和双音素数据库，
输出 16 位线性 PCM 音频（`raw`/`au`/`wav`/`aiff`）。它不是文本转语音
系统，需要上游文本处理模块提供音素命令。

```bash
mbrola <database> <pho_file>+ <output_file>
mbrola -i <database>        # 查看数据库信息
mbrola -t 1.2 -f 0.8 db x.pho out.wav   # 时长/频率比例
```

## OHOS 适配

MBROLA 3.3 是便携 C89 程序，仅依赖 libc 与 libm。上游 Makefile 自带
平台可移植性定义（`-DLITTLE_ENDIAN`、ROM 数据库支持、信号处理），
OHOS/aarch64 下**无需任何源码补丁**；配方（Conan recipe）仅把编译器
替换为 Conan profile 提供的 OHOS clang，并安装产物：

| 路径 | 说明 |
| --- | --- |
| `bin/mbrola` | 命令行合成器 |
| `licenses/LICENSE` | 上游 AGPL-3.0 许可证 |
| `share/doc/mbrola/README.md` | 上游说明文档 |

## 依赖

无编译期依赖（仅 libc/libm）。可选：安装语音库（如仓库中已适配的
`mbrola-gr2`）后即可实际合成语音。

## 测试

本包消费者测试以已发布的 `mbrola-gr2` 希腊语语音库为数据，真实驱动
`bin/mbrola`：CLI 契约、数据库信息、上游 211 条音素示例的真实合成、
WAV/AU/RAW 输出、时长/幅度/确定性、`-t/-v/-f/-l` 运行选项、
`-W/-w` ROM 往返一致性以及 `-e` 错误恢复。上游无自动化测试套件
（Makefile `check` 目标所需的 `UTILITY_TCTS` 语料不在发布包内）。

## 使用示例

```bash
conan install --requires=mbrola/3.3
mbrola share/mbrola/gr2/gr2 share/mbrola/gr2/TEST/DEMOST~1.PHO output.wav
```
