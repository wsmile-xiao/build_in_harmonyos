# audacious-plugins 4.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码解压到 ~/tmp/builds/audacious-plugins-4.5.1.work/
2. configure:
   ```
   ./configure --prefix=$DEFAULT_PREFIX --disable-gtk --disable-qt --disable-opus --disable-wavpack --disable-neon --disable-ffaudio
   ```
3. make -j1
4. make install DESTDIR=$TEST_PREFIX (staging)
5. make install (本地安装到 ~/usr/local)

## 遶到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure失败：缺gtk+-3.0 | 鸿蒙无GTK | --disable-gtk --disable-qt |
| 2 | configure失败：缺opusfile>=0.4 | 无预编译包 | --disable-opus |
| 3 | configure失败：缺neon>=0.27 | 无预编译包 | --disable-neon |
| 4 | configure失败：缺wavpack | 无预编译包 | --disable-wavpack |
| 5 | ffaudio链接失败：libavcodec静态库无PIC | FFmpeg静态库不支持-fPIC | --disable-ffaudio |
| 6 | mpris2编译失败：python3找不到libintl.so.8 | LD_LIBRARY_PATH未包含hnp lib目录 | 设置LD_LIBRARY_PATH包含/data/service/hnp/python.org/python_3.12/lib |

## 源码修改

- 0001-build-aux-config.guess.patch: 添加HarmonyOS识别
- 0002-build-aux-config.rpath.patch: 更新config.rpath以适配平台

## 依赖版本

- audacious: 4.5.1
- glib-2.0: 2.88.0
- libmpg123: 1.32.9
- vorbis: 1.3.7
- flac: 1.4.3
- alsa: 1.2.12
- libpulse: 17.0
- libxml2: 2.x
- zlib: 1.2.13
- gio: 2.88.0

## 验证结果

```bash
# 32个插件.so文件正确安装到 ~/usr/local/lib/audacious/*/ 
# 包含 Input(9), Output(4), Effect(10), General(2), Container(6), Transport(1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| audacious-plugins-4.5.1-ohos-aarch64.tar.gz | ~XX MB | 预编译包（strip+签名） |
| audacious-plugins-4.5.1-ohos-aarch64-debug.tar.gz | ~XX MB | 调试包 |

## 注意事项

- ffaudio(FFmpeg解码)已禁用，因静态libavcodec不支持PIC
- opus/wavpack/neon已禁用，因缺少对应预编译包
- GTK/Qt已禁用（纯插件模式，无GUI界面）
- 需设置LD_LIBRARY_PATH确保gdbus-codegen能正常运行
---

**编译结束**: 2026-05-29 13:56
**最终状态**: published
