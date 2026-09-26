# 自研 configure 要求 CWD=源码根目录，Conan 配方必须就地构建

- **草稿 ID**: DRAFT-magicrescue-1.1.10-custom-configure-source-root-cwd
- **来源**: magicrescue 1.1.10 HarmonyOS PC 适配（自研 configure 要求 CWD=源码根目录，配方改就地构建后 G2 PASS）
- **分类**: build-system / configure / conan
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `Directory config.d not found. Run configure from the source root.`（conan create G2 阶段失败）
- magicrescue 的 configure 是 hand-written 脚本（非 autoconf 生成，release tarball 只有生成的 `configure` + `Makefile.in`，无 `configure.ac`/`Makefile.am`），脚本用 `[ -d config.d ] || ...` 做相对路径检查，只支持在源码根目录就地运行。

## 根因

Conan 2.x Autotools helper 的 `configure()` 在构建目录（build_folder）下执行 configure 脚本；自研 configure 的相对路径检查（`./config.d`、`./config.config`）在构建目录必然失败——文件只在源码树里。这是"自研 configure 假设单目录就地构建"与"Conan 构建/源码目录分离"的语义冲突。

## 最小修复方案

在 `archives/m/magicrescue/1.1.10/conanfile.py` 范围内：

`build()`/`package()` 用 `self.run()` 显式指定 `cwd=self.source_folder` 就地构建（不用 Autotools helper 的默认构建目录执行）：

```python
def build(self):
    apply_conandata_patches(self)
    # magicrescue ships a custom `configure` (not autoconf) that requires
    # the source root as CWD (it checks `./config.d` and `./config.config`),
    # so build in-source from the source folder.
    self.run("./configure --prefix=/", cwd=self.source_folder, env="conanbuild")
    # R9: -j1
    self.run("make -j1", cwd=self.source_folder, env="conanbuild")

def package(self):
    # Makefile install honors $(DESTDIR)$(PREFIX); prefix=/ → package_folder/bin
    self.run(f"make install DESTDIR={self.package_folder}",
             cwd=self.source_folder, env="conanbuild")
```

要点：

- `env="conanbuild"` 注入 Conan 生成的工具链环境（CC/CFLAGS 等）。
- configure 参数保持最少化（`--prefix=/`），避免自研脚本参数白名单问题（与 DRAFT-E2167 的 `update_configure_args` 场景互补）。
- 该库是纯 CLI 工具：`package_type="application"`，产物为 magicrescue/dupemap/inputseek/safecat/textextract 5 个可执行文件 + recipes + perl 工具。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机 · Conan 2.29.1 + clang 15 + `ohos-aarch64` profile | 修复前 G2 FAIL（`Directory config.d not found`）；就地构建修复后 `conan create` G2 PASS；conan-verify G0-G4 + L2/L4/L5 全绿 |
| 鸿蒙专项测试 | 用 OHOS 构建产物运行 magicrescue gzip 提取，`ALL TESTS PASSED`（exit 0） |
| 消费者验证 | `test_package/test.sh` 构造 gzip blob → magicrescue 恢复 → payload 内容校验通过（conan create 内执行） |

## 禁止策略

- 禁止在 build() 里继续用 `autotools.configure()`/Autotools helper 默认路径——构建目录执行必然触发相对路径检查失败。
- 禁止为这个问题补丁修改 configure 的 config.d 相对路径逻辑（R8/P005：补丁须可向上游提交；改配方构建方式即可）。

## 相关

- 相似条目：E392（raw makefile 的 make cwd 陷阱）、DRAFT-E2167（handwritten configure 参数白名单）、E588（in-source configure 覆盖陈旧生成头）、E095（自定义 configure 不读 CXX）
- 引用原则：P005（补丁可向上游提交）