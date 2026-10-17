# qttranslations 6.11.1 适配笔记

## 基本信息

- 归档版本：6.11.1
- 实际上游版本：Qt 6.11.1
- 类型：积分赛主库
- 主库 Issue：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/951
- qtbase 依赖 Issue：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/958
- qttools 依赖 Issue：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/957
- qtbase 依赖 PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/2889
- qttools 依赖 PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/2890
- 依赖拓扑：qtbase 6.11.1 → qttools 6.11.1 → qttranslations 6.11.1
- 当前状态：built
- 完整 Conan create：已通过
- conan-verify：已通过
- 远端 CI：尚未执行
- 制品仓上传：尚未执行

## 编译环境

- 系统：HarmonyOS PC
- 架构：AArch64
- 构建系统：CMake
- 编译器：clang/clang++
- 构建类型：Release
- 构建日期：2026-07-17
- Qt 安装前缀：$HOME/usr/local
- Qt mkspec：harmonyos-clang

## 源码信息

- 源码包：qttranslations-everywhere-src-6.11.1.tar.xz
- 官方地址：https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qttranslations-everywhere-src-6.11.1.tar.xz
- SHA256：37c02c81206594c7bb4edca85ac93e8e55a9836b70c960fde6cb0f8623ec5677
- 上游 TS 文件数量：291
- 构建生成 QM 文件数量：304

## 依赖项

### qtbase 6.11.1

qtbase 提供以下构建依赖：

- Qt6 Core
- Qt6 BuildInternals
- Qt6 CMake 配置
- harmonyos-clang mkspec

qtbase 在 HarmonyOS PC 上需要处理平台识别、SONAME、RUNPATH、ARM AES 和 pthread cancellation 兼容问题。

### qttools 6.11.1

qttools 提供 Qt Linguist 工具链：

- lrelease
- lupdate
- lconvert
- lcheck
- lrelease-pro
- lupdate-pro
- ltext2id

qttranslations 构建 QM 文件需要 lrelease，消费者验证使用 lconvert。

## 构建过程

源码初始化：

```bash
cd ~/build_in_harmonyos
python3 scripts/ohc-run.py init-build qttranslations 6.11.1 \
  --url=https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qttranslations-everywhere-src-6.11.1.tar.xz
```

配置：

```bash
cd ~/tmp/builds/qttranslations-6.11.1.work
mkdir -p build
cd build

$HOME/usr/local/bin/qt-configure-module ..
```

构建全量翻译资源：

```bash
cmake --build . --target updateqm --parallel 2
```

安装：

```bash
cmake --install .
```

## 构建原理

qttranslations 不是需要链接的 C/C++ 库，而是 Qt 翻译资源集合。

顶层配置依赖：

- Qt6 BuildInternals
- Qt6 Core
- Qt6 Linguist

translations/CMakeLists.txt 将 updateqm 定义为默认构建目标，并使用 qt_add_lrelease 调用 lrelease，把 TS 翻译源转换为 QM 二进制翻译文件。

上游包含 291 个 TS 文件。构建过程中额外生成 13 个英语翻译文件，因此最终生成 304 个 QM 文件。

## 遇到的问题

### 构建系统误判

ohc-run.py conan-init 根据初始模板将项目误判为 Autotools，自动生成的配方使用 AutotoolsToolchain。

实际项目使用 CMake 和 Qt BuildInternals。配方已改为 CMakeToolchain 和 CMake，并显式构建 updateqm 目标。

### Qt 依赖未发布

qtbase 和 qttools 已在当前 HarmonyOS PC 的 $HOME/usr/local 中完成编译、安装和功能验证，并已分别提交独立 PR，但尚未完成 Conan 制品发布。

当前配方使用 $HOME/usr/local 作为 CMAKE_PREFIX_PATH，并已在 HarmonyOS PC 真机通过完整 conan create。正式发布和远端 CI 前仍需将依赖切换为已发布的 Conan 包。

### 缺失其他 Qt 仓库源码警告

配置阶段会提示部分 Qt 仓库源码目录不存在。这些目录用于 lupdate 更新 TS 源文件，不影响已有 TS 到 QM 的全量转换。

本次目标是构建并安装现有翻译资源，因此允许这些警告。

### GNU Make FIFO 警告

HMDFS 不支持 GNU Make jobserver 使用的 FIFO，构建时可能出现 Operation not permitted 警告。

目标仍可正常完成。需要通过命令退出状态和实际生成文件确认构建结果。

