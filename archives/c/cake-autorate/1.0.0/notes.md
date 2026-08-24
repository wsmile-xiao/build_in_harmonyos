# cake-autorate 1.0.0 适配记录

## 软件简介

cake-autorate 是一个 shell 脚本工具，通过测量流量负载和往返时间
（RTT）来自动调整 CAKE 带宽设置，从而最小化延迟。专为变速带宽
连接设计（LTE、Starlink、电缆调制解调器）。

- 上游：https://github.com/lynxthecat/cake-autorate
- 作者：lynxthecat
- 许可证：MIT
- 语言：Shell（纯脚本，无编译）
- 上游版本：v1.0.0（GitHub tag）
- conan 版本：1.0.0

## 源码信息

- 下载 URL：https://github.com/lynxthecat/cake-autorate/archive/refs/tags/v1.0.0.tar.gz
- SHA256：b047eba0701c706519dd46f8e28974ff7ad155b6682de3243375ce3a41eb3d9b
- 大小：49873 字节
- 选择理由：GitHub 是 cake-autorate 官方仓库，CI build_and_test.sh
  的 mirror fallback 覆盖 github.com，CI worker 可达。

## 构建与安装

cake-autorate 是纯 shell 脚本包，**无构建系统**（无 Makefile/configure）。

安装步骤：
1. `source()`：下载并解压 GitHub release tarball
2. `build()`：确保 4 个脚本可执行（chmod 755）
3. `package()`：复制文件到 package_folder
   - `bin/cake-autorate.sh` — 主监控/调整脚本
   - `bin/cake-autorate-setup.sh` — 安装助手
   - `bin/cake-autorate-config.sh` — 配置编辑器
   - `bin/cake-autorate` — OpenWrt init.d 包装器
   - `share/cake-autorate/LICENCE.md` — 许可证
   - `share/cake-autorate/Example_Starlink_config.sh` — 示例配置
   - `share/cake-autorate/CHANGELOG.md` — 变更日志
   - `share/cake-autorate/README.md` — 说明文档

## 运行时依赖

- bash（必需）
- fping（必需，RTT 测量）
- tc / iproute2（必需，CAKE 队列管理）

## 测试策略（R34）

- bash -n 语法校验所有安装的 .sh 脚本
- 验证 4 个脚本存在且可执行
- 验证 LICENCE.md 许可证文件存在
- shell 脚本包，bash -n 是 R34"实际执行被测包脚本"对纯 shell 包的等价校验

## 已知限制

- cake-autorate 主要面向 OpenWrt 路由器环境
- 运行需要 root 权限（tc qdisc 操作）
- 依赖 fping 进行 RTT 测量
