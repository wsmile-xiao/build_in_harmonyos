# 上游测试数据要求 root 属主（沙箱不可满足）：`ctest -E` 排除并如实申报

- **草稿 ID**: DRAFT-SCHROOT-1613-ROOT-OWNED-TESTDATA
- **条目文件**: `knowledge/drafts/schroot-1.6.13-root-owned-testdata.kv`
- **来源事件**: schroot 1.6.13 上游测试阶段（2026-10-01）
- **严重程度**: 🟡 medium（处理不当会连累整轮测试的真实验证价值）

## 1. 现象

上游 CTest 套件在构建沙箱内失败，报错指向**属主**而非逻辑错误：

```
Failed  Test #1: sbuild-chroot-config
（上游报错文本指向：配置文件/测试数据 must be owned by root）
```

而同一批测试里其余套件全部通过。

## 2. 根因

上游为**安全语义**显式校验测试数据的属主：schroot 的 `sbuild-chroot-config`
在 `load_data()` 中拒绝非 root 属主的配置文件——这是防止低权限用户劫持 chroot 配置
的**设计**，不是 bug。

构建沙箱以普通用户运行，且本机：

- `/tmp` 只读（须用 `$TMPDIR` / `$HOME/tmp`）；
- HMDFS/FUSE 挂载下 `chmod`/`chown` 被忽略，权限固定 660，**chown 无效**。

⇒ 该套件在结构上**不可能**通过，把它当成失败会误判一个功能正常的包。

## 3. 解决方案

1. **定性**：先证明原因归属"环境不可满足"——读上游测试源码找到显式属主校验，
   并**实测** `chown` 无效（留存输出作为证据）。
2. **排除而非跳过全部**：在配方 `build()` 内以等价方式自调 ctest，`-E` 排除该套件；
   其余套件**必须全部真跑**。

   ```bash
   ctest --output-on-failure -E sbuild-chroot-config   # 工作目录 = 构建目录
   ```

   （上游 `test` 目标内部直接调 ctest 且不接受额外参数，故配方内自调。）

3. **如实申报**（R51 上游测试三步法）：
   - `test_package/MANIFEST.yml`：`upstream_tests[]` 列实跑套件，
     `upstream_tests_excluded[]` 写排除项 + 原因；
   - `notes.md`：同步说明；
   - PR 正文：写清"排除 1 个、实跑 7/7 通过"。

4. 若上游提供官方跳过开关，优先用官方开关。

## 4. 禁止做法

- ❌ 整轮 `make test` 跳过，或让测试无条件返回 0——会把其余套件的真实结果一起丢掉，
  违反 R51（清点 → 实跑 → 如实回填），PR 宣称"测试通过"却无证据（假绿），真人评审必拒。
- ❌ 删改上游测试源码、伪造属主以"跑过"。

## 5. 备选

平台后续若提供特权/真机测试通道，可把被排除套件移到该通道执行并回填结果；
在此之前保留排除声明与证据（属主校验代码位置 + chown 实测失败输出）。

## 6. 验证

```bash
id -u                                          # 非 0 ⇒ 沙箱确为非特权
ctest -N | grep sbuild-chroot-config           # 上游确实注册了该套件
ctest --output-on-failure -E sbuild-chroot-config
# 期望：100% tests passed, 0 tests failed out of 7
```
