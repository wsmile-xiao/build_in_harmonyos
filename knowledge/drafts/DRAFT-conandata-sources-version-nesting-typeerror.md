# DRAFT — conandata.yml sources 多写版本嵌套层导致 `get() got an unexpected keyword argument '<版本号>'`

> 通用配方结构条目。来源：radioclk 1.0.pristine r1 真机 shadow CI 失败。

## 使用说明

新写 Conan 配方后，source() 阶段（或 `conan-verify G2` / 真机 conan create）
报如下错误时，直接按本条目检查 `conandata.yml` 的层级结构：

```
ERROR: <库名>/<版本>: Error in source() method, line N
	get(self, **self.conan_data["sources"], strip_root=True)
TypeError: get() got an unexpected keyword argument '<版本号>'
```

报错里的 "unexpected keyword argument" 显示的是**版本号字符串**（如
`'1.0.pristine`）而非参数名——这是嵌套层被 `**` 展开成 kwarg 的指纹特征。

## 适用范围

- 本仓库（build_in_harmonyos）全部 Conan 2.x 配方；上游 ConanCenter 风格
  配方迁移过来时**高发**（CCI 的约定就是版本嵌套，本仓库不是）
- 阶段：source() / conan-verify G2 / 真机 conan create 第一步
- 触发条件：配方用 `get(self, **self.conan_data["sources"], strip_root=True)`
  （本仓库主流写法，先例：aa3d、fathom 等）

## 输入输出定义

输入：配方目录下的 `conandata.yml`

诊断：

```sh
python3 -c "import yaml; print(yaml.safe_load(open('conandata.yml')))"
# 错误结构（多一层版本嵌套，键是版本号字符串）：
# {'sources': {'1.0.pristine': {'url': ..., 'sha256': ...}}}
# 正确结构（url/sha256 直接在 sources 下）：
# {'sources': {'url': ..., 'sha256': ...}}
```

输出：修正后的 conandata.yml（去掉版本嵌套层），`**` 展开后 kwarg 恰为
`url=`/`sha256=`。

## 示例

```yaml
# ❌ 错误（ConanCenter 风格，本仓库配方会炸）
sources:
  "1.0.pristine":
    url: "https://deb.debian.org/debian/pool/main/r/radioclk/radioclk_1.0.pristine.orig.tar.gz"
    sha256: "8C63F60E..."

# ✅ 正确（本仓库约定：单版本包 sources 直接平铺）
sources:
  url: "https://deb.debian.org/debian/pool/main/r/radioclk/radioclk_1.0.pristine.orig.tar.gz"
  sha256: "8C63F60E..."
```

配方侧保持仓库主流写法不变：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
```

若确需多版本共存（少见），改为按版本索引：
`get(self, **self.conan_data["sources"][self.version], strip_root=True)`，
但新库适配一律用平铺结构。

## 验证

- 本机 `python3 -c "import yaml; ..."` 结构检查即可拦截，无需真机。
- radioclk 1.0.pristine r1 失败 → 修复后 r2 起源码下载正常（后续轮次错误
  已转移到编译阶段，证明 source() 通过）。

## 关联条目

- DRAFT-exifprobe-2.0.1-conan2-copy-keep-perm：同型错误
  （`TypeError: <api>() got an unexpected keyword argument`），不同因
  （那是 copy() 的失效参数，这是 conandata 层级错误）——注意区分。
- xmodem 经验（工作流 §13）：conandata.yml 的 CI 预下载路径缺陷是另
  一个独立问题，勿混淆。
