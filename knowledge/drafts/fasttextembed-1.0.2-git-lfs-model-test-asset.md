# fasttextembed 1.0.2：Git-LFS 托管模型资产 → 获取 LFS 对象实跑 e2e + 合成模型端到端

> 草稿（DRAFT）— 来自 fasttextembed 1.0.2 HarmonyOS PC (aarch64) 第二轮适配的真实日志
> （r01 记录 SKIP 路径，r02 获取 66MB LFS 模型后实跑 e2e 达成 3/3=100%）。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/fasttextembed-1.0.2-git-lfs-model-test-asset.kv`

## 现象

- 上游 `model.fte` 是 66MB 模型权重，由 **Git-LFS** 托管
  （`.gitattributes: model.fte filter=lfs`）；
- GitHub 官方 tag archive（codeload）**只含 133B 的 LFS 指针**文件，
  真实权重需从 `media.githubusercontent.com` 拉取；
- 上游 `tests/test_e2e.c` 依赖该模型做 golden 对拍，模型缺失时按上游设计
  打印 `SKIP e2e` 并 `exit 0`（CTest 会将其计为 Passed，但**不是真实通过**）。

## 正确处置（r01 → r02 两阶段）

### r01：模型不可得时的台账（SKIP 计入分母不计通过）

- `source_declared_total = 3`（test_kernels / test_tokenizer / test_e2e，CMake add_test 注册）；
- 实际执行通过 2（test_kernels、test_tokenizer），test_e2e 因 LFS 模型缺失 SKIP；
- 全量通过率 = 2/3 = 66.7%，实际执行集合 2/2 = 100%；
- 不伪造：禁止用假模型文件填塞、把 SKIP 写为 PASS、或从台账隐去该用例。

### r02：真实获取 LFS 模型并实跑 e2e（达成 3/3 = 100%）

1. **获取**：`curl -sS -L -o model.fte.real https://media.githubusercontent.com/media/cemsina/fasttextembed/v1.0.2/model.fte`
   实测 **4.92s 完成 66561280 字节**；`sha256sum` =
   `a527daa2fe5cf8424f02d8d32e50836b0f1b8e9fcf29f24ae087182c2cbe3411`
   与 LFS 指针 oid **完全一致**（核验通过）。
2. **恢复配置**：把真实模型放入 conan 源码缓存
   `~/.conan2/p/fastt*/s/model.fte`（替换 133B 指针，备份指针为
   `model.fte.lfs-pointer.bak`），移除旧二进制后重建
   `conan create . --build=missing`。
3. **实跑**：build() 内 `cmake.test()` 以真实模型运行 —— r02 日志
   `test_e2e` 耗时 **0.91s**（r01 SKIP 路径仅 0.02s），直接运行输出：
   ```
   doc 0  cos=0.9999996  maxdiff=1.72e-04  meandiff=3.52e-05  (>1e-4: 9/384)
   doc 1  cos=0.9999998  maxdiff=2.10e-04  meandiff=2.10e-05  (>1e-4: 2/384)
   doc 2  cos=0.9999998  maxdiff=1.82e-04  meandiff=2.23e-05  (>1e-4: 5/384)
   doc 3  cos=0.9999997  maxdiff=1.26e-04  meandiff=3.05e-05  (>1e-4: 6/384)
   OK (rc=0)
   ```
   → **上游全量通过率 3/3 = 100%**（test_kernels / test_tokenizer / test_e2e 全部实跑通过）。

### 补充：合成模型端到端（不依赖 LFS 资产）

按上游**公开**二进制契约（`src/fte_format.h`：`FTE1` 魔数、`fte_header` 60B、
`fte_tensor_entry` 104B、张量名/形状/类型）在测试内合成**结构合法**的零权重
`.fte` 模型（LayerNorm 偏置置 0.5 防全零输出退化），真实走通
`fte_init → fte_embed → fte_embed_batch`，断言 384 维、全有限、L2 归一化 ≈ 1。
供鸿蒙专项测试与 test_package 消费者用例（各 1/1，分别计数）使用，不重复充数。

## 关键代码（合成模型要点）

- 张量名与上游 `model_bert.c` 完全一致：`embeddings.word_embeddings.weight`、
  `Attention_{L}_qkv_weight`（384×1152）与 `onnx::MatMul_1536/1549/…` 等
  12×3 个 `fte_layer_matmul_name`（该名单是生成代码，勿手改）；
- 形状：word [30522,384]、tok [2,384]、pos [512,384]、各层 qkv [384,1152]、
  attn_out [384,384]、inter [384,1536]、out [1536,384]（fp16）；bias/LN 偏置
  [384]/[1152]/[1536]（fp32）；
- **offset 必须为文件内绝对偏移**（header 60 + tensor 表 104×N 之后 + 相对偏移）；
- `vocab.tsv`（官方 tarball 自带 403KB）随包 resdirs 分发，消费者/测试经
  `VOCAB_PATH` 定位。

## 验证结果（r02）

| 项目 | 结果 |
|------|------|
| LFS 模型获取 | 4.92s / 66561280B，SHA-256 与指针 oid 一致 |
| test_kernels | PASS（rc=0，"OK"） |
| test_tokenizer | PASS（4 行 golden 对拍，"OK"） |
| test_e2e（真实模型） | PASS（doc0-3 cos≈0.9999997，rc=0） |
| 上游全量通过率 | **3/3 = 100%** |
| 鸿蒙专项 test_ohos_embed（合成模型） | PASS（l2norm=1.000000） |
| test_package 消费者 | PASS（conan create 内 1/1） |

## 适用边界

- 适用于任何用 Git-LFS 托管模型/大数据资产、官方源码 tarball 不含实际文件的库；
- 恢复条件：从 `media.githubusercontent.com/media/<owner>/<repo>/<tag>/<file>`
  拉取并按 LFS 指针 oid 核验 SHA-256 后重跑测试；
- 反例：资产已随 tarball 分发（无 LFS）时不适用；模型文件小且可随包分发时，
  优先随包资源（data/resources）而非合成。