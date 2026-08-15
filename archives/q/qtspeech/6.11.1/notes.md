# qtspeech 6.11.1 适配笔记

## 编译环境

- 构建系统：CMake（Qt 6 模块 BuildInternals）
- 编译日期：2026-08-14
- 目标平台：HarmonyOS PC aarch64
- 编译器：clang/clang++ 15.0.4
- 状态：built

## 源码与依赖

- 官方源码：`qtspeech-everywhere-src-6.11.1.tar.xz`
- SHA256：`c035c318012025875a653245701a23d3807e8e46b8bf7987877842219c273f14`
- 必需依赖：`qtbase/6.11.1`、`qtmultimedia/6.11.1`；上游 `Qt6TextToSpeech` 公开链接 `Qt::Multimedia`，其公共头文件也使用 `QAudioFormat`。
- 间接依赖：`qtshadertools/6.11.1`
- 可选 `qtdeclarative` 未引入，因此不构建 QML API 和 QML 测试。

## 构建配置

- `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`
- `QT_BUILD_TESTS=ON`
- `QT_BUILD_TESTS_BY_DEFAULT=OFF`
- `QT_BUILD_EXAMPLES=OFF`
- `FEATURE_speechd=OFF`
- `FEATURE_flite=OFF`

HarmonyOS PC 可直接执行生成的 aarch64 OHOS ELF。Qt 的仓库级 CMake 初始化会在
`CMAKE_CROSSCOMPILING` 为真时强制要求独立 `QT_HOST_PATH`；因此配方通过 early
user-toolchain block 在 `project()` 之前启用 Linux 平台 SONAME 规则并设置同机模式，
而 OHOS clang driver 仍使用 `aarch64-unknown-linux-ohos` 目标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | 配置报 `You need to set QT_HOST_PATH to cross compile Qt` | `CMAKE_SYSTEM_NAME` 与 host 名称不同导致 Qt 判断为交叉构建 | 在 Conan toolchain 的 early block 中设置同机 Linux 平台规则和 `CMAKE_CROSSCOMPILING=FALSE` |
| 2 | 上游测试尝试加载 `xcb` 后端并退出 | qtbase 包仅提供 `offscreen`、`minimal` 等无显示服务插件 | 测试环境设置 `QT_QPA_PLATFORM=offscreen` |
| 3 | HarmonyOS 没有可用的 Speech Dispatcher、Flite 或原生 TTS 服务 | 上游后端依赖平台服务或额外库 | 显式关闭 speechd/flite，保留并验证上游 mock 引擎；不宣称原生语音能力 |
| 4 | Qt 模块和消费者查找配置跨多个 Conan 包 | qtbase、qtmultimedia、qtspeech 各自安装原生 Qt CMake config | 显式设置 `Qt6_DIR`、`Qt6Multimedia_DIR`、`Qt6TextToSpeech_DIR` |

## 源码修改

应用 `patches/0001-src-plugins-tts-mock-CMakeLists.txt.patch`，为 CMake MODULE 类型的 mock 插件显式添加相对 `DT_SONAME`。配方安装阶段同步把 Qt 导出的 `IMPORTED_NO_SONAME_RELEASE` 元数据改为 `IMPORTED_SONAME_RELEASE`，避免下游按绝对路径链接插件。

## 验证结果

探索构建已完成核心库、mock 插件和两个上游测试可执行文件：

```text
tst_qtexttospeech: PASS
tst_qvoice:         PASS
CTest:              2/2 passed, 0 failed
```

消费者测试真实执行以下行为：

- 通过 `QTextToSpeech::availableEngines()` 发现已安装的 `mock` 插件；
- 显式构造 `QTextToSpeech("mock")`；
- 验证 Ready 状态、引擎名、locale 和 voice；
- 验证 rate、pitch、volume 属性往返。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | HarmonyOS PC Qt Speech 配方、上游测试和 OHOS ELF 签名 |
| `conandata.yml` | 官方/镜像源码 URL 与 SHA256 |
| `manifest.yaml` | 构建元数据、依赖与知识沉淀 |
| `pre-analysis.md` | 平台能力和后端预分析 |
| `test_package/` | 独立 CMake 消费者测试及测试清单 |

## 功能边界

该制品提供 Qt TextToSpeech 核心 API 和可测试的 mock 插件。HarmonyOS PC 当前没有
本任务可调用的原生 TTS 服务，因此该适配不提供真实语音输出后端；此限制不会被包装为
完整 TTS 能力，并将在 PR 描述中明确披露。
---

**编译结束**: 2026-08-14 23:16
**最终状态**: built
