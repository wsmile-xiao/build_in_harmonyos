# 上游测试目标本身不可用：裸 `-C` 与后续参数粘连，`bigcheck` 在 pristine 源码上就失败

> Draft: `DRAFT-REFLEX-20241231-BIGCHECK-BARE-C-COMPRESSION-OPTION`
> Stem: `reflex-20241231-bigcheck-bare-c-compression-option` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-BIGCHECK-BARE-C-COMPRESSION-OPTION
- **严重度**: 3
- **类别**: upstream-defect|test-harness
- **触发工具**: make|reflex
- **阶段**: testing

## 错误特征

`make bigcheck` 在**未打任何补丁的 pristine 源码**上就失败，失败点固定在第一项：

```
$ make bigcheck
./flex: unknown -C option '/'
make: *** [Makefile:...: bigcheck] Error 2
```

`bigcheck` 的实现是把同一自举断言在 7 种表压缩模式下各跑一遍：

```make
bigcheck:
	for m in -C -Ce -Cm -f -Cfea -CFer -l; do \
	    $(MAKE) COMPRESSION=$$m check || exit 1; \
	done
```

## 根因

本版选项解析器把**裸 `-C`** 当作"需要后缀"的开关，并把紧随其后的**独立参数**（`-Ce`）
吞成它的后缀 —— 于是报 `unknown -C option '/'`（连字符后的字符被当作后缀字符）。

这是**平台无关**的选项解析缺陷：与 aarch64 / OHOS / toolchain 均无关，任何平台上
`bigcheck` 都跑不到第二项。

判据：**在 pristine 源码上复现**（不打补丁、不改配置），若同样失败且错误文本落在参数解析，
即可判定为上游自带缺陷，而不是本包移植引入。

## 影响范围

- reflex 20241231（及同血统 flex 2.5.4 系）的 `bigcheck` 目标。
- 更一般地：**上游测试目标本身不可用时**，若"照抄上游 target"就会把上游缺陷记成
  自己包的构建失败，进而可能误加补丁去改上游测试驱动。

## 推荐方案

**方法**: `enumerate-available-test-modes-and-document-the-exclusion`

1. **先判归属**：在 pristine 源码上跑同一目标；若同样失败、且失败点是选项解析/参数粘连
   这类平台无关错误 → 判为上游缺陷。
2. **不要改上游的测试驱动**：改为在 recipe 的 `build()` 里显式驱动**可用的那几种模式**：

   ```bash
   for m in -Ce -Cm -f -Cfea -CFer -l; do
       rm -f scan.c          # 必须删掉中间产物，否则自举重生成不会真的发生
       make COMPRESSION=$m check || exit 1
   done
   ```

   本包因此把"默认模式 1 次"提升到 7 次实际执行（默认 + 6 种压缩模式）。
3. **逐字记录排除**：在 `test_package/MANIFEST.yml` 与 `notes.md` 里写明**被排除项与理由**
   （裸 `-C`）以及替代覆盖率，让检视者看到"少了一项"是显式决策而非疏漏。

## 验证命令

```bash
# 在 pristine 源码上确认上游即失败（判归属）
make bigcheck                      # 期望: ./flex: unknown -C option '/' , 非 0 退出

# 驱动可用的 6 种模式（每种都先删 scan.c 保证真重生成）
for m in -Ce -Cm -f -Cfea -CFer -l; do
    rm -f scan.c && make COMPRESSION=$m check || { echo "FAIL mode=$m"; exit 1; }
done
```

## 取证记录

- 包: reflex 20241231（`archives/r/reflex/20241231`）
- 逐字证据: `test_package/MANIFEST.yml`（`upstream_test_count_method` / `upstream_test_audit`）、
  `notes.md`（问题 #5）、`reports/w3-local-ci.log` ——
  `Check successful, using COMPRESSION=""` 与 `"-Ce" / "-Cm" / "-f" / "-Cfea" / "-CFer" / "-l"`
  共 7 次，证明 7 次自举比对全部真实执行
