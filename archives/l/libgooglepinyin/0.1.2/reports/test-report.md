# libgooglepinyin 0.1.2 测试报告

> **项目**: libgooglepinyin
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS PC aarch64（OHOS Clang 15，ohos-aarch64 profile）
> **测试类型**: 手动功能测试（消费者测试）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 1 | 100% |
| 通过 (PASS) | 1 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

> 上游测试：上游 tarball 无任何测试套件（清点证据见 notes.md 与 test_package/MANIFEST.yml），上游可运行测试入口 0/0（不适用）。

---

## 二、测试结论

### 2.1 总体评价

✅ **libgooglepinyin 0.1.2 在 HarmonyOS PC aarch64 上构建成功，解码引擎核心功能经消费者测试实跑验证可用**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | 无 | 🟢 |

### 2.3 可用功能清单

```
✅ 系统词典加载（im_open_decoder 打开打包的 dict_pinyin.dat）
✅ 拼音整句解码（im_search("nihao") 返回 62 个候选）
✅ 候选获取（im_get_candidate 返回真实 UTF-16 候选串）
✅ 解码正确性（前 10 个候选包含 U+4F60 U+597D "你好"，首选"你好"）
✅ 共享库 SONAME（readelf 实测 DT_SONAME = libgooglepinyin.so）
⚠️ 用户词典/联想预测（im_get_predicts 未单独测试，公开 API 与核心解码同源）
⚠️ 词典构建工具 dictbuilder（构建期工具，上游不安装，仅由构建机 pass 生成词典时验证）
```

### 2.4 已知限制

1. 上游无测试套件，本报告覆盖为消费者视角的核心解码链路，未覆盖全部公开 API。
2. 词典由构建机 dictbuilder 在小端环境生成；OHOS aarch64 与主流构建机均为小端，大端目标需另行生成（上游原始行为一致）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_libgooglepinyin | 打开系统词典+用户词典、搜索 "nihao"、断言候选非零、候选串非空、"你好" 在前 10 候选（4 项断言） | ✅ PASS |

实测输出（OHOS aarch64 设备原生运行）：

```
PASS: candidates=62 top=你好 ('nihao'->'nihao' pair present)
exit=0
```

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | - | - |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | - |

---

## 四、关键问题分析

### 问题1: 首轮 W3 的 L5a 门禁失败（已修复）

- **现象**: 打包的 libgooglepinyin.so 缺少 DT_SONAME。
- **根因**: HarmonyOS 平台模块（Android 风格）忽略 CMake VERSION/SOVERSION 属性，不给链接器传 -soname。
- **修复**: 补丁 0003 显式追加 LINK_FLAGS `-Wl,-soname,libgooglepinyin.so`，readelf 复测 SONAME 正确。

### 问题2: 交叉编译下词典生成步骤不可行（配方设计解决）

- **现象**: 上游 data/ 构建步骤需运行目标架构 dictbuilder，交叉编译无法执行。
- **处置**: 配方统一两阶段——构建机 pass 生成词典，目标 pass 安装预置词典（补丁 0004）。

---

**编译结束**：2026-09-17

**最终状态**：built
