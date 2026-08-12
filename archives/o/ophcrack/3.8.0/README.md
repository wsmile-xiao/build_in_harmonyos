# ophcrack — Windows 密码破解工具（OHOS PC 适配）

ophcrack 是一个基于彩虹表（rainbow tables）的 Windows 密码破解工具，支持 LM/NTLM 哈希的暴力破解与查表破解。本目录为 OpenHarmony PC (aarch64) 适配交付物。

## 功能概述

- 基于彩虹表查表的 LM/NTLM 哈希破解
- 支持暴力破解（bruteforce）
- 支持 pwdump/session 格式哈希文件输入
- 支持会话保存与断点续跑
- GUI 前端（本适配已裁剪，仅保留 CLI）

## OHOS 适配要点

- **GUI 裁剪**：GUI 依赖 Qt5Charts（cnb 未就绪），`--disable-gui` 关闭，保留完整 CLI 破解核心
- **构建类型识别**：OHOS `uname -s` 返回 HarmonyOS，config.guess 无法猜测，显式传 `--build/--host=aarch64-unknown-linux-gnu`
- **临时目录权限**：configure 临时目录 `umask 077` 在 OHOS hmfs 上子目录不可写（权限位保留不完整），补丁改 002
- **pthread 取消 API 缺失**：OHOS musl libc 无 `pthread_cancel/pthread_setcancelstate/pthread_setcanceltype`，补丁定义为 no-op
- **Windows 专用头**：`ntdll.h` 无条件 include `windows.h`，补丁加 `#ifdef WIN32` 保护（-MM 依赖解析阶段会解析它）

## 依赖关系

### 编译依赖
- openssl 3.5.6（cnb 制品仓，crypto）
- expat 2.8.2（cnb 制品仓，XML 表/报告解析）

### 运行依赖
- libexpat.so（test 时经 conanrun 环境提供）
- libc.so（系统 libc）

## 构建方式

```bash
CC=clang CXX=clang++ ./configure --disable-gui \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --with-libssl=<openssl prefix> --with-libexpat=<expat prefix>
make -j1
```

产物 `bin/ophcrack` 为已签名 ELF（OHOS 必需，否则 `Operation not permitted`）。

## 测试

- 上游无正式测试套件（src/test 仅内部自测可执行，无断言框架），test_package 补充消费者视角测试：`ophcrack -h` 冒烟验证（1/1，100% 通过）
- conan-verify 门禁 G0-G4 + L2/L4/L5 全部通过

## 参考资料

- 官网：https://ophcrack.sourceforge.io/
- 源码（权威镜像）：https://deb.debian.org/debian/pool/main/o/ophcrack/ophcrack_3.8.0.orig.tar.bz2
- 作者：Objectif Securite
- 许可证：GPL-2.0-with-OpenSSL-exception
