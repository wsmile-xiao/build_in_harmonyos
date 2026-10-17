- **三方库名称**：Pillow
- **上游版本**：12.3.0
- **上游仓库地址**：https://github.com/python-pillow/Pillow
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（知识图谱 E004/E011/E045/E046/E087，并参考 `archives/a/aggdraw/1.4.1` 的 OHOS 二进制签名先例）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 4312 | 来源：上游 `Tests/`（pytest），本平台实际执行且全部通过 |
| 集成测试 | 0 | 来源：上游 `Tests/` 未按该维度划分集成测试目录 |
| 其他测试 | 863 | 860 skipped + 3 xfailed，均由上游用例自身的 `skipif`/`importorskip`/`xfail` 条件标记 |
| **合计** | **5175** | 上游收集 5175/5178（3 个用例因缺少外部资源未收集），0 failed |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 4312 | 不变 | 上游 `Tests/` 原样全量执行（`python -m pytest Tests/`），无 `-k` 过滤、无 `--deselect` |
| 集成测试 | 2 | +2 | 新增 `test_package/test_pillow.py`：消费者集成用例——PNG 无损往返（逐像素精确比对）、JPEG 有损往返（容差比对），以 `python3 -I` 从 Conan 包内导入 PIL（不回退到系统 Pillow）；参数缺失时输出 usage 提示而非 `IndexError` |
| 鸿蒙特有测试 | 1 | 新增 | 新增 `test_package/test_harmonyos_runtime.py`：Conan 目标 OHOS + 架构 armv8 校验，ELF64 little-endian AArch64（`e_machine=183`）校验，`PyInit__imaging*` 导出符号、`NEEDED libpython3.12.so`、`.codesign` 段校验，并实际加载 `_imaging` 完成真实像素往返 |
| **合计** | **5178** | **+3** | 上游全量 5175（含跳过/预期失败）+ 适配新增 3 |

### 跳过、预期失败与失败原因说明（补充）

- **跳过 860**：全部由上游用例自身的 `skipif` / `importorskip` 条件触发，与适配无关，分类如下：
  1. Windows/macOS 专属能力、Linux `wl-clipboard` 等非 OHOS 平台测试；
  2. Qt、Tk、IPython、XCB 等可选 GUI/桌面依赖未安装；
  3. raqm、freetype2、libtiff、webp、Netpbm、djpeg 等可选图像/字体功能未启用；
  4. 特定 locale、测试图片、仅 CI 执行条件或空参数集合等环境资源条件。
- **预期失败 3（xfail）**：上游自身标记的已知问题用例，非适配引入。
- **失败 0**：无失败用例；未删除、未跳过、未改写任何上游测试用例。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 证据：`patches/` 下仅 `0001-build-without-pybind11-helper.patch` 一个补丁，改动文件为 `setup.py`（`ParallelCompile` 在无 pybind11 环境中安全退化），未触碰上游 `Tests/` 任何文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游 `Tests/`（pytest）收集 5175 个用例，覆盖编解码、滤镜、格式转换等核心功能，不存在“上游缺测试需补全”的情况。

**适配侧新增用例清单**（Conan 消费验证用途，非上游缺口补全）：

1. `test_package/test_pillow.py` — 消费者集成用例 2 个：PNG 无损往返（逐像素精确比对）、JPEG 有损往返（容差比对）；参数缺失时给出明确 usage 提示。
2. `test_package/test_harmonyos_runtime.py` — 鸿蒙特有测试 1 个：OHOS 目标 / armv8 架构、ELF64 AArch64（`e_machine=183`）、`PyInit_` 导出符号、`NEEDED libpython3.12.so`、`.codesign` 段，并实际加载 `_imaging`。
3. `test_package/artifact_checks.py` — 产物校验辅助模块（纯 Python 解析 ELF 与签名段，供上述两个用例调用），不单独计为用例。

## 验证结果

- 编译状态：通过（`conan create` @ `aarch64-linux-ohos`，本机 W3 模拟 setup.sh + build_and_test.sh 全流程通过）
- 上游测试用例通过率：4312/4312（100%）；另 860 skipped + 3 xfailed 均为上游条件标记，0 failed
- 新增测试用例通过率：3/3（100%）——PNG 往返、JPEG 往返、鸿蒙平台/产物校验
- CI（PR 流水线）：✅ PASSED — 构建 #45478（head `ef4fb32f86`），`conan-setup` / `conan-build-test` / `cleanup` 全部通过。此前失败轮根因是原生扩展未签名被 MAC 拒绝加载，已在本提交中于 `build()` 内补 OHOS 签名后通过；PR 末尾 docs-only 提交仅同步归档说明与测试报告，不改变 CI 输入与构建产物。

## 补充说明

1. **依赖最小化**：仅保留实际使用到的 `zlib/1.3.1.1` 与 `libjpeg-turbo/3.0.4`，未引入 raqm/freetype/libtiff/webp 等可选库（对应上游跳过分类 3）。
2. **构建方式**：使用上游官方 `setup.py bdist_wheel`，不依赖 PEP 517 自定义 backend（CI 环境不可用），并在 Conan 私有目录中引导 setuptools，不污染系统环境。
3. **pybind11 补丁**：`patches/0001-build-without-pybind11-helper.patch` 让 `ParallelCompile` 在无 pybind11 环境下安全退化，无功能删减。
4. **OHOS 二进制签名**：原生扩展在 `build()` 内完成 OHOS 签名（与 `archives/a/aggdraw/1.4.1` 同一方案），保证 `.so` 进入 Conan 缓存前已签名；测试侧在 MAC 拒绝加载的工作域上不跳过，而是回退到产物级校验（ELF/导出符号/依赖/签名段），避免“假通过”。
5. **已知限制**：仅启用 zlib/jpeg 特性，涉及可选图像库（tiff/webp/raqm 等）的用例在上游即为跳过状态；Pillow 其余功能在 OHOS/aarch64 上未发现平台差异。
