# klystrack 0.20171212 适配笔记

## 编译环境
- 构建系统: Makefile（非 configure autotools）
- 编译日期: 2026-08-01
- 上游版本号来源: raspbian 打包用日期戳（0.20171212 = 2017-12-12 上游 commit 快照），上游 release tag 是 1.7.6

## 依赖
- SDL2/2.30.10（制品仓已发布）
- SDL2_image/2.8.0 未发布到制品仓（不声明依赖，上游 Linux 构建不强制）

## 构建
```bash
# Conan 制品仓构建（OHOS arm64）
conan create . --build=missing

# 手动构建参考
make CFG=release CC=clang CFLAGS+="-I<SDL2_inc> -I<SDL2_image_inc>" LDFLAGS+="-L<SDL2_lib> -L<SDL2_image_lib>" PREFIX=/staging
make install CFG=release PREFIX=/staging
```

## 上游测试
# 上游无自动化测试套件
# klystrack 是 chiptune tracker 纯音频应用，C 项目无 test/ 目录无 Makefile test target
# test_package 验证 bin/klystrack --version 输出非空 + --help 退出码 0
# 上游测试核对（2026-08-09，CI #16863 checkout-pr 网络问题后复核）：
#   源码树无 tests/ 无 test/ 目录，Makefile 无 test/check target（仅 install bundle 用
#   test -d），确认上游无自动化测试；适配后 test_package 消费测试为唯一验证点

## 适配要点
- Makefile 构建（非 configure），用 CPPFLAGS/LDFLAGS 注入 SDL2/SDL2_image 头路径+库路径
- PREFIX 用于 install 目标（RES_PATH=$(PREFIX)/lib/klystrack）
- CFG=release 产出 bin.release/klystrack
- 上游 LICENSE: MIT（Tero Lindeman kometbomb + Ilija Melentijevic 图形）
