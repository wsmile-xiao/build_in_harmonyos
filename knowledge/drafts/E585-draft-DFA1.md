# E585 — conan MesonToolchain 将 libexecdir 映射为 bin：meson 安装目录断言需按实际布局

## 错误特征

test_package 按上游约定的 `libexec/<name>` 路径断言打包产物时，报 `missing packaged file`。例如 turnstile 上游将 dinit backend 安装到 `libexecdir/turnstile/dinit`，但 conan 包内实际路径为 `bin/turnstile/dinit`。

```
AssertionError: missing packaged file: <package>/libexec/turnstile/dinit
```

## 触发条件

- 构建系统: meson，且上游向 `libexecdir` 安装数据/脚本
- 阶段: installation / test_package（消费者路径断言）
- 平台: OHOS/aarch64，conan 2（MesonToolchain）

## 根因分析

conan 2 的 MesonToolchain 生成的 `conan_meson_native.ini` 将 `libexecdir` 固定为 `'bin'`（与 CMakeToolchain 默认 `CMAKE_INSTALL_LIBEXECDIR=bin` 同族行为，见 DRAFT-rdma-core）。上游 meson.build 中 `install_dir: join_paths(get_option('libexecdir'), 'turnstile')` 展开后实际落盘到 `bin/turnstile/`，而非 GNU 惯例的 `libexec/turnstile/`。test_package 若按上游源码路径断言（`libexec/...`）就会报 missing，且 meson 不报错（静默映射），问题只在消费者断言/运行时路径解析处暴露。

## 解决方案

### 推荐方案

test_package 按 conan 安装后的**实际布局**断言，上游路径仅作参考并注释映射原因：

```python
# conan MesonToolchain maps libexecdir to bin/; upstream installs the
# dinit backend under libexecdir/turnstile → bin/turnstile/dinit here.
backend = os.path.join(pkg, "bin", "turnstile", "dinit")
```

如确有需要恢复 GNU libexec 布局，可在 `generate()` 显式覆盖：
`tc.project_options["libexecdir"] = "libexec"`（需确认上游依赖该路径的运行时查找逻辑同步）。

### 禁止做法

- ❌ 不要照抄上游源码路径断言打包产物（meson 静默映射 libexecdir→bin，不报错）
- ❌ 不要为了凑断言修改上游 meson.build 的 install_dir（引入无谓补丁面）

## 验证

```bash
# conan create 后检查包内实际布局
find <package_folder> -name "dinit" -o -name "turnstiled*" | sort
# 实测（turnstile 0.1.11）：bin/turnstile/dinit 存在，libexec/turnstile/dinit 不存在
# 修正断言为 bin/turnstile/dinit 后 conan-verify G2 PASS
```

实证：turnstile 0.1.11（2026-09-21）：test_package 首次按 libexec/turnstile/dinit 断言 → conan-verify G2 FAIL（missing packaged file）；按实际路径 bin/turnstile/dinit 修正后 G2 PASS（G0-G4 + L2/L4/L5 全绿）。

## 适用边界

- 适用：meson 构建、向 libexecdir 安装数据/脚本、OHOS/aarch64 conan 环境
- 不适用：纯 CMake 项目（CMakeToolchain 的 CMAKE_INSTALL_LIBEXECDIR 问题见 DRAFT-rdma-core，修复方式为显式覆盖变量）；不在 libexecdir 安装内容的 meson 项目

## 关联条目

- similar_to: DRAFT-rdma-core-61.0-conan-libexecdir-bin-collision（同族根因：conan 工具链将 libexecdir 映射为 bin；差异：CMake 变体显式覆盖 CMAKE_INSTALL_LIBEXECDIR 恢复 libexec 并伴随安装冲突报错，Meson 变体为静默映射、仅在 test_package 断言暴露，修复以按实际布局断言为主）
- 落地实现: archives/t/turnstile/0.1.11/test_package/test_turnstile.py（bin/turnstile/dinit 断言 + libexecdir→bin 映射注释）
