# source-extractor 2.28.2 适配笔记（OHOS PC, aarch64）

上游：SExtractor（Source Extractor），github.com/astromatic/sextractor。
Debian 包名 source-extractor（astromatic 1.2 起更名）；本配方采用 Debian 名
以对齐 astromatic 元包 Recommends。

## 构建结论（conan create 本地预检 PASS）

- conanfile.py: name=source-extractor / version=2.28.2 / package_type=application
- 构建系统：autotools（GitHub archive 无预生成 configure → autoreconf 自举）
- 依赖：fftw3f/3.3.9.1（单精度 FFT，ACX_FFTW fflag=yes）、openblas/0.3.34、
  cfitsio/4.6.4、zlib/1.3.1.1（cfitsio.a 传递依赖）
- 上游官方测试：make check（tests/modelfit.test）→ 1 PASS，真实执行
- 产物：bin/sex + bin/ldactoasc + share/sextractor 配置/卷积核 + man 页

## OHOS 适配点

1. **config.guess/config.sub**：autoreconf 生成的版本不含 HarmonyOS 分支，
   在 build() 内联补 `*:HarmonyOS:*:*)` 识别 → aarch64-unknown-linux-ohos
   （同 scamp）。设备 uname -s = HarmonyOS。
2. **configure 重执行 shell 的 cwd**：profile buildenv 设 CONFIG_SHELL=bash，
   configure 自举后以 bash 重执行；OHOS 设备 toybox sh 不 export 当前目录
   环境变量，bash 启动 getcwd() 失败 → configure 报 "working directory
   cannot be determined"。修复：build() 内预置当前目录环境变量
   （os.environ）再 configure。
3. **--enable-threads=no**：OHOS pthread.h 未声明 pthread_cancel，
   threads.h 的 QPTHREAD_CANCEL 会链接失败（同 swarp 处理）。单线程模式
   完全可用。
4. **依赖头文件 -I**：SExtractor 的 configure 宏只做存在性检查，不把
   include 路径写入 AM_CPPFLAGS —— 用 AutotoolsToolchain.extra_cflags
   注入 fftw/openblas/cfitsio 的 include 路径。
5. **cfitsio + zlib**：cfitsio 静态库含 deflate/inflate 未定义符号，
   AC_CHECK_LIB 链接测试需 `-L<zlib>/lib -lz`（extra_ldflags 注入，同 swarp）。
6. **out-of-source 构建子库路径**：src/Makefile.am 的 fits/wcs/levmar 子库
   路径 `$(srcdir)/fits/libfits.a` 等改 `$(builddir)`（patch 0001，同 swarp）；
   Makefile.am 的 `config/* xsl` dist_pkgdata_DATA glob 加 `$(srcdir)`
   前缀（patch 0002，同 scamp）。
7. **测试数据**：tests/ 的 FITS 图与配置（galaxies*.fits 等）out-of-source
   构建下须复制到 build/tests 再 make check；sex 动态链接 conan 库，
   make check 用 conanrun 环境（LD_LIBRARY_PATH）。

## 未适配/已知

- 多线程禁用（--enable-threads=no）；未做 pthread_cancel 头文件补丁。
- FFTW 单精度库未启用多线程（fftw3f 默认 threads=False，ACX_FFTW 仅 WARN
  不阻塞）。
- 上游仅 1 个自动化测试（modelfit.test），无整目录测试套件。

## 参考

- 同生态先例：scamp（config.guess 内联补丁）、swarp（threads=no + zlib）
- astromatic 元包依赖本配方（requirements-only 聚合）。
