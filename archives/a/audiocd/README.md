# audiocd

audiocd 是 KDE 的音频 CD 抓取栈（KDE Gear 26.04.3，tarball 名 audiocd-kio）。

## 描述

上游形态包含 audiocd:// KIO worker（kio_audiocd）、KCM 配置模块
（kcmaudiocd）以及可复用的 audiocdplugins 编码器库与编码器插件
（wav/cda、flac、vorbis、lame、opus）。在 HarmonyOS PC 上交付
audiocdplugins 库与编码器插件（嵌入型集成用法），KIO worker 与 KCM
模块因 KIO/KCMUtils/Solid 未发布且平台无光驱设备而裁剪。

## 已编译版本

- 26.04.3 (2026-09-15)

## 特性

- AudioCDEncoder / AudioCDDataSink 编码器基类与数据汇抽象
- wav/cda、flac、vorbis、lame、opus 编码器插件
- 插件发现机制（create_audiocd_encoders 符号 + QLibrary 解析）
- KCDDB CDInfo 元数据管线（对接已发布的 libkcddb）

## 使用方法

```cmake
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6Config REQUIRED)
find_library(AUDIOCDPLUGINS_LIBRARY audiocdplugins)
# 编码器插件位于包 lib/ 目录（libaudiocd_encoder_*.so）
```

```cpp
#include <audiocdencoder.h>

class MySink : public AudioCDDataSink {
public:
    void data(const QByteArray &d) override { /* 消费编码输出 */ }
};

QList<AudioCDEncoder *> encoders;
// 把包 lib/ 目录加入 QCoreApplication::libraryPaths() 后：
AudioCDEncoder::findAllPlugins(&sink, encoders);
```
