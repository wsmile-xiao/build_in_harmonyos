# E323 — OHOS 无媒体后端时 integration 测试排除

## 错误特征

```
ctest: 大量 integration/backend 测试失败（qaudiosink、qcamera、
qmediarecorderbackend 等），失败原因均为无法打开媒体设备/后端不可用。
```

## 触发条件

- 构建系统: cmake + ctest
- 阶段: testing
- 适用: 依赖真实音频/视频设备的 Qt Multimedia 测试套件

## 根因分析

OHOS PC 无音频/视频媒体后端（configure 报 `No backend for low level
audio found`）。integration/backend 测试需要真实媒体设备，无后端环境下
必然失败；这些失败属于平台能力缺失，不是适配缺陷。

## 解决方案

### 推荐方案

1. `test_package/MANIFEST.yml` 声明 `excluded_upstream_tests` 并说明
   排除原因（无媒体后端，需真实设备）；
2. build() 用 ctest 正则只运行可运行的 unit 子集：

```
ctest -R 'tst_qmediametadata|tst_qmediaplayer|module_includes' --output-on-failure
```

### 禁止做法

- ❌ 修改上游测试代码以"通过"（保持上游测试原样，用 MANIFEST 声明排除）
- ❌ 把 integration 失败谎报为通过（通过率统计须如实）

## 验证

```bash
ctest -N | grep -cE "integration|backend"
# 对比 MANIFEST 声明：被排除项数量一致且原因合理
```
