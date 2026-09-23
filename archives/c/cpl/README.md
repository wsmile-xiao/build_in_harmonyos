# ESO Common Pipeline Library（CPL）

> ESO 为天文数据处理管线打造的 ISO-C 工具库，提供图像、星表、矩阵、属性表、WCS、拟合与 recipe 插件接口等通用能力。

## 简介

CPL（Common Pipeline Library）是欧洲南方天文台（ESO）为 VLT 等仪器数据处理管线开发的标准化 C 语言库，涵盖底层数据类型（image、table、matrix、vector、propertylist）、FITS 读写（基于 CFITSIO）、世界坐标系（基于 WCSLIB）、数值拟合与傅里叶变换（基于 FFTW），以及管线 recipe 的标准应用接口与动态加载机制。除天文管线外，也可作为通用图像与信号处理框架使用。

7.4 是 2026 年 6 月发布的版本，主要增加 PyCPL/PyHDRL 构建支持与 pkg-config 文件。

## OHOS 适配要点

- **构建系统**：Autotools，上游自带 `configure`，无需 `autoreconf`；`make check` 即官方测试套件（54 项）。
- **零源码补丁**：复用同门库 libcext/1.3.2 的构建时 `configure` 调整（`umask 022`、真实 shell、编译器路径回退、`ld.lld` 宿主库探测）。
- **系统 cext**：上游默认使用系统安装的 libcext，不构建源码包内附带的 `libcext/` 子目录。
- **已知裁剪**：FFT 支持关闭（注册表 fftw 缺单精度库）、线程支持关闭（当前 cfitsio 非线程安全构建）、gasgano/Java 绑定未构建（上游默认关闭）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libcext | 1.3.2 | ESO C 扩展库，CPL 的系统 cext 依赖 |
| cfitsio | 4.6.4 | FITS 读写（上游要求 ≥ 3.35） |
| wcslib | 8.4 | 世界坐标系（上游要求 ≥ 4.16） |

编译工具：clang、autoconf 系工具链（`autoconf` 仅 wcslib 需要；CPL 自带 `configure`，不需要）。

## 功能验证

```bash
# 消费者视角：链接 cpl::cpl，跑 6 组真实 API 断言
conan create archives/c/cpl/7.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
./test_cpl
```

## 参考

- 官网: https://www.eso.org/sci/software/cpl/
- 下载页: https://www.eso.org/sci/software/cpl/download.html
- 在线手册: https://ftp.eso.org/pub/dfs/pipelines/libraries/cpl/docs/
