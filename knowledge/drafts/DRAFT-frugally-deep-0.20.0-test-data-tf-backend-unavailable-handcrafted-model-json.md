# E-DRAFT: 推理库测试数据依赖 TF/Keras 后端不可用时的完整恢复路径

- **触发实例**：frugally-deep 0.20.0 适配（2026-09-27，R01/R02，task frugally-deep-0.20.0-r02-pc2-50）
- **错误签名**：`No module named 'keras'` / `No module named 'jax'` / `Could not find a version that
  satisfies the requirement tensorflow`；`Invalid node index`（IntegerLookup 无 TF）；adaptive
  pooling verify 数值 mismatch（Two-Pool Gather vs fdeep adapt_range）
- **类别**：test-data-generation, dl-inference
- **严重度**：2（上游测试数据链整体阻塞，恢复模式固定且已验证 7/7 通过）

## 症状

frugally-deep 0.20.0 上游 7 个 ctest 测试项（test_model_{autoencoder,embedding,exhaustive,
recurrent,sequential,variable}_test + readme_example_main）均依赖 keras_export 生成的模型
`.json`。R01 时数据链整体不可用：

```text
$ pip3 install tensorflow
ERROR: Could not find a version that satisfies the requirement tensorflow (from versions: none)

$ KERAS_BACKEND=numpy python3 keras_export/generate_test_models.py exhaustive out.keras
ModuleNotFoundError: No module named 'jax'   # keras numpy backend 依赖 jax 数学内核

$ KERAS_BACKEND=jax python3 keras_export/generate_test_models.py exhaustive out.keras
ImportError: cannot import name 'AdaptiveAveragePooling1D' from 'keras.layers'
```

## 根因（逐层）

1. **无训练后端**：测试数据链 `generate_test_models.py(.keras) → convert_model.py(.json)` 强制
   依赖 Python 训练后端。OHOS aarch64（musl libc）无 tensorflow 轮子（默认 PyPI 与鸿蒙社区源
   均 `No matching distribution`），JAX/torch 亦缺失，keras numpy backend 又引依赖 jax。
2. **keras 版本面**：keras 3.15.1 的 MultiHeadAttention 在 jax backend 有 value_dim≠key_dim
   reshape 冲突；keras ≤3.12 缺 AdaptiveAveragePooling1D/2D/3D 等层。
3. **IntegerLookup 硬依赖 TF**：keras 3.x 的 IntegerLookup/IndexLookup 在 `__init__`
   `if not tf.available: raise ImportError`，musl OHOS 无 TF 时任何 backend 都无法构造。
4. **adaptive pooling 语义差异**：keras jax backend 的 Two-Pool Gather 在非均匀窗口
   （small=floor, big=ceil，窗口大小在两者间变化）时与 fdeep C++ 的 `adapt_range` 公式
   （`[floor(i*in/out), ceil((i+1)*in/out))`）逐点不一致（实测 AdaptiveMaxPooling2D
   output=318 差 2.7），导致 read_model verify 数值失败。

## 恢复路径（已验证，7/7 全通过，不改变上游测试语义）

1. **jaxlib ohos_aarch64 轮子**：鸿蒙社区源 pypi.cnb.cool 提供 `jaxlib-0.10.2-cp312-cp312-ohos_aarch64.whl`
   （SHA-256 56945e31…，与 simple 页一致）+ `jax-0.10.2-py3-none-any.whl`（724d73c4…）。
   直接 curl 下载到 /dev/shm 后 zipfile 解压到 site-packages 即可（规避共享区 inode 限制与
   pip 临时目录问题）。
2. **keras 3.14.1**：同时具备 Adaptive* 层、GroupQueryAttention(use_gate=True)、
   MultiHeadAttention(value_dim≠key_dim) 且 jax 冒烟全通过。
3. **IntegerLookup 兼容层**：按 keras config 字段语义（output_mode='int'、num_oov_indices==1、
   vocabulary、mask_token）用 keras ops 实现等价层，语义与 fdeep integer_lookup_layer 一致
   （in-vocab → num_oov_indices+idx；OOV → (mask?1:0)；mask → 0），
   `register_keras_serializable` 后注入 `keras.layers.IntegerLookup`。
4. **adaptive pooling 兼容层**：按 fdeep adapt_range 公式直接实现 1d/2d/3d max/average
   adaptive pooling，patch **`keras.src.backend.jax.nn` 子模块**（父模块属性 patch 不生效——
   `backend.nn.adaptive_max_pool is cap.adaptive_max_pool` 为 False 是陷阱）。
5. 上游脚本原样生成 7 个 .keras → convert_model.py 原样转 .json → 7 个测试目标原样加载运行。

## 验证证据（frugally-deep 0.20.0 R02）

```text
$ for t in test_model_{autoencoder,embedding,exhaustive,recurrent,sequential,variable}_test readme_example_main; do ./$t; done
7/7 PASS, 0 FAIL（每个入口 rc=0，doctest "1 passed | 0 failed"）
日志: /storage/Users/currentUser/tmp/builds/fdeep-logs/r02-tests/*.log
```

conan-verify G0-G4 PASS；鸿蒙专项 ohos_special_test PASS；消费者 test_package PASS。

## 七轴查重与关系

- exact/causal/trigger/solution_duplicate 均 false（既有 E321/E322/E470 仅覆盖 header-only 配方；
  astronomy 草稿为外部数据仓库漂移不同因；E285 为音频 Null/loopback 后端替代不同域）
- combination/boundary/test_migration_novelty 均 true
- similar_to：E285（替代验证思路）、E231（测试发现口径）

## 适用边界 / 反例

- 适用：公开 API 可从最小模型触发的推理型 header-only DL 库；上游测试数据需 Python 训练
  后端且 OHOS/musl 无轮子的场景（恢复路径已验证可跨库复用）
- 依赖：鸿蒙社区源存在 jaxlib ohos_aarch64 轮子是路径前置；若无该轮子需降级为手工最小模型
  JSON + 公开 API 验证（见 ohos_special_test.cpp）
- 反例：库仅能加载官方生成器产物、无 API 构造路径（或手工 JSON 解析器不认）时不适用