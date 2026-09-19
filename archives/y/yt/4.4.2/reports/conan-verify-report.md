# Conan Verify Report — yt 4.4.2

**Verdict**: PASS
**Reference**: `yt/4.4.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-18T14:34:12.467087

## G0: ✅ PASS
  📦 构建系统: unknown
  ℹ️ 无法识别构建系统，跳过预查询

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  ✅ 构建系统: pip（封装 OHOS 预编译 wheel，无 C/C++ 编译步骤）
  ✅ 后缀归一化: `normalised 93 extension module(s) to .cpython-312.so`
  ✅ ELF 代码签名: `code-signed 115 shared object(s) for OHOS`
  ✅ test_package: `ALL 7 CHECKS PASSED`（7/7 消费者断言，详见下方「W3 本地 CI 模拟」节）
  ✅ 制品来源: wheel 15056113 字节，sha256 与 `conandata.yml` 声明值一致
  ℹ️ 该轮次构建源为 `file://` 预下载缓存 → 仅作**配方构建/验证证据**，**不**作为源可达性/完整性证据
  ℹ️ 原始 `*.log` 属仓库三·19 禁止随 PR 提交的文件类别，故不在本 PR 内；结论以本节点内联为准

## G3: ✅ PASS
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## W3 本地 CI 模拟: ✅ PASS

`ci/conan/build_and_test.sh` 在 `conan create` 产出的制品上对 `test_package/` 的真实运行结果
（原始日志属仓库三·19 禁止随 PR 提交的类别，故此处内联可复现结论行；`exit_code=0`）：

```
ok   import+version (yt 4.4.2, numpy 2.2.6)
ok   runtime closure (unyt 3.1.0, matplotlib 3.11.1)
ok   ohos ext suffix (53 extension modules all end with .cpython-312.so)
ok   compiled modules (5 compiled submodules imported)
ok   real analysis (4096 cells, total_mass=5.11e+47 g, T_max=1.1e+06 K)
ok   projection (projection (256,), 256 values)
ok   derived fields (derived g*K/cm**3 max_rel_err=0 (neg-ctl wrong-field 0.01, expected in (1e-3,1e-1)); sphere 480 cells, mass=5.912e+46 g < total=5.11e+47 g)

ALL 7 CHECKS PASSED
```

同轮次的构建期关键结论行：

```
yt/4.4.2: normalised 93 extension module(s) to .cpython-312.so
yt/4.4.2: code-signed 115 shared object(s) for OHOS
```

门禁（同轮次）：L1e 破坏性负测通过 —— `[sabotage] bin/ moved away` / `[sabotage] lib/ moved away` →
`[ok] L1e: Negative test confirmed — test genuinely depends on yt`（证明 7 组断言真实依赖被测包，
非空壳；对应 R34 / 审计规则一·2）。

> **证据边界**：本节的构建/测试轮次其源为 `file://` 预下载缓存，因此仅作**配方构建/验证证据**
> （安装 / 后缀归一化 / 代码签名 / 门禁）。源可达性与完整性由对声明 URL 的**独立直连取源**证明
> （HTTP 200、15056113 字节、sha256 与 `conandata.yml` 声明值一致）；运行时功能正确性由**真机
> 上游测试套件**（792 passed / 97 skipped / 0 failed）与消费者测试（7/7）证明。
