# camellia 2.7.0 适配笔记

## 编译环境
- 构建系统: autotools (2007 年快照; autoconf 2.6x + automake 1.10 + libtool 1.5.24)
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4 (target aarch64-unknown-linux-ohos; libc++)
- 状态: built

## 编译步骤

原生探索(任务私有目录, 依据日志逐条加参数/补丁):

```bash
./configure --build=aarch64-unknown-linux-gnu --prefix=<task>/native/dest CC=clang CXX=clang++
make -j1 && make install
```

Conan 构建: `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
配方在 OHOS 下追加 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
(与 a52dec 0.7.4 先例一致; 2007 版 config.guess 无法识别 HarmonyOS 宿主)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别 aarch64 triple | 内置 config.sub/config.guess 为 2007-04-28 版; 设备 uname 报 HarmonyOS 内核; config.guess 还因临时目录权限失败 | 补丁 0001: config.sub 早期接受 aarch64-*-linux*/ohos*; 配方显式传 --build/--host |
| 2 | configure 退出码 0 但 Makefile/config.h 全部未生成 | config.status 临时目录 umask 077 在 setgid HMDFS 上不可写, 写入全部 Permission denied | 补丁 0002: 两处 umask 077 改 022 (同 a52dec 0002 先例) |
| 3 | 消费者程序在 camAllocateImage 后访问 imageData 段错误 | 2007 代码用 (int) 截断 64 位 malloc 指针做 8/16 字节对齐, aarch64 上产生非法指针 (clang 15 对 cam_utils.c 报 8+8 条 pointer-to-int 告警) | 补丁 0003: 8 处对齐计算改用 uintptr_t 并补 stdint.h; 无平台条件宏 |
| 4 | 补丁后 make 可能用系统 autoconf 重生成 configure | automake 维护者规则按时间戳重生成 | 配方 _pin_autotools_timestamps(): 全依赖链 utime 到同一历史时间戳 |
| 5 | Conan out-of-tree 构建首个文件即报 camellia.h not found | 生成的 src/Makefile 硬编码 -I../inc, 仅树内构建可解析; Conan 构建目录与源码目录分离 | 配方 generate() 经 CPPFLAGS 注入 -I<源码>/inc (同 adplug/libbinio 先例模式), 不改生成文件 |

## 源码修改

- patches/0001-config-sub-aarch64.patch: config.sub 增加 aarch64 triple 早期接受分支
- patches/0002-configure-umask-022.patch: configure 临时目录创建两处 umask 077→022
- patches/0003-src-cam-utils-uintptr-alignment.patch: src/cam_utils.c 8 处指针截断改 uintptr_t; 增加 stdint.h

## 依赖版本

无 Conan 外部依赖 (configure.in 仅 AC_CHECK_LIB(m) 与可选 linux/videodev.h 探测;
OHOS 无 videodev.h 时上游自带的空实现分支生效, 摄像头捕获功能不可用)。

## 验证结果

- 原生: configure/make -j1/make install 全通过; 22 项断言消费者程序 (libCamellia.so 动态加载) SMOKE OK
- 上游测试: 无测试套件 (Makefile.in check-am: all-am 且无 TESTS; demo 依赖 tarball 未附带的 resources/ 固定图像)
- test_package: 24 项断言 C 消费者, CMake 构建链接 libCamellia 后运行

## 注意事项

- 库内的 camError() 出错时直接 exit(0)——进程退出码 0 不代表测试通过; 判定以测试程序自身的断言与最终标记输出为准
- CamRLEImage/CamLabelingResults 等结构体作为栈变量使用前必须清零, 否则 nSize/allocated 垃圾值会绕过库内自动分配路径
- camLabelling 需要目标图为 CAM_DEPTH_16U (CAM_LABEL_PIXEL 为 unsigned short), 传 8U 时静默返回 0
- 发布 tarball 内大量文件为 CRLF; 补丁以字节级 diff 生成并经"应用后逐字节等价"验证
