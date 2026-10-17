# debuerreotype

debuerreotype 是 debuerreotype/debuerreotype 项目的可复现、基于 snapshot.debian.org 的
Debian rootfs 构建器（一组自包含 Bash 脚本，主要面向 Docker 镜像制作），基于
reproducible debootstrap 思想，对给定时间点的 Debian 做可审计、可复现的 rootfs 打包。

## 功能概述

- debuerreotype-init：基于 suite + timestamp 创建初始 rootfs（sources.list 指向 snapshot.debian.org）
- debuerreotype-chroot / debuerreotype-apt-get：在 rootfs 内执行命令与 apt 操作
- debuerreotype-minimizing-config / debuerreotype-slimify：面向 Docker 的精简配置与裁剪
- debuerreotype-debian-sources-list / debuerreotype-recalculate-epoch：sources.list 生成与 epoch 重算
- debuerreotype-fixup / debuerreotype-tar：确定性 tar 打包前修正与输出
- debuerreotype-version：打印当前安装版本

## OHOS 适配

- 纯 Bash 脚本应用，无编译产物，走脚本打包路径（build_system: none）
- 运行时依赖：bash、getopt（选项解析）、readlink；真实 rootfs 构建另需 debootstrap、root 特权、Docker、公网（本包不做）
- 安装布局保持上游相对路径语义：`bin/` 下 11 个入口 + 点号 helper（`.constants.sh` 等），包根 `VERSION` 供 `_version()` 读取
- 上游无单元测试套件；官方 CI 全部为需特权与公网的端到端校验（debootstrap + Docker + snapshot.debian.org），不可移植为配方内测试
- 功能验证：`bash -n` 语法自检 + `debuerreotype-version` 实执冒烟（走真实 getopt 解析与 VERSION 读取）

## 依赖关系

- 运行依赖：bash、getopt
- 编译依赖：无

## 参考资料

- 源码：https://github.com/debuerreotype/debuerreotype
- 许可证：MIT
