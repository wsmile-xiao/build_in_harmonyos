# wmmisc

wmmisc 是 WindowMaker DockApp 系统监视器，以 dockapp 图标形式监控：
登录用户数、进程总数、运行中进程数、fork 计数与系统负载均值。

## OHOS 适配

- **构建系统**: autotools（conan + ohos-aarch64 profile）
- **依赖链**: libdockapp/0.7.3（传递引入 libx11/6.4.0、libxext/6.4.0、libxpm/3.5.17、libxcb 等 X11 全家桶）
- **适配补丁**: 移除 glibc 专有头文件（`bits/getopt_core.h`、`bits/types/time_t.h`），见 `patches/`

## 版本目录

- `1.2/` — 当前版本（状态: built，含 conanfile.py / conandata.yml / test_package / packaging）

## 使用

打包产物 `1.2/packaging/wmmisc-1.2-ohos-aarch64.tar.gz` 自包含全部共享库依赖，
解包后通过 `LD_LIBRARY_PATH=lib:lib/external ./bin/wmmisc` 运行
（OHOS 加载器不读 DT_RUNPATH）。