### CMake HarmonyOS 平台警告

独立 test_package 配置时，CMake 会提示系统平台 HarmonyOS 未内置。

该警告未影响纯 C 测试程序的配置、编译和运行。Qt 依赖本身已通过 qtbase 的 HarmonyOS 平台文件恢复 ELF 平台规则。

## Conan 包设计

Conan 包包含：

- translations/*.qm
- translations/catalogs.json
- sbom/qttranslations-6.11.1.spdx

包不声明 include、lib 或 bin 目录，也不声明 qttranslations 链接库。

消费者通过 QT_TRANSLATIONS_PATH 环境变量定位翻译资源目录。

当前配方使用 package_type application，表示该包主要交付运行时资源，而非链接库。

package() 使用 cmake.install() 执行上游标准安装规则，确保同时打包 304 个 QM、catalogs.json 和 SPDX SBOM。

## 验证结果

### 全量生成

- 上游 TS：291
- 构建 QM：304
- 安装 QM：304
- 失败：0
- catalogs.json：已安装
- SPDX SBOM：已生成并安装

### 安装一致性

以下文件的构建树和安装树 SHA256 完全一致：

- qt_zh_CN.qm：c0e29d32c9540a7e78643b74214e633c56f6ab11f018e516629f2c11b1fb09fc
- qtbase_zh_CN.qm：0481a9b92a6f0578400e960a7d5ee70217a6a450eaf7f98b7d32b8dbd0d58616
- linguist_zh_CN.qm：b1fb2eb48cd2151c772a2dc24e9e8bb9b0374227a91868e36aed41fdfb6bf2b3

### 中文翻译解析

安装版 qtbase_zh_CN.qm 经 lconvert 成功转换为 TS：

- lconvert 返回状态：0
- 消息数量：1785
- 中文翻译内容：正常

验证样例包括：

- 转到
- 否
- 上方向
- 剪切
- 新建
- 红
- 互联网
- 是

### 消费者测试

test_package 验证：

- QT_TRANSLATIONS_PATH 已设置
- catalogs.json 存在且非空
- qt_zh_CN.qm 存在且非空
- qtbase_zh_CN.qm 存在且非空
- linguist_zh_CN.qm 存在且非空
- lconvert 可以解析 qtbase_zh_CN.qm
- 解析结果包含不少于 1000 条消息和有效 translation 元素

完整 Conan 消费者测试结果：

- Python 配方语法：通过
- CMake 配置：通过
- updateqm 全量构建：通过
- Conan 打包：通过
- 测试程序编译：通过
- 翻译资源运行检查：通过
- lconvert QM 解析：通过
- 消费者断言：7/7

## Conan 验证结果

- Conan 版本：2.29.1
- Profile：ohos-armv8
- 系统设置：OHOS 6.0 / armv8
- 编译器：Clang 15 / libc++ / gnu14
- Recipe Revision：8c48e633724940eac3d534aa34806a63
- Package ID：1c21bc3ded24ff47b1a195f6cb801f864247735c
- Package Revision：57e6dd94062be087ed74850771db1ee6
- 完整构建日志 SHA256：5ea015d30d66b4862d004ea0527f2754971ea05f69a9561bac27413e0685ce48
- 完整 conan create：通过
- conan-verify：通过
- G0、G1、G2、G3、G4、L2、L4、L5：全部通过
- Verify Package ID：1c21bc3ded24ff47b1a195f6cb801f864247735c
- Verify 日志 SHA256：2f25f84b0f8a93bc9b65eb71616896e13908ac8c63bb2dff3a37c77f74198142
- Conan 包内 QM：304
- Conan 包内 catalogs.json：存在且 JSON 解析通过
- Conan 包内 SPDX SBOM：存在
- test_package：通过

## 当前限制

- 远端 CI 尚未执行。
- qtbase/6.11.1 和 qttools/6.11.1 尚未发布到 Conan 制品仓。
- 当前配方依赖 $HOME/usr/local 中的已安装 Qt，不具备远端 CI 自包含性。
- 当前状态只能标记为 built，不能标记为 published。

## 后续工作

1. 跟踪 qtbase PR #2889 和 qttools PR #2890 的 CI 与评审。
2. 发布 qtbase/6.11.1 和 qttools/6.11.1 Conan 包。
3. 将 qttranslations requirements 切换为正式 Conan 依赖。
4. 执行远端 CI 验证。
5. 验证制品上传成功后将状态更新为 published。
