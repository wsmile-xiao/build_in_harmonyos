# GitHub codeload 归档封装非字节稳定（同一 commit 不同 sha256）

> Draft: DRAFT-DIME-CODELOAD-FRAMING-VARIANCE
> Stem: `dime-0.20111205-codeload-framing-variance` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-DIME-CODELOAD-FRAMING-VARIANCE
- **严重度**: 2
- **类别**: source-download-checksum
- **触发工具**: conan
- **阶段**: source-download

## 错误特征

```
ERROR: dime/0.20111205: Error in source() method, line 70
	get(self, **self.conan_data["sources"][self.version], strip_root=True)
	ConanException: sha256 hash failed for 'edcbe949ae67.tar.gz' file.
 Provided hash: 6d9f7d0c1ba20f5815c585a33589943d6ba969bc53587269b735c64703c9f3a6
 Computed hash: 065a7d74d4e1f15244d3a467f8b92e37908f33d4824a528d468379ea868a9914
```

（URL 与哈希都没写错——同一天 curl 两次下载该 URL 均得到 Provided hash，
conan 的 Python 下载器却拿到 Computed hash。）

## 可复现问题

`https://github.com/coin3d/dime/archive/edcbe949ae67.tar.gz`（302 →
codeload.github.com，按请求即时生成）：

- curl 下载两次 → 两次都是 `6d9f7d0c…`；
- conan（Python requests）同日下载 → `065a7d74…`；
- 两个 tar.gz **解包后 209 个文件逐文件 sha256 完全一致**，差异仅在
  gzip 封装层（压缩参数/后端节点不同）。

因此钉死单一 sha256 的配方呈现**偶发失败**：成败取决于当次请求被
codeload 分到哪个后端。

## 根因分析

codeload 的 tar.gz 不是静态资产而是**动态生成**：同一 git tree（内容确定）
可以对应多种 gzip 字节流。conan 的校验对象是整个 tar.gz 字节流而非
解包内容，所以"内容相同、封装不同"直接判死。GitHub release 资产
（releases/download/...）是静态上传文件，不受此影响。

## 解决方案

**主方案**: multi-framing-sha256-set-in-source

```python
_SOURCE_SHA256 = (
    "6d9f7d0c…",  # curl 直连
    "065a7d74…",  # conan Python 下载器
)

def source(self):
    src = self.conan_data["sources"][self.version]
    archive = "dime-0.20111205-src.tar.gz"
    download(self, src["url"], archive)          # 不带在途校验
    computed = hashlib.sha256(open(archive, "rb").read()).hexdigest()
    if computed not in _SOURCE_SHA256:
        raise ConanException(...)                # 报错里写明核实与扩展方法
    unzip(self, archive, strip_root=True)
    os.remove(archive)
    apply_conandata_patches(self)
```

要点：

1. **校验永不跳过**——接受的是同一棵树的多种已知封装，不是放松校验；
   禁止 `get(..., sha256=None)` 一绕了之。
2. conandata 仍保留主变体 `sha256:`（满足 L0b 门禁与 CI 源码身份对比）。
3. 出现第三种封装时，先解包与官方 orig tarball 逐文件 sha256 对比，
   确认仅封装差异后才能追加进集合。

## 关联提示

- 镜像链路（gh-proxy 等）转发的是各自缓存的封装，同样可能出现
  "本地过的哈希 CI 不过"——多哈希集合对镜像场景同样有效。
- CI 的 conandata 源码身份对比逻辑按"文件名 + sha256 集合"比对，
  recipe 内的 `_SOURCE_SHA256` 集合不影响该对比（conandata 未变）。
