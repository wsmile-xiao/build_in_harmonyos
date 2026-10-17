# mbrola-gr2

MBROLA 的希腊语男声 GR2 双音素数据库。

## 上游信息

- 上游语音库：https://github.com/numediart/MBROLA-voices
- 语音提供者：Gerasimos Xydas，University of Athens
- 版本：`0.0.20010521`
- 数据库格式：MBROLA `2.060`
- 采样率：22050 Hz
- 双音素数量：1081

## OHOS 适配

GR2 是与处理器架构无关的语音数据，不需要编译或平台补丁。Conan 配方
将数据库安装到 `share/mbrola/gr2/gr2`，该路径与 eSpeak NG 文档中的
Unix MBROLA voice 布局一致。

消费者测试会解析数据库头和全部双音素索引，并用上游 PHO 样例验证音素
集合、相邻双音素覆盖、时长和音高字段，不以文件存在性作为唯一结论。

## 许可证注意

本数据库使用 `LicenseRef-MBROLA-GR2` 自定义许可证。它仅允许与 MBROLA
程序配合用于语音合成，分发时必须保留许可证通知，商业销售或集成需要
数据库所有者事先许可。使用和再分发前请阅读包内 `licenses/license.txt`。

## 使用

本包只提供 voice database，不包含 `mbrola` 可执行程序。安装 MBROLA
合成器后可运行：

```bash
mbrola share/mbrola/gr2/gr2 \
  share/mbrola/gr2/TEST/DEMOST~1.PHO output.wav
```
