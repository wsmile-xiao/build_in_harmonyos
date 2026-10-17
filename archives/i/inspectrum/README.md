# inspectrum

inspectrum 是一个 Qt5 编写的无线电信号频谱分析工具：读取原始 IQ 采样文件
（cfile/cf32、cs16、cs8、cu8、f32、sigmf-data 等格式），渲染频谱图
（spectrogram）与时域波形，支持采样率设置与文件格式覆盖。

- 上游: https://github.com/miek/inspectrum
- 许可: GPL-3.0-or-later
- 适配版本: 0.3.1（OHOS aarch64）
- 依赖: qt5-qtbase/5.15.2.2、fftw3f/3.3.10、liquid-dsp/1.8.2

## 适配说明

- 构建系统: CMake（conanfile.py 内完成全部 OHOS 适配，无源码补丁）
- 上游 FindFFTW/FindLiquid 模块通过预设缓存变量指向依赖包内绝对路径
- GUI 程序: OHOS 无显示服务器，自动化调用须设 `QT_QPA_PLATFORM=offscreen`；
  GUI 进入事件循环后不会自行退出，冒烟验证需限时 kill

## 使用

```
inspectrum [options] file
  -r, --rate <Hz>      设置采样率
  -f, --format <fmt>   设置文件格式（cfile/cf32/cs16/cs8/sigmf-meta 等）
```

详细适配记录见 `0.3.1/notes.md` 与 `0.3.1/reports/test-report.md`。
