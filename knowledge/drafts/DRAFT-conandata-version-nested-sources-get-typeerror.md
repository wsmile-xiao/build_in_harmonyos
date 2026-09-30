# DRAFT: conandata.yml 按版本嵌套 sources 导致 get() TypeError——本仓库惯例是扁平结构

- **日期**: 2026-09-29
- **来源**: mdns-reflector 0.0.1 适配（真机 shadow CI r2 轮）
- **平台**: HarmonyOS PC aarch64 / shadow CI（与平台无关，纯 Conan 配方结构问题）

## 现象

`conan create` 在 `source()` 阶段立即失败，错误只有一行 TypeError，且报错的
"keyword" 是**版本号字符串本身**：

```
ERROR: mdns-reflector/0.0.1: Error in source() method, line 55
	get(self, **self.conan_data["sources"], strip_root=True)
TypeError: get() got an unexpected keyword argument '0.0.1'
```

L0/L0j/L0k/L0m 全过（静态门禁不查 conandata 内部结构），失败发生在 conan create
运行期，距门禁全绿仅数秒。

## 根因

Conan 官方文档的 conandata.yml 惯例是**按版本嵌套**：

```yaml
sources:
  "0.0.1":
    url: "..."
    sha256: "..."
```

而本仓库配方（如 ncdu/2.9.2、mbw/2.0.1）通行的写法是
`get(self, **self.conan_data["sources"], strip_root=True)`——它要求 `sources`
**直接就是** `{"url": ..., "sha256": ...}`（扁平结构）。两种惯例混搭时，
`**` 展开把 `"0.0.1"` 这个键变成关键字参数名，直接 TypeError。

## 解法（实测通过）

**首选：扁平化 conandata.yml**（对齐仓库惯例，如 `archives/n/ncdu/2.9.2/conandata.yml`）：

```yaml
sources:
  url: "https://github.com/pbkhrv/mdns-reflector/archive/4b4cd3b.tar.gz"
  sha256: "e4a95915876576888f2f5e4efd51393e591cf7c0999afaae3331be4e8828bc05"
```

配方保持 `get(self, **self.conan_data["sources"], strip_root=True)` 不变。

CI 的 Mirror fallback / Pre-download 环节对扁平结构完全兼容（实测 URL 重写为
gh-proxy 镜像 → 设备无 curl 时降级 conan 内建下载 → conan create 全绿，
L0/L1/L4/L5 pass）。

备选（保持官方嵌套结构时改配方，仓库内少见）：

```python
get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
```

## 与现有条目的区别

- **E276 / E483**：讲的是 `**conan_data["sources"]` 加 `filename=` 参数（归档名
  不带格式后缀的场景），前提是扁平结构本来就对；不覆盖"嵌套导致 TypeError"。
- **E282 / DRAFT-ohos-conandata-patches-silently-unapplied**：讲 patches 的
  base_path / 未应用问题，与 sources 结构无关。

## 复用要点

新写配方第一次 `conan create` 报
`TypeError: get() got an unexpected keyword argument '<版本号>'` 时，直接检查
conandata.yml 是否多套了一层版本嵌套；对照仓库内已过 CI 的配方（ncdu/mbw）
确认扁平结构即可，不需要怀疑 url/sha256 本身。
