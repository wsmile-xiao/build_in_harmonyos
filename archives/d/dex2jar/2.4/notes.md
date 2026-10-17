# dex2jar 2.4 适配笔记

## 编译环境
- 构建系统: custom（Gradle/JVM）
- 编译日期: 2026-08-02
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: failed（未适配）

## 编译步骤

```bash
# 下载源码
wget https://github.com/pxb1988/dex2jar/archive/refs/tags/v2.4.tar.gz

# 解压并进入
tar xzf v2.4.tar.gz && cd dex2jar-2.4

# Gradle 构建（OHOS CI worker 无 JDK，无法执行）
gradle clean distZip
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_ensure_java()` 找不到可用 JDK | OHOS CI worker 无 JDK（install-jdk.sh 不在 CI 范围内） | 采用 prefixsuffix 失败记录模式，如实标记 status: failed |
| 2 | test_package 无可执行二进制 | 无 JDK 无法运行 Gradle/JVM 构建 | 校验失败归档内容（manifest + notes）真实性 |

## 验证结果

```bash
# OHOS 上无编译产物，验证失败归档内容
$ python3 test_failed_archive.py <package_folder>
PASS: dex2jar failed adaptation record is complete
```

## 注意事项
- dex2jar 是 JVM 工具（Gradle 构建），OHOS CI worker 无 JDK，无法编译
- 失败归档包含 status: failed、failure_reason（JVM/Gradle/JDK 缺失）与 OHOS 说明
- 待 CI worker 安装 JDK（bishengjdk 17）后可启用真实 Gradle 构建

---

**编译结束**: 2026-08-02
**最终状态**: failed
