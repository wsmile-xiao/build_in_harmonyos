# ACE for HarmonyOS

ACE (ADAPTIVE Communication Environment) 在 HarmonyOS PC (aarch64) 上的编译记录。

## 版本

- **8.0.5** (built): ACE 核心框架，GNU Make + MPC 构建，产物为 libACE 系列 6 个动态库。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | ACE |
| 官网 | https://www.dre.vanderbilt.edu/~schmidt/ACE.html |
| 下载 | GitHub DOCGroup/ACE_TAO（镜像 gh-proxy.com） |
| 许可证 | DOC |

## 编译要点（OHOS 适配）

ACE 8.0.5 源码结构为 ACE/ + TAO/ 分离，无 ACE_wrappers，无 configure 脚本，采用传统 GNU Make + MPC：

1. 编写 `ace/config.h`：include `ace/config-linux.h`，无条件关停 ACE_HAS_UALARM / ACE_HAS_NETLINK / ACE_HAS_AIO_CALLS，定义 ACE_LACKS_PTHREAD_CANCEL（R8：不写 `__OHOS__` 条件编译）
2. 编写 `include/makeinclude/platform_macros.GNU`：include platform_linux_clang.GNU 并设置 INSTALL_PREFIX
3. 用 MPC 生成 makefiles：perl bin/mwc.pl -type gnuace ACE.mwc（需设 ACE_ROOT / MPC_ROOT）
4. 编译：`make -j1 ACE`（ace/），再在 Compression/、ETCL/、Monitor_Control/ 各 `make -j1`（E074：禁止 -jN）
5. 安装：各目录 `make -j1 install`（E216：`shared`→`shared_libs`/`static_libs`；默认 shared=True）

### 关键适配点

- E119 sockaddr_storage 冲突：OHOS SDK 的 linux/socket.h 与 sys/socket.h 均定义 sockaddr_storage，关停 ACE_HAS_NETLINK 规避
- OHOS musl 缺失 API：ualarm、pthread_cancel、POSIX AIO 均不可用，关停对应 ACE 特性宏
- make 内置 CXX 无效：系统 make 的 CXX 变量被 CI 环境硬编码为无效路径，需显式指定 clang
- MPC 依赖：ACE tarball 不含 MPC 核心模块，conan 配方双 source 固定 DOCGroup/MPC commit（非 master）
- Conan 2 env 传参：self.run 的 env 参数只接受环境文件名，设置变量须用 Environment 工具类

## 验证结果

- conan-verify 8 道门禁全部通过（G0-G4 + L2/L4/L5）
- test_package 消费者测试通过：ACE_OS::getpid / ACE_VERSION / ACE_Message_Block
- 代表性回归测试：ACE_Test / Basic_Types_Test / SString_Test / Get_Opt_Test 全部 exit=0

## 依赖

- MPC（构建期源码依赖，DOCGroup/MPC @ 420e24790d349057e6463890ae993eb61eecc273）
- 无其他外部库依赖（ACE 为自包含框架）
