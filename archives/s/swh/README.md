# SWH

Steve Harris 的 LADSPA 音频插件集合，提供放大、滤波、均衡、延迟和效果处理。

## OHOS 适配

保留原始 Perl C 生成器与全部插件；用 Python 标准库生成兼容 XML::Parser
Tree 的 JSON，避免不兼容的 Perl XS 模块。C99 头文件函数采用 static inline。
OHOS 的短任务 FFT 规划使用 FFTW_ESTIMATE，保留变换与音频结果断言。
不承诺最优长期 FFT 性能，也不把离线处理测试当作硬件音频 I/O 验证。

## 依赖

运行依赖 FFTW 单精度库；构建依赖已发布 Perl、Python 和 CMake。
Conan 管理依赖和 LADSPA_PATH；没有可执行 CLI，无需 commands.json。

## 参考

[上游](https://plugin.org.uk/)；[上游源码](https://github.com/swh/ladspa)。
