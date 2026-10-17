# dbeacon

dbeacon 是一个用 C++ 编写的组播连通性 beacon：它在指定的 IPv4/IPv6 组播组上
周期性宣告自身，并收集同组其它 beacon 的可达性、丢包、时延与抖动统计，
可选地把统计结果导出为 XML，供上游 `contrib/matrix.pl` 等矩阵站点使用。

## 功能概述

- IPv4 与 IPv6 组播 beacon 收发（`-4` / `-6` 强制族），同时支持 ASM 与 SSM。
- 周期性统计并输出 XML dump（`-d FILE`，间隔 `-I N`），供矩阵/CGI 消费。
- 内建 SSM Ping 服务端能力（`-P`）。
- 支持配置文件、syslog、daemonize、pidfile、带宽报表（`-U`）与外部命令挂钩（`-L`）。
- 命令行入口为 `bin/dbeacon`，参数见 `docs/dbeacon.1`（随包安装到 `share/man/man1/`）。

## OHOS 适配

- 上游为纯 Makefile 工程（无 configure），配方按 R33 从 profile 的
  `tools.build:compiler_executables` 取 clang++ 绝对路径，以 `make -j1 CXX=<clang++>` 构建，
  并固定 `cwd=self.source_folder`（上游 Makefile 不支持 out-of-tree 构建）。
- 源码是 C++ 翻译单元（`<map>`/`<string>` 等）且含 `using namespace std;`，
  未限定的 POSIX `bind(2)` 在 libc++ 下会被 `std::bind` 模板抢占而编译失败；
  `patches/0001-qualify-bind-call-with-global-scope.patch` 把该调用限定为 `::bind`，
  对 glibc/libstdc++ 与其它平台行为完全一致（无平台条件编译）。
- 运行时需要具备组播能力的网络接口；设备实测 IPv4 组播组加入与 dump.xml 产出正常。
- 上游自报版本串仍为 `0.3.9.2p1`（未随 0.4.0 发布更新），本包版本号以官方 tag
  `dbeacon-0.4.0` 与上游 Changelog 为准。

## 依赖关系

- 编译依赖：无第三方依赖，仅使用平台 C/C++ 运行时。
- 运行依赖：无（`libc++`/`libm` 由平台提供）。

## 参考资料

- 上游仓库：<https://github.com/uoaerg/dbeacon>（Debian `d/watch` 跟踪的上游）
- 原始项目（已归档，无 0.4.0 tag）：<https://github.com/hugosantos/dbeacon>
- 手册页：`docs/dbeacon.1`、协议说明 `docs/PROTOCOL`
