# libxmi 1.2 适配笔记 (GLM-30, 2026-09-15)

## 任务
- 平台任务号: 13472 (开源鸿蒙PC专项积分赛-依赖, activity_id=6)
- 分支: feat/libxmi-1.2 (基于 upstream/main 6b5087b97a)
- 上游: https://ftp.gnu.org/gnu/libxmi/libxmi-1.2.tar.gz
- sha256: 9d56af6d6c41468ca658eb6c4ba33ff7967a388b606dc503cd68d024e08ca40d
- worktree: ~/qzy/GLM-30-libxmi-1.2
- CONAN_HOME: ~/tmp/ch/home-glm30-libxmi

## 上游概况
GNU libxmi 1.2 (2001): 2D 光栅化库, 将矢量路径(线/多边形/圆弧)转换为像素
spans (X11 Canvas 风格 API: miNewGC/miDrawLines/miFillPolygon/miNewCanvas)。
单静态库 libxmi.la, 标准 automake 布局。

## 语言/构建预检
- lang-preflight: c:19 文件 100% (通过)
- 构建系统: autotools (configure.in + 捆绑 1999 libtool/ltconfig)

## 测试四维账本
- N_static = 0: 上游无测试套件。证据: tarball 顶层无 test*/ 目录与任何
  test*.c 程序; Makefile.am 无 check_PROGRAMS/TESTS 声明。
- N_registered = 0 / N_executed = 0: 无可执行上游测试。
- N_consumer = 1: test_package/test.c 消费者程序通过公开头 xmi.h 走完整
  绘制管线 miNewGC -> miNewPaintedSet -> miDrawLines -> miCopyPaintedSetToCanvas
  -> miDelete*, 以进程退出码断言。
- N_assertion = 3: 三个对象创建非空断言 + 管线全程无崩溃(退出码 0)。

## 主要适配点 (无 patches/ 文件, 全部在配方内)
1. 捆绑 1999 libtool (ltconfig) 不认识 OHOS 三元组, configure 直接失败:
   build() 中 autoreconf -fi 重新生成 configure/ltmain.sh (cliquer 先例);
   build_requirements() 加 tool_requires automake/1.18 + libtool/2.5.4
   (均已在制品仓发布, conan download 验证)。
2. config.guess 无法识别 OHOS: autoreconf 后仍显式传
   --build/--host=aarch64-unknown-linux-ohos (argp-standalone/abiword 先例)。
3. R26 静态默认 (--enable-static --disable-shared)。
4. package() 移除 libxmi.la (libtool 绝对路径)。

## 消费者测试
test_package/test.c: opaque API 下的最大可行断言 = 全管线调用 + 退出码。
说明: miCanvas/miPaintedSet 为不透明类型(xmi.h 仅 typedef), 像素级断言
在公开 API 下不可行; 测试真实调用了光栅化全链路。

## 路径 B 判断
不走 B。理由: 适配点(autoreconf 自举 + 显式三元组)均为仓库既有模式
(cliquer/argp-standalone/abiword-plugin 先例, 检查清单 autotools #1/#3/#4
已有条目), 无新跨仓库知识增量。结论: 纯路径 A。

## 已知限制
- 上游无测试套件, 测试覆盖仅消费者测试一层。
---

**编译结束**: 2026-09-17 03:12
**最终状态**: built


## 安装修复（GLM-43 接手，2026-09-17）

G2 首轮失败于 test_package 链接：Library xmi not found in package。
根因是 package() 的 `autotools.install(args=["prefix=<绝对路径>"])` 与
Conan 注入的 DESTDIR 发生双重拼接（libtool 装到 <包目录><绝对路径>/lib
的畸形嵌套路径，包内 lib/ 为空）。改为 `prefix=`（空）：文件落到
DESTDIR/lib ✓。conan-verify 重跑 G0-G4 全过（2026-09-17 03:0x）。
