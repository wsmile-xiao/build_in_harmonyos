# randmac 0.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 cmake_minimum_required 3.12，设备 cmake 4.1.2）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（/data/service/hnp/bin）
- 状态: built（conan-verify G0/G1/G2/G3/G4 + L2/L4/L5 全过，本地验证；
  W0/CI 依赖 strcase/0.1 发布，见"交付前置条件"）

## 交付前置条件（拓扑序，R36）

- 硬依赖 strcase/0.1（github.com/rd235/strcase，VirtualSquare；
  PR #10505 已提审、四件套全绿）。R36 机械门禁：strcase release 上传
  制品仓后，本包 preflight/finish/CI 方可通过。
- 本地验证路径：在 GLM-51 本地 CONAN_HOME 用 GLM-42-strcase-0.1 worktree
  的已合入配方 `conan create`（不带 user/channel，与 requires 精确匹配），
  randmac 全门禁据此通过。
- 接手窗口唯一下一步：确认 strcase/0.1 发布（`conan install --requires=strcase/0.1 --build=never`）→ `$P run randmac 0.2 GLM-42-randmac-0.2 --title-file <f> --body-file <f>`。

## 编译步骤

conan create（ohos-aarch64 profile）：
1. generate(): CMakeToolchain 注入 CMAKE_REQUIRED_INCLUDES（供上游
   check_include_file(strcase.h) 探测）与 CMAKE_C_FLAGS -I（供 randmac.c
   编译），另设 CMAKE_SKIP_INSTALL_RPATH=ON（E077：cmake --install 改写
   RPATH 破坏 .codesign；本包无运行时 RPATH 需求，直接禁用）
2. build(): cmake configure + build
3. test_package: 13 项断言真机执行（见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify 首轮报 strcase/0.1 不在缓存 | 本地验证用 strcase 包带 user/channel 建（@ohpcd/stable），与裸 requires("strcase/0.1") 不匹配 | 本地 create strcase 时不带 --user/--channel，精确匹配 |
| 2 | 消费者测试初版 1 项断言失败（-o QEMU 期望命中 qemu OUI） | 上游 strcase() 为大小写敏感版（strcase_tolower 才折叠大小写），-o QEMU 走 hex 分支报错退出是上游真实行为 | 断言改为负路径：-o QEMU 必须非零退出（更准确刻画 strcase 集成行为） |
| 3 | GLM-42 勘查称 strcase"归档无/平台无/上游 repo 待考" | 实际上游为 rd235 个人账号（非 virtualsquare org），tag 0.1 | 已由 GLM-42 同日适配为 PR #10505（Debian 亦打包 strcase-dev 0.1-3） |

## 源码修改

无补丁、无源码修改（conandata.yml patches 为空）。适配点全部在配方层
（include 路径注入 + RPATH 策略）。

## 依赖版本

- strcase/0.1：header-only（strcase.h 单头文件，inline 函数 + STRCASE 宏），
  package_type=header-library，仅传播 include 目录

## 验证结果

- conan create + conan-verify：PASS（G0/G1/G2/G3/G4，L2/L4/L5）
- 消费者测试（真机）：test_randmac.sh 13 项断言 13/13 通过——
  MAC 格式（默认）、-q qemu OUI、-xU xen OUI 大写、-l 本地管理位、
  -m 组播位、-u 单播位、-e EUI-64（ff:fe 中缀）、-h 帮助退出码、
  -o 十六进制/冒号两种形式、-o qemu/-o xen strcase 分支命中、
  -o QEMU 大小写敏感负路径
- 日志：reports/conan-create.log（含 "checks=13 failures=0"）

## 上游测试清点（R51）

- 上游无任何测试：源码树仅 randmac.c/CMakeLists.txt/man/COPYING/README；
  无 test/ 目录；CMakeLists.txt 无 enable_testing/add_test；构建树无
  CTestTestfile.cmake。N_static = 0。

## 注意事项

- R38：可执行文件交付，commands.json 已建于软件级 archives/r/randmac/commands.json
- 提交前必须剔除 test_package/build/（本地验证产物）与 *.ghfast-bak
- worktree 复用 GLM-42 遗留（~/qzy/GLM-42-randmac-0.2，其 libXext 大小写
  恒定假改动按 §5.1 不碰、不提交）；CONAN_HOME=~/tmp/ch/home-glm42-randmac

## 路径 B 判断（GLM-58，2026-09-19）

判断：不走路径 B，按纯路径 A 交付。依据：①适配手法均为既有知识库条目的组合
应用（E077 安装期 RPATH 策略；CMakeToolchain 注入 include 路径属常规配方操作），
无新的可跨仓库复用错误签名/根因/方案；②消费者断言负路径修正（-o QEMU 大小写
敏感走非零退出）刻画的是上游 strcase API 真实语义，非 OHOS 平台特有问题；③
无查重后的新知识增量，单库配方层适配不构成 B 门槛。
---

**编译结束**: 2026-09-19 02:03
**最终状态**: built
