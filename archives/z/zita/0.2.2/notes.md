# zita 0.2.2 适配笔记

> 任务软件名 `zita`（任务总纲命名），对应上游 kokkinizita（Fons Adriaensen）zita 家族中
> 版本号 0.2.2 的唯一软件 **zita-rev1 0.2.2**（官方 tarball zita-rev1-0.2.2.tar.bz2，
> 上游最新版，2018-08-25 发布）。构建产物为 JACK 混响器 GUI 程序 `zita-rev1`
> （可执行文件，非库）。

## 编译环境
- 构建系统: makefile（source/Makefile，无 configure 脚本，无上游测试目标）
- 编译日期: 2026-09-16
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 依赖清单（W0 全部已发布至 ohpcd 制品仓，`conan download --only-recipe` 已验证）

| 依赖 | 版本 | 说明 |
|------|------|------|
| clthreads | 2.4.0 | 必需（clxclient/3.9.2 精确约束 2.4.0；2.4.2 与 clxclient 冲突） |
| clxclient | 3.9.2 | 必需（GUI 库，依赖 clthreads/2.4.0、libxft/2.3.8） |
| jack | 1.9.22 | 必需（JACK 音频后端） |
| libpng | 1.6.58 | 必需（cairo 约束 1.6.58；1.6.58.2 与 cairo 冲突） |
| cairo | 1.18.4.1 | 必需（GUI 绘制，约束 freetype/2.14.3、libpng/1.6.58） |
| freetype | 2.14.3 | 必需（cairo/fontconfig 约束 2.14.3；2.14.3.1 与 fontconfig 冲突） |
| libxft | 2.3.8 | 必需（clxclient 精确约束 2.3.8；2.3.9 与 clxclient 冲突） |
| libx11 | 6.4.0 | 必需（cairo X11 后端约束 6.4.0，override 统一；1.8.13 与 libxext/6.4.0 冲突） |
| fontconfig | 2.18.3 | 传递依赖（libxft 链需求 2.18.3，cairo 约束 minor 2.18.Z，override 统一） |

依赖版本冲突要点：
1. clxclient/3.9.2 精确 requires clthreads/2.4.0、libxft/2.3.8 —— 不能用手动指定的 2.4.2/2.3.9
2. cairo/1.18.4.1 的适配层 override libx11/6.4.0 + libxext/6.4.0 —— 依赖图必须统一到 6.4.0
   （libx11/1.8.13 与 libxext/6.4.0 直接冲突）
3. cairo 约束 freetype/2.14.3、libpng/1.6.58（精确 minor）；fontconfig 用 override 统一到 2.18.3
4. 制品仓 cairo/1.18.4.1 存在多个 recipe revision，本项目使用 2026-09-15 的 revision
   （requires 内容含 libx11/6.4.0 override 的适配层版本）

## 编译步骤

纯 Makefile 项目，无 configure。在 `source/` 目录执行：

```bash
make -C source -j1 \
  CXX=/data/service/hnp/bin/clang++ \
  CXXFLAGS="-DCLTHREADS_NO_PTHREAD_CANCEL -O2 -Wall -ffast-math -pthread" \
  CPPFLAGS="<全依赖 include 路径>" \
  LDFLAGS="<全依赖 lib 路径>" \
  zita-rev1

make -C source install \
  CXX=... CXXFLAGS="..." CPPFLAGS="..." LDFLAGS="..." \
  DESTDIR=$staging PREFIX=/usr
```

环境要点：
- freetype2 头文件在 `include/freetype2/` 子目录（Makefile 通过 `pkgconf --cflags freetype2` 获取，
  OHOS 无 pkgconf 命令，探索阶段用 pkg-config wrapper 替代；正式配方直接注入 include 路径）
- X11/Xos.h 等 X11 头在 xorgproto 包的 include 目录（部署路径为 `xorgproto/2025.1/armv8/include`）
- 依赖通过 conan 私有 prefix 注入（R49），不触碰 /usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游为本地优化编写，交叉/可移植构建不安全 | 源码修改移除该行（与 zita-alsa-pcmi 相同模式） |
| 2 | OHOS 无 PATH 上的裸 `install` 命令 | OpenHarmony toybox 提供 /bin/install，但 PATH 不含裸名 | Makefile 引入 `INSTALL ?= /bin/install`，install 目标全部使用 `$(INSTALL)` |
| 3 | clthreads.h 使用 `pthread_cancel` | OHOS libc 未提供 pthread_cancel | clthreads.h 自带 `CLTHREADS_NO_PTHREAD_CANCEL` 守卫宏，编译传 `-DCLTHREADS_NO_PTHREAD_CANCEL` |
| 4 | `X11/Xos.h` not found | X11 公共头在 xorgproto 包（部署结构为 armv8/include 非 Release/armv8/include） | include 路径补 xorgproto |
| 5 | `ft2build.h` not found | freetype2 头在 `include/freetype2/` 子目录 | include 路径补 `-I.../include/freetype2` |
| 6 | init-build 嵌套源码扁平化导致 `../share/*` 失效 | init-build 把 tarball 内 `source/` 子目录内容提到 work 根，install 目标引用 `../share/*`（兄弟目录）失败 | 重建完整目录结构（source/ + share/ + doc/ + AUTHORS/COPYING/README），与 zita-alsa-pcmi 同类处理 |
| 7 | 依赖传递 .pc 文件 prefix 损坏 | full_deploy 部署后的 .pc 仍指向 .conan2 原始路径 | 探索阶段手工修正 prefix；正式配方走 conan cpp_info 依赖链，不依赖 .pc |
| 8 | conan install 依赖版本连环冲突 | clxclient/cairo/fontconfig 相互精确约束 | conanfile 内 requires 精确版本 + libx11/libxext/fontconfig override 统一（详见依赖清单） |

## 源码修改
- `source/Makefile`：移除 `-march=native`；新增 `INSTALL ?= /bin/install`；install 目标命令改用 `$(INSTALL)`
- （补丁由 finish refresh-patch --auto 生成）

## 上游测试
- 上游无测试目标：`make check` → "No rule to make target 'check'"，已如实申报
- 自研 test_package（见 test_package/）：用例级 conan test 进程 rc=0 完整通过，
  内部 4 项确定性检查点：二进制存在 / ELF AArch64 / 版本字面量 / DT_NEEDED 动态依赖链完整

## 验证结果
- 编译：zita-rev1 生成成功，ELF64/AArch64，动态链接 /lib/ld-musl-aarch64.so.1
- 安装：bin/zita-rev1 + share/zita-rev1/*.png（6 个）全部就位
- staging 消费者验证：见 test_package

## 注意事项
- zita-rev1 是 JACK + X11 GUI 程序：无 JACK 服务/无显示环境时完整 GUI 无法运行属预期；
  test_package 以确定性静态断言（ELF 架构/版本字面量/DT_NEEDED 依赖链）为验证口径，
  `-h` 尽力运行仅作诊断信息输出、不进入断言判定、不影响用例 rc
- 包类型：可执行文件（commands.json 需创建，R38）
- conandata.yml sources.url 用官方源
  https://kokkinizita.linuxaudio.org/linuxaudio/downloads/zita-rev1-0.2.2.tar.bz2
  （R39 官方源；init-build 阶段因 urllib SSL 证书验证失败，用 curl 预下载 tarball 到
  ~/tmp/builds/ 跳过下载，TMPDIR 需指向 $HOME/tmp 避免系统临时目录）

---

**编译结束**: 2026-09-16 03:37
**最终状态**: built
