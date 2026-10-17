# DRAFT-pocketfft-release_for_eigen-headeronly-g1-three-declarations — header-only library 配方 G1 三声明齐全

> **Contributor**: pc2-26 | **Status**: DRAFT | **Updated**: 2026-09-16
> **Severity**: medium | **Category**: conan / recipe / header-only
> **Audience**: 适配 header-only（无构建系统）C++ 库并生成 Conan 配方的编写者

## 问题签名与触发条件

问题签名（conan-verify G1 输出）：

```text
G1: FAIL
  ❌ conanfile.py 缺少: build() 方法
  ❌ conanfile.py 缺少: export_sources() 方法
  ❌ conanfile.py 缺少: 补丁应用调用
❌ G1 失败，请先生成完整配方: ohc-run.py conan-init <软件> <版本>
```

触发条件：header-only 库（`package_type = "library"`，如单头文件 FFT 库
pocketfft release_for_eigen），配方按"无编译"直觉省略 build()、export_sources()
与补丁应用调用。conan-verify 的 G1 是**结构检查**，逐项硬性要求三项声明存在，
任一缺失即 FAIL，阻断后续 G0-G5/L2/L4/L5。

## 根因

G1 配方完整性检查（scripts/ohc/conan_verify.py gate1）对 conanfile.py 逐项
grep：`def build(`、`export_sources`、`apply_conandata_patches`，三项均为必填。
header-only 库无 configure/make，省略属直觉行为，但结构检查不区分编译型与
header-only——必须显式声明。

既有 E257（bshoshany-thread-pool）只覆盖了"缺少: build() 方法"单缺场景，
error_signature 未含 export_sources/补丁应用调用；若按 E257 只补 build() 而
省略其余两项，G1 仍 FAIL。E255（资源/数据包）虽提到
"export_sources() + apply_conandata_patches() 仍需声明"，但其场景是
`package_type=unknown` 数据包（settings 仅 os/arch），不覆盖保留
`package_type='library'` 与完整 settings 的 header-only 库配方。

## 修复

在 conanfile.py 中显式声明三项（header-only 无编译阶段，不得伪造编译日志——R34）：

```python
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

def export_sources(self):
    export_conandata_patches(self)

def build(self):
    # 无编译阶段：header-only 库无 configure/make；当前无补丁时仅为结构完整性
    apply_conandata_patches(self)
```

配套项：
- 保留 `settings = "os", "compiler", "build_type", "arch"` 与 `package_type = "library"`
- 声明 `options = {"shared": [True, False]}`（E283：library 类型必须声明 shared option，否则
  conan create 报 "Package type is 'library', but no 'shared' option declared"）
- `package()` 中 copy() 的 dst 必须用 `os.path.join(self.package_folder, "include")` 绝对路径
  （相对 `dst="include"` 会导致 "No files in this package!"，见 boost-te/picosha2 草稿）

## 验证

```bash
python3 scripts/ohc-run.py conan-verify pocketfft release_for_eigen
# 结果: G1 PASS → G2 conan create PASS → G3/G4/L2/L4/L5 全过（RC=0）
```

## 适用边界与反例

- 适用：header-only / 无构建系统 C++ 库（package_type=library），包括单头文件库、纯头文件模板库
- 反例：有真实构建系统的库照常写真实 build()；纯资源/数据包按 E255（package_type=unknown，
  settings 仅 os/arch）处理——两者都仍需要 export_sources + apply_conandata_patches 声明

## 查重差异（相对既有知识）

| 轴 | E257 | E255 | 本草稿 |
|---|---|---|---|
| 错误面 | 仅 build() 单缺 | 数据包 export_sources/补丁声明 | header-only library 三声明全缺/多缺 |
| package_type | header-library（未展开） | unknown（数据包） | library（保留 settings 四项） |
| 新增差异 | — | — | build()+export_sources()+补丁应用调用三声明的完整错误面与最小修复，对 library 类型配方可跨库复用 |
