# codemadness-frontends 0.8 — OpenHarmony 编译记录

## 基本信息
- 软件: codemadness-frontends
- 版本: 0.8
- 构建系统: makefile
- 目标: ohos-aarch64
- 上游: https://codemadness.org/idiotbox.html（源码 https://codemadness.org/releases/frontends/frontends-0.8.tar.gz）
- sha256: b59b264eba2e2927e06b5b035a0f1b68fe743635b37b26e8c3dfad67a03928e0
- 许可: ISC
- 依赖: libressl/3.9.1（libtls）
- 产物: 4 个二进制（youtube-cli / youtube-cgi / youtube-gopher / youtube-feed，无库目标，cpp_info.libs=[]）

## 编译指导
- 纯 Makefile 构建，FRONTENDS_CFLAGS / LIBTLS_LDFLAGS(_STATIC) 均为简单 `=` 赋值，可经 make 命令行覆盖（零补丁）
- 显式传入 Linux 宏 -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700（上游默认 OpenBSD 块）
- LIBTLS 动态链接（去掉上游 -static），lib 路径指向 libressl 包内 lib
- make -j1（HMDFS jobserver FIFO EPERM，E074）
- Makefile 无 install 目标，package() 手工拷贝到 bin/
- OHOS 下二进制需自签名（binary-sign-tool -selfSign），配方内路径存在时自动执行

## 补丁清单
- 无（零补丁）

## 已知限制
- 在线搜索/抓取需网络与 YouTube 可达；test_package 仅覆盖离线路径（usage 与空查询渲染）
- 上游无任何测试套件（见 test_package/MANIFEST.yml 审计）；离线行为由 test_package 真实执行二进制覆盖

## 功能验证
- test_package/test_frontends.sh：youtube-cli 无参 usage + -o 非法选项 usage + youtube-cgi 空查询渲染（</html>）+ youtube-gopher 空环境菜单（7Search）
