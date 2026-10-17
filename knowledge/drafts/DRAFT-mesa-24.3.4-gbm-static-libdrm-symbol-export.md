# DRAFT-mesa-24.3.4-gbm-static-libdrm-symbol-export

**OpenHarmony 适配**: 静态依赖符号泄漏进共享库动态导出表（`gbm-symbols-check: unknown symbol exported: drm*`）

**分类**: L2 模式经验（linking / symbol-export / static-library / OHOS）
**严重性**: 🟡 中等（阻塞上游 ABI 校验测试，不阻塞链接运行）
**影响软件**: 任何在 OHOS 上以静态形态（.a）消费依赖并链接进共享库（.so）的库；实测 mesa 24.3.4（GBM 使能后 libgbm）

## 问题现象

mesa `-Dgbm=enabled` 构建成功后，上游测试 `gbm-symbols-check` 失败：

```
src/gbm/libgbm.so.1.0.0: unknown symbol exported: drmOpenOnceWithType
src/gbm/libgbm.so.1.0.0: unknown symbol exported: drmPrimeFDToHandle
... (数百个 drm* 符号)
```

上游 `gbm-symbols-check` 按 `src/gbm/gbm-symbols.txt` 白名单校验 libgbm 的动态导出表，只允许 `gbm_*` 符号。

## 根因分析

OHOS ohpcd 制品仓以纯静态形态发布 libdrm（`libdrm/2.4.133` 包内仅 `libdrm.a`，无 `.so`）。mesa 的 `src/gbm/meson.build` 中 `libgbm` 是 `shared_library(...)` 且 `dependencies : [dep_libdrm, ...]`：

- 链接器把静态库 `libdrm.a` 的对象符号（`drm*`）合并进 `libgbm.so` 的动态导出表；
- 上游在 Linux 发行版上链接的是动态 libdrm.so，符号留在 libdrm.so 内，不会泄漏进 libgbm 导出表；
- 因此只有 OHOS 这种"依赖纯静态发布"的形态会触发，属平台/制品形态差异而非源码缺陷。

## 解决方案

在链接静态依赖的共享库目标 link_args 中加入 `-Wl,--exclude-libs,ALL`（mesa 补丁 0008）：

```python
libgbm = shared_library(
  'gbm',
  files_gbm,
  ...
  link_args : [ld_args_gc_sections, '-Wl,--exclude-libs,ALL'],
  dependencies : [dep_libdrm, idep_xmlconfig],
  ...
)
```

效果：libgbm.so 动态导出表恢复为仅 `gbm_*` 白名单符号，`gbm-symbols-check` 通过：

```
1/1 gbm - mesa:gbm-symbols-check OK
```

## 验证

- 修复前：`meson test -C build gbm-symbols-check` → FAIL（unknown symbol exported: drm* 数百条）
- 修复后：`meson test -C build gbm-symbols-check` → OK
- 双口径台账：gbm suite 新增 2 注册项（gbm-abi-check / gbm-symbols-check）均通过；上游测试 43/45（另 2 组为 R10 已记录环境差异）
- GBM 消费者（include gbm.h + `-lgbm` 链接 + 调用 gbm_create_device 等）编译/链接验证通过，未受影响

## 适用边界 / 反例

- **适用**：OHOS 上依赖以纯静态（`.a`）形态发布、且被链接进共享库目标的场景；产品愿意以"共享库公共 ABI 不含依赖库符号"为准绳。
- **反例**：依赖以动态 `.so` 形态发布时，符号不会泄漏，无需该参数（若强行添加也无副作用）。
- **反例**：白名单检查本身要求依赖符号成为公共 ABI（如故意 re-export 场景）时不适用。
- **注意**：`--exclude-libs,ALL` 排除的是静态库符号，不影响目标自身源码编译产出的符号，也不影响运行时内部符号解析（依赖仍静态链接在内）。

## 查重差异（相对既有条目）

- `E104`（libolm version_script.ver 缺失）：同为"符号导出控制"，但触发是 maker 构建缺 version script 文件、方案是创建 version script 白名单；本候选触发是静态依赖符号泄漏、方案是链接期 `--exclude-libs,ALL`，机制与工具不同，仅 solution 部分重叠。
- 无任何正式条目或草稿记录 `--exclude-libs` 静态库符号排除场景。

## 关系

- similar_to: E104 (symbol export control)
- caused_by: ohpcd libdrm 静态发布形态 + mesa GBM 使能
- prerequisite_of: 无（独立修复）
- conflicts_with: 无