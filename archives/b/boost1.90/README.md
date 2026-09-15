# boost1.90

Boost C++ Libraries 1.90.0 — 独立包名归档（与 `boost/1.90.0` header-only 配方并行维护）。

手动编译 4 个非 header-only 库（b2 构建系统在 OHOS 不兼容，E068）：

- **filesystem**（9 源文件，跳过 windows_file_codecvt.cpp）
- **regex**（1.90 精简为 2 源文件：posix_api/wide_posix_api，ICU-independent）
- **program_options**（10 源文件，跳过 winmain.cpp）
- **iostreams**（zlib 后端 4 源文件，依赖 conan zlib/1.3.1）

system / date_time 自 Boost 1.69 起 header-only，随头文件一起安装。

与 1.84 系列的差异：上游已原生为 `__OHOS__` 守卫 `pthread_setcancelstate`
（boost/core/detail/sp_thread_sleep.hpp），无需 boost1.84 的 0001 补丁。
