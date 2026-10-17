# DRAFT-affiche-gnustep-app-bundle-smoke - GNUstep 应用包应以 bundle 形态验收

> **Source event**: affiche 0.6.0 HarmonyOS PC adaptation
> **Category**: B类难度库 / 知识库拓展

Affiche 不是库，而是 GNUstep 应用。对这类包，`conan create` 的重点不是导出
头文件或可链接库，而是确认安装后的 `share/GNUstep/Affiche.app` bundle 是否完整。

## 适用场景

这条经验适用于以下三类包：

- 上游使用 `gnustep-make`，入口是顶层 `GNUmakefile`
- 产物是 `.app` bundle，而不是传统 C/C++ 静态库或动态库
- 上游没有自动化测试，CI 又没有图形会话，不能可靠启动 GUI

Affiche 的价值在于暴露了 GNUstep app 在 HarmonyOS worker 上的完整闭环：
依赖发布门禁、GNUstep Make strict mode、目标机脚本执行限制、SDK 工具动态库污染、
以及 GUI 应用 test_package 验收方式。

## 关键点

1. `GNUSTEP_MAKEFILES` 只解决构建系统入口，不会自动替代依赖包的 include/lib 路径。
2. `gnustep-make` 2.9.2 strict mode 已废弃 `GNUSTEP_SYSTEM_ROOT`。应用包应显式设置
   `GNUSTEP_SYSTEM_APPS`、`GNUSTEP_SYSTEM_LIBRARY`、`GNUSTEP_SYSTEM_TOOLS` 等 SYSTEM 域路径，
   把 `make install` 结果限制在当前 Conan 包目录。
3. 依赖包的头文件/库路径要显式加入 `CPPFLAGS`、`LDFLAGS`、
   `ADDITIONAL_INCLUDE_DIRS` 和 `ADDITIONAL_LIB_DIRS`。
   构建期避免把依赖库目录加入 `LD_LIBRARY_PATH`，否则 SDK 工具如 `lld` 可能加载到
   依赖包里的不匹配动态库。
4. `test_package` 不要强行 headless 启动 GUI；bundle 目录、可执行文件、`.plist`、
   `bin/` 启动入口、`.desktop`、`.lproj`、`.tiff` 这些真实产物比启动行为更稳定。
5. Conan 的自定义环境脚本名字不能复用 `conanbuild`，否则容易撞上 Conan 自带脚本。
6. OHOS 上由 Python 写出的 shell wrapper 或 GNUstep Make 自带脚本可能无法被 `make`
   直接执行；若上游 makefile 需要这类小工具，可在 recipe 中用目标编译器生成极小
   二进制 wrapper，并通过 `MKDIRS` / `MKINSTALLDIRS` 等 make 变量显式覆盖。

## 依赖门禁处理

PR CI 的 L0/R36 依赖检查以制品仓可见性为准，不能只依赖本机 cache 或 sibling worktree。
Affiche 曾使用本机已验证的 `gnustep-gui/0.32.0`，但 PR worker 检查时该版本尚未在
公开 Conan registry 可见，导致 L0 直接失败。最终改用制品仓已发布且能满足 Affiche
0.6.0 构建的 `gnustep-gui/0.31.1`。

判断原则：

- `conan list "dep/*" -r=ohpcd` 先确认版本是否存在
- `conan list "dep/version:*" -r=ohpcd --format=json` 再确认是否有目标 profile 二进制
- 用干净 `CONAN_HOME`、禁用 `conancenter` 重跑，避免本机 cache 掩盖 PR worker 问题
- 依赖缺版本时不要把依赖适配混入当前库 PR

## 构建环境陷阱

GNUstep app 需要依赖库参与链接，但构建期不要把所有依赖库目录加入 `LD_LIBRARY_PATH`。
PR worker 上曾出现 SDK `lld` 被 `LD_LIBRARY_PATH` 污染后加载到 Conan 包中的
不匹配 `libxml2`，报 `xmlNewNs` / `xmlFree` 符号缺失。正确做法是：

- 编译链接搜索路径放入 `CPPFLAGS`、`LDFLAGS`、`ADDITIONAL_INCLUDE_DIRS`、
  `ADDITIONAL_LIB_DIRS`
- app 运行需要的路径通过 `package_info()` 的 `runenv_info` 暴露
- 避免在 build env 中全局 prepend 依赖库目录到 `LD_LIBRARY_PATH`

## GNUstep Make 脚本替换

OHOS worker 上，GNUstep Make 包里的 shell 脚本可能因为执行策略被拒绝，例如：

- `mkinstalldirs`: make 内部用绝对路径调用时，单纯把 wrapper 目录放进 `PATH` 不生效
- `plmerge` / `pl2link`: app bundle 资源阶段可能需要，但依赖包未必提供可执行工具

Affiche 的处理方式是在 recipe 中用目标 C 编译器生成极小二进制 wrapper，并在 `make`
命令行显式覆盖：

```sh
make -j1 MKDIRS="/path/to/wrapper/mkinstalldirs" MKINSTALLDIRS="/path/to/wrapper/mkinstalldirs"
make install MKDIRS="/path/to/wrapper/mkinstalldirs" MKINSTALLDIRS="/path/to/wrapper/mkinstalldirs"
```

## 建议的 bundle smoke

- `share/GNUstep/Affiche.app` 存在
- `bin/Affiche` 启动入口存在且可执行
- `Affiche.app/Affiche` 可执行文件存在且可执行
- `AfficheInfo.plist` 或 `Info-gnustep.plist` 可找到
- `Affiche.desktop` 可找到
- 至少一个 `Localizable.strings` / `InfoPlist.strings`
- 至少一个 `*.tiff`

## 最小验证组合

```sh
CONAN_HOME=/tmp/clean-conan conan create archives/a/affiche/0.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing

CONAN_HOME=/tmp/clean-conan \
CI_PACKAGES="archives/a/affiche/0.6.0" \
zsh ci/conan/build_and_test.sh
```

期望结果：

- `L0_RESULT=pass`: 依赖版本和目录结构通过
- `L1_RESULT=pass`: `test_package` 执行
- `L2_RESULT=skip`: GUI app 无 `--help` / `--version` 时可接受
- `L4_RESULT=pass`: 无 patch 或 patch 声明一致
- `L5_RESULT=pass`: `bin/` 入口存在

## 关联文件

- `archives/a/affiche/0.6.0/conanfile.py`
- `archives/a/affiche/0.6.0/test_package/conanfile.py`
- `archives/a/affiche/0.6.0/test_package/test_bundle.py`
- `archives/a/affiche/0.6.0/notes.md`
