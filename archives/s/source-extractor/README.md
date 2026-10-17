# source-extractor (SExtractor)

## 是什么

SExtractor（Source Extractor）是 AstrOmatic 软件套件的核心工具，从天文图像
（FITS）中提取天体源并生成星表（catalog）。Debian 打包名 source-extractor
（astromatic 1.2 起由 sextractor 更名），上游代码库 github.com/astromatic/sextractor。

## 功能

- 源检测、去卷积、测光、形状参数与星等估算
- FITS / 加权图 / 卷积核 / 神经网络分类
- 输出 XML / ASCII / LDAC 星表
- 配套 `ldactoasc`：LDAC 星表转 ASCII

## OHOS 适配

- **构建**：autotools，GitHub archive 无预生成 configure → autoreconf 自举；
  config.guess/config.sub 内联补 HarmonyOS 识别。
- **线程**：`--enable-threads=no`——OHOS pthread.h 未声明 `pthread_cancel`
  （threads.h QPTHREAD_CANCEL 链接失败），单线程模式完全可用。
- **cwd 环境变量**：configure 重执行 shell 需要当前目录环境变量预置
  （设备 toybox sh 不 export，bash getcwd 失败）。
- **依赖头文件/库**：-I 经 CFLAGS 注入；cfitsio.a 需 -Lz -lz。
- 详细适配见 `2.28.2/notes.md`。

## 依赖关系

| 依赖 | 版本 | 用途 |
|------|------|------|
| fftw3f | 3.3.9.1 | 单精度 FFT（ACX_FFTW fflag=yes） |
| openblas | 0.3.34 | BLAS/LAPACK（--enable-openblas） |
| cfitsio | 4.6.4 | FITS I/O（含压缩 FITS） |
| zlib | 1.3.1.1 | cfitsio.a 传递依赖 |

## 参考资料

- 官网：https://www.astromatic.net/software/sextractor
- 源码：https://github.com/astromatic/sextractor
