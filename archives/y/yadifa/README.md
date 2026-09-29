# yadifa

YADIFA 权威 DNS 服务器套件（Yet Another Domain Information File Application）。

## 简介

YADIFA 是 EURid 维护的权威域名服务器实现，纯 C 编写，含运行期 DNSSEC 签名与
密钥滚动能力。本包发布的是整套可执行文件：

| 可执行 | 作用 |
|--------|------|
| yadifad | 权威名称服务进程（支持 RFC 1035/1912/2136/2181 等） |
| yadifa | 控制与查询客户端（NOTIFY/RECONFIG/STOP 与任意查询） |
| yadifa-keygen | TSIG 与 DNSSEC 密钥生成 |
| yadifa-zonesign | 区域文件离线签名 |
| yakeyrolld | KSK/ZSK 密钥滚动守护工具 |

库面（dnscore / dnssec / libyaml 等）按上游内部静态库使用，不作为对外消费接口发布，
故包内只交付可执行文件。

## 官网

https://www.yadifa.eu

源码仓库：https://github.com/yadifa/yadifa

## 许可证

BSD-3-Clause

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 3.0.9 | built | 2026-09-25 | cmake | 3（均为 portability） |

### 平台适配说明

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| OpenSSL 找不到 | 上游自带 cmake/FindOpenSSL.cmake 只探测硬编码系统路径，Conan 依赖不可见 | 补丁 0001 把无条件 set 改成 if(NOT DEFINED) 以允许 -D 注入，配方注入 openssl 的 package_folder |
| pthread 与 affinity | musl/OHOS 无独立 libpthread、无 pthread_setaffinity_np | 补丁 0002 回落裸 pthread；补丁 0003 守卫 affinity；build() 加 -D__MUSL__ |
| 无 OHOS CMake 平台模块 | 上游不认 os=OHOS | 交叉构建按 Linux 描述（CMAKE_SYSTEM_NAME=Linux + aarch64） |
| 安装目录分层 | yadifad 默认装 sbin，Conan 包只暴露一个 bin | BINDIR 与 SBINDIR 同为 bin，etc/var 收进 res/ |
| /tmp 只读（E002） | 上游测试把临时路径硬编码到 /tmp，大面积 EROFS | 仅测试阶段注入 LD_PRELOAD 路径重定向 shim，打包产物与运行路径不受影响 |

### 测试口径

上游 860 条静态 add_test 声明（lib 与 lib/*/tests 下的 CMakeLists），CTest 实际注册 858 条，
本包在 build() 内真实执行全部注册用例并把逐组结果记在版本级 notes.md 的五维账本里；
未通过项按根因分组申报，不缩小分母、不使用任何关闭测试的开关。

### 源码来源说明

取上游官方 GitHub tag 归档 v3.0.9（R39 官方源头口径），sha256 见版本级 conandata.yml 与
manifest.yaml；版本级 notes.md 记录取源与哈希读数。
