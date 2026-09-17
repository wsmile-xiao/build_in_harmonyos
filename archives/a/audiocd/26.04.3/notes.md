# audiocd 26.04.3 OHOS 适配笔记

## 背景

audiocd（KDE Gear 26.04.3，tarball 名 audiocd-kio）是 KDE 的音频 CD 抓取栈：
上游形态 = audiocd:// KIO worker（kio_audiocd）+ KCM 配置模块（kcmaudiocd）+
可复用的 audiocdplugins 编码器库与 wav/flac/vorbis/lame/opus 编码器插件。

平台任务 #3888（积分赛主池）。前置 libkcddb/26.04.3（#9143，已发布）。

## 编译环境

- 构建系统: cmake (ECM/KDEInstallDirs/KDECMakeSettings)
- 编译日期: 2026-09-15
- 编译器: clang 15 (aarch64-unknown-linux-ohos, libc++)
- conan profile: ohos-aarch64
- 状态: built

## 适配决策（核心）

1. **裁剪 KIO worker 与 KCM 模块**：
   - KF6::KIO / KF6::KCMUtils / KF6::Solid 未发布到 ohpcd 制品仓；
   - worker 的抓取核心依赖 cdparanoia 的 cdda_* API 直接访问 /dev/sr0 型
     光驱设备节点——OHOS PC 无光驱；
   - 交付物收敛为 audiocdplugins 库 + 5 个编码器插件（嵌入型用法，
     KAudioCreator 系应用直接集成）。

2. **sink 抽象替代 KIO::WorkerBase**：上游 encoder 只调用 worker 的
   `data(QByteArray)`（转发编码块）。新 `AudioCDDataSink` 抽象接口保留
   完全相同的调用语义，插件 ABI 的 `create_audiocd_encoders` 符号保留。

3. **cdparanoia 依赖剔除**：唯一残留消费者（encodercda.cpp）只需两个
   固定 Red Book 常量（CD_FRAMESIZE_RAW=2352 / CD_FRAMESAMPLES=588），
   收敛进自包含 audiocdcdio.h。

4. **KProcess → QProcess**（lame/opus 插件）：operator<< / execute() /
   setOutputChannelMode 是 KCoreAddons 便利 API；QProcess 等价 =
   setProgram/setArguments + start() + waitForFinished() +
   setProcessChannelMode。

## 关键踩坑（按时间序）

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | QWidget 找不到 | 上游把 Qt::Widgets 链接只放在 worker 目标 | plugins/CMakeLists 给 audiocdplugins 加 Qt6::Widgets（PUBLIC） |
| 2 | audiocd_kio_debug.h 找不到 | 该头由 worker 目标的 ecm_qt_declare_logging_category 生成 | 在 audiocdplugins 库目标上声明同名 category；删除 encoder.cpp 里的手写 Q_LOGGING_CATEGORY（重复符号） |
| 3 | KCDDB::Title 等枚举未声明 | 重写 audiocdencoder.h 时丢了 `using namespace KCDDB` | 恢复（上游就有） |
| 4 | setOutputChannelMode 不存在 | KProcess API，QProcess 叫 setProcessChannelMode | 改名 |
| 5 | **dlopen "Permission denied"** | **lld 默认 max-page-size=0x10000 会把 .dynsym/.dynstr 放进独立高址 RW LOAD 段（7 段布局），OHOS musl loader 拒绝 mmap** | 链接 flag `-Wl,-z,max-page-size=0x1000` 恢复常规 4 段布局 |
| 6 | patchelf sweep 后 dlopen 再挂 | **OHOS patchelf --replace-needed 会把 program header 重排成同样的 7 段被拒布局**（27KB/4段 → 198KB/7段） | 删除 R05 sweep；绝对路径 DT_NEEDED 保留（libkcddb #9143 先例，CI 环境路径一致可加载） |
| 7 | 插件 NEEDED '../../bin/libaudiocdplugins.so' | CMake 对同构建树 target 用相对路径链接，安装后失效 | 插件用 `-L build/bin -laudiocdplugins` 裸名链接 + add_dependencies 保序 |
| 8 | -l 后 include/链接传播丢失 | 字符串链接项不传播 target 的 usage requirements | 各插件补 target_include_directories（source/../ + binary/../）+ 显式 KF6::ConfigGui/KCddb6/Qt::Widgets |
| 9 | "target pattern contains no '%'" | OGGVORBIS::vorbis 接口引用 Ogg::ogg（conan libogg target）不可见；且 OggConfig 把 OGG_LIBRARY 普通变量覆盖为 target 名 | plugins/CMakeLists 里 find_package(Ogg CONFIG) + 捕获/恢复 OGG_LIBRARY/OGG_INCLUDE_DIR 实路径 |
| 10 | vorbis 插件不构建 | check_library_exists(vorbis vorbis_bitrate_addblock) 交叉链接解析不了传递 libogg | HAVE_LIBVORBISENC2=1 硬置（API 自 1.1/2004 存在，nm -D 验证） |
| 11 | 'ogg/ogg.h' 找不到 | conanfile 把 OGG_INCLUDE_DIR 设成了 libvorbis 的 include | 修正为 libogg 包的 include |
| 12 | libogg 版本冲突 | flac/1.5.0 锁 1.3.5，libvorbis/1.3.7 锁 1.3.6 | `self.requires("libogg/1.3.6", override=True)`（稳定 C ABI） |
| 13 | test 阶段引用旧包路径 | 旧 audiocd 包在缓存中残留，test_package CMakeCache 复用旧 find_library 结果 | 调试时 conan remove + 清 ~/.conan2/p/b/audio*；正常流程不受影响 |

## 依赖版本

- qtbase/6.11.1, kconfig/6.26.0, kcoreaddons/6.26.0, ki18n/6.26.0,
  kwidgetsaddons/6.26.0, libkcddb/26.04.3
- flac/1.5.0, libvorbis/1.3.7, libogg/1.3.6 (override), lame/3.100, opus/1.5.2
- ecm/6.26.0 (tool)

## 验证结果

```
conan create . --build=audiocd/* -pr:h=ohos-aarch64 -pr:b=default -r=ohpcd
→ audiocd/26.04.3: Package '08149eb3890c4b1d2687a38b0ed16edb39e899dd' built
→ test_package: 35/35 assertions ALL PASS
```

上游无测试套件（无 tests/ autotests/ add_test()）——test_package 消费者测试
覆盖（35 断言）：sink 抽象、wav RIFF 头生成（含小端 size 字段）、cda 帧透传、
flac/vorbis/opus 编码器构造与运行时 round trip、插件符号解析、KCDDB CDInfo
管线、Red Book 常量。

## 产物

- lib/libaudiocdplugins.so（含 audiocdencoder.h / audiocdcdio.h /
  audiocdplugins_export.h / audiocdplugins_version.h 公共头）
- lib/libaudiocd_encoder_{wav,flac,vorbis,lame,opus}.so（编码器插件）

## 注意事项

- 消费者加载插件：把包 lib/ 目录加入 QCoreApplication::libraryPaths()，
  AudioCDEncoder::findAllPlugins() 自动发现 libaudiocd_encoder_*.so。
- lame/opus 编码器运行时 spawn 外部 opusenc/lame 二进制（上游设计），
  缺工具时插件优雅降级（init() 返回 false）。
- KIO worker / KCM 模块不随本包交付（kio/kcmutils/solid 未发布 + 无光驱）。
