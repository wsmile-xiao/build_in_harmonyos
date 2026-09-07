# gadap

## 简介

GADAP (GrADS Data Interface / GrADS-OPeNDAP) 是 GrADS 气象数据分析
系统访问 OPeNDAP 站点 (in-situ/station) 数据的客户端 C++ 库。上游
2008 年由 IGES (Institute of Global Environment and Society) 开发,
提供 `gadap_open/gadap_sq_send` 等稳定 C API, 供 GrADS 内嵌调用。

## OHOS 适配

- 构建系统: autotools (tarball 自带 configure 2.59)
- 依赖: libdap/3.20.6 (DAP2 协议核心), libxml2/curl/
  libtirpc/uuid (libdap 静态链接传递需要)
- 11 个补丁: 0001 configure 平台修复 (VERSION→GADAP_VERSION 防大小写
  遮蔽 + 临时目录 mkdir -m 700); 0002-0011 libdap 3.20.6 namespace
  适配 (有限 using 声明)
- 配方 generate() 生成重定位 dap-config (libdap 包内版本 prefix=/
  硬编码路径, 打包缺陷) + LD_LIBRARY_PATH 清洗 + TMPDIR 指向 tmpfs

## 使用注意

- gadap/libdap 只支持 OPeNDAP 远程数据源 (http URL); 本地文件路径会
  在 libdap `Connect::request_dds` 空指针解引用 (上游 `_local` 分支
  `d_http=0` 设计)
- 静态库: `libgadap.a` + 头文件 `gadap.h/gadap_err.h/gadap_types.h`
- 错误码约定: `errval(GADAP_ERR_*) = -1 * 枚举值`

## 依赖

- libdap/3.20.6
- libxml2/2.15.3, curl/8.15.0, libtirpc/1.3.7, uuid/2.40.1

## 参考

- 官网: https://cola.gmu.edu/grads/gadap/
- 源码: https://archive.ubuntu.com/ubuntu/pool/universe/g/gadap/
