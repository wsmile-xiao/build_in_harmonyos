# shntool

shntool 是一个多媒体音频文件处理工具套件，主要用于操作和分析无损音频格式（WAV、FLAC、APE 等）。

## 功能

- **len**: 显示 PCM WAVE 数据的长度、大小和属性
- **fix**: 修复 CD 质量 PCM WAVE 数据的扇区边界问题
- **hash**: 计算 PCM WAVE 数据的 MD5 或 SHA1 指纹
- **pad**: 用静音填充不在扇区边界上的 CD 质量 PCM 文件
- **join**: 将多个文件的 PCM WAVE 数据合并为一个文件
- **split**: 将一个文件的 PCM WAVE 数据分割为多个文件
- **cat**: 将 PCM WAVE 数据写入终端
- **cmp**: 比较两个文件中的 PCM WAVE 数据
- **cue**: 从一组文件生成 CUE 表或分割点
- **conv**: 将文件从一种格式转换为另一种格式
- **info**: 显示 PCM WAVE 数据的详细信息
- **strip**: 去除额外的 RIFF 块或写入标准头
- **gen**: 生成包含静音的 CD 质量 PCM WAVE 数据文件
- **trim**: 从文件两端去除 PCM 静音

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 3.0.10 | published | 2026-06-04 | 首次编译，HarmonyOS aarch64 适配 |

## 来源

- 官方站点: https://shnutils.freeshell.org/shntool/
- Debian 源: https://deb.debian.org/debian/pool/main/s/shntool/