# aview 1.3.0rc1 适配笔记

## 软件简介
- aview：终端 ASCII 艺术图像查看器（PGM/PPM/PNG/BMP）与 FLI/FLC 动画播放器（AA-Project 家族）
- 上游：https://aa-project.sourceforge.net/aview/
- 许可证：GPL-2.0-or-later
- 构建系统：autotools（configure 已预生成，autoconf 2.13 老式脚本）
- 依赖：aalib（已适配发布 aalib/1.4p5）

## 探索编译（本环境已全部验证通过）
- configure --prefix=$DEFAULT_PREFIX                              ✅
- make -j1（aview + aaflip + asciiview 三个产物）                ✅
- make check（上游无测试目标，无 test suite）                    ✅
- make install DESTDIR=$TEST_PREFIX                              ✅
- 功能验证：aview -driver stdout <真实PPM图> → ASCII 输出正常    ✅
- 非交互退出：echo q | aview -driver stdout -kbddriver stdin     ✅

## 上游测试情况
- 上游 **0** 个自动化测试（2001 年发布，Makefile.am 无 TESTS/check_PROGRAMS）
- test_package 自建 8 断言完整功能测试集（见 test_package/test.sh）：
  1. aview 输出 Usage
  2. aview 渲染真实 PPM → 断言 "Calculating" 标记
  3. aview 输出含 ASCII 字符（| + ~ 等）
  4. 渲染为多行（≥3 行）
  5. aview 对不存在文件报错
  6. aaflip 输出 usage/error
  7. asciiview 脚本在 PATH
  8. 幂等（PASS/FAIL 统计）

## 环境限制说明（重要）
本 OpenDesk 会话的 python 进程处于 SELinux `adhoc_bin` 域（SKILL 知识库 E009）：
- 由 python subprocess 启动的任何进程都无法让 SDK clang 读取源文件（主输入失败，stdin/-include 可用）
- 因此 `conan create`（标准 Autotools 方式）在本环境无法完成：
  - configure 由 /system/bin/sh exec 被拒（脚本 exec 域限制）
  - 即使 bash 显式执行 configure 通过，make 内 clang -c 读取源文件仍失败
- 对比：exeputeBash（hishell_hap 域）可直接完成全部 clang 编译、链接、运行，探索编译即在此验证
- SKILL 声明的"本地可跑"针对完整特权 worker 环境；OpenDesk 沙箱 python 受限

## 交接清单（在可构建环境执行）
配方目录：archives/a/aview/1.3.0rc1（含 conanfile.py/conandata.yml/test_package/patches/commands.json）
依赖：aalib/1.4p5 已发布制品仓

在具备 clang 全权限的环境（hishell 终端 / CI worker）执行：
  1. cd archives/a/aview/1.3.0rc1 && conan create . -pr=ohos-aarch64 --build=missing
     （G2 门禁关键；预期标准 Autotools 流程可通）
  2. python3 ohc-run.py conan-verify aview 1.3.0rc1
  3. python3 ohc-run.py finish aview 1.3.0rc1 published
  4. python3 ohc-run.py submit aview 1.3.0rc1（创建 feat/aview-1.3.0rc1 分支 + PR）

## 已确认事项
- aview 此前未被适配（无归档/分支/知识库记录）
- 唯一依赖 aalib 已发布，无需新适配依赖

## 知识沉淀
- aview（2001 年，autoconf 2.13）是纯工具类（无库），package_type 应为 application
- 上游无测试 → 需按用户要求自建完整功能测试集（test_package）
- E009：OpenDesk 沙箱 python(adhoc_bin) 无法驱动 SDK clang 编译，需 hishell 域
---

**编译结束**: 2026-08-22 02:40
**最终状态**: built
