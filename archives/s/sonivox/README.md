# sonivox

`sonivox` 是 Sonic Network EAS（Embedded Audio Synthesis）波表 MIDI 合成器库的 CMake 移植版
（AOSP `platform_external_sonivox` 的 fork，pedrolcl/sonivox 维护）。库内嵌采样音色，
无需外部音色库即可实时合成 GM MIDI，资源占用低，适合小型/嵌入式设备；也支持加载 DLS
音色库提升渲染质量。库本身只做合成，不提供 MIDI 输入与音频输出接口（由使用方提供）。

## Versions

| Version | Status |
| --- | --- |
| 3.6.16 | built |

Homepage: https://github.com/pedrolcl/sonivox

## 产物

- `lib/libsonivox-static.a` 静态库（默认）；`-o sonivox*:shared=True` 时为 `lib/libsonivox.so`
- `include/sonivox/*.h` 公共头文件（eas.h / eas_types.h / eas_report.h / eas_reverb.h / eas_chorus.h）
- `bin/sonivoxrender` 命令行工具：`sonivoxrender file.mid > out.pcm`
- `lib/cmake/sonivox/`、`lib/pkgconfig/sonivox-static.pc`

## 用法示例

```bash
# 消费者（Conan）
conan install --requires=sonivox/3.6.16
# test_package 即消费者 API 回归：EAS_Config 契约 + SMF 渲染非静音 + 坏文件负例
```
