# qttranslations 6.11.1 真机测试报告

## 测试对象

- 软件：qttranslations
- 归档版本：6.11.1
- 上游版本：Qt 6.11.1
- 平台：HarmonyOS PC
- 架构：AArch64
- 日期：2026-07-17

## 测试结论

qttranslations 6.11.1 已在 HarmonyOS PC 真机完成源码配置、全量 QM 生成、安装、一致性检查、中文翻译解析和消费者资源检查。

当前真机构建、完整 Conan create 和 conan-verify 结论均为通过，归档状态为 built。

远端 CI 和制品上传尚未执行，因此不能标记为 published。

## 构建结果

| 项目 | 结果 |
|---|---:|
| 上游 TS 文件 | 291 |
| 生成 QM 文件 | 304 |
| 安装 QM 文件 | 304 |
| QM 生成失败 | 0 |
| catalogs.json | 已安装 |
| SPDX SBOM | 已安装 |
| 安装流水线状态 | 0 0 |

## 关键资源

| 文件 | 大小 | 结果 |
|---|---:|---|
| catalogs.json | 797 字节 | 通过 |
| qt_zh_CN.qm | 99 字节 | 通过 |
| qtbase_zh_CN.qm | 147222 字节 | 通过 |
| linguist_zh_CN.qm | 34840 字节 | 通过 |
| assistant_zh_CN.qm | 约 20 KiB | 通过 |
| designer_zh_CN.qm | 约 110 KiB | 通过 |

## 一致性检查

| 文件 | SHA256 | 构建树与安装树 |
|---|---|---|
| qt_zh_CN.qm | c0e29d32c9540a7e78643b74214e633c56f6ab11f018e516629f2c11b1fb09fc | 一致 |
| qtbase_zh_CN.qm | 0481a9b92a6f0578400e960a7d5ee70217a6a450eaf7f98b7d32b8dbd0d58616 | 一致 |
| linguist_zh_CN.qm | b1fb2eb48cd2151c772a2dc24e9e8bb9b0374227a91868e36aed41fdfb6bf2b3 | 一致 |

## QM 解析

验证命令使用安装版 lconvert 将安装版 qtbase_zh_CN.qm 转换为 TS。

| 项目 | 结果 |
|---|---|
| lconvert 返回状态 | 0 |
| 转换文件 | 已生成 |
| message 数量 | 1785 |
| 中文内容 | 正常 |
| translation 元素 | 存在 |

## 消费者测试

| 断言 | 结果 |
|---|---|
| QT_TRANSLATIONS_PATH 已设置 | 通过 |
| catalogs.json 存在且非空 | 通过 |
| qt_zh_CN.qm 存在且非空 | 通过 |
| qtbase_zh_CN.qm 存在且非空 | 通过 |
| linguist_zh_CN.qm 存在且非空 | 通过 |
| lconvert 成功解析 QM | 通过 |
| 解析消息不少于 1000 且包含有效翻译 | 通过 |

消费者测试结果：7/7。

## Conan Create

| 项目 | 结果 |
|---|---|
| Conan 版本 | 2.29.1 |
| Profile | ohos-armv8 |
| OS | OHOS 6.0 |
| 架构 | armv8 |
| 编译器 | Clang 15 |
| C++ 标准库 | libc++ |
| C++ 标准 | gnu14 |
| Recipe Revision | 8c48e633724940eac3d534aa34806a63 |
| Package ID | 1c21bc3ded24ff47b1a195f6cb801f864247735c |
| Package Revision | 57e6dd94062be087ed74850771db1ee6 |
| QM 文件 | 304 |
| catalogs.json | 已打包并解析通过 |
| SPDX SBOM | 已打包 |
| test_package | 通过 |
| 完整日志 SHA256 | 5ea015d30d66b4862d004ea0527f2754971ea05f69a9561bac27413e0685ce48 |

## Conan Verify

| Gate | 结果 |
|---|---|
| G0 预构建风险评估 | 通过，命中 E092 提示但未阻断构建 |
| G1 配方完整性 | 通过 |
| G2 干净 conan create | 通过 |
| G3 系统同名库隔离 | 通过 |
| G4 产物完整性 | 通过，资源包无 bin/lib |
| L2 平台冒烟测试 | 通过，无 cache 路径而跳过执行 |
| L4 静态安全扫描 | 通过，无 cache 路径而跳过执行 |
| L5 产物基线对比 | 通过，无 cache 路径而跳过执行 |
| Package ID | 1c21bc3ded24ff47b1a195f6cb801f864247735c |
| Verify 日志 SHA256 | 2f25f84b0f8a93bc9b65eb71616896e13908ac8c63bb2dff3a37c77f74198142 |

## 已知限制

- 本报告记录的是 HarmonyOS PC 真机构建、完整 conan create、conan-verify 与消费者测试。
- 远端 CI 尚未执行。
- qtbase 和 qttools 尚未发布为正式 Conan 依赖。
- 当前配方暂时使用 $HOME/usr/local 中已安装的 Qt。
- 远端 CI 自包含性仍需在依赖包发布后验证。
