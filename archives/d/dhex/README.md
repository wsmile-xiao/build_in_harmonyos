# dhex 0.69 — OpenHarmony 编译记录

## 基本信息
- 软件: dhex
- 版本: 0.69
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 目标: ohos-aarch64
- 依赖: ncurses/6.6
- 上游: https://www.dettus.net/dhex/（只发 tar 包，无 git 仓库）

## 编译指导
- `make -j1`，CC 取自 Conan conf（clang），ncurses 头文件/库路径由配方注入
- ncurses/6.6 仅提供 libncursesw.a，构建时以符号链接满足上游 LIBS=-lncurses
- 上游 `make install` 硬编码 DESTDIR=/usr/local，配方改为手动安装二进制与 man 页

## 补丁清单
- 0001-output-h-initcolors-prototype.patch — output.h 的 initcolors 补全函数原型（与定义一致）

## 已知限制
- 上游 dhex 0.69 无测试套件（手写 Makefile 无 check/test 目标，todo.txt 自认缺测试套件），
  功能验证由 test_package 真实执行 dhex 二进制（-v/-h/-g 非交互断言）完成

## 功能验证
- test_package/test.sh: dhex -v 精确版本断言（0.69）+ dhex -h 帮助断言 + dhex -g 许可证断言
