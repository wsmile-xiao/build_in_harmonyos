# E6417 — Unix compress(.tar.Z, LZW) 源码包解不开：conan get() 报 BadZipFile、init-build 按 gzip 解失败、设备 toybox gzip 无 LZW

## 错误特征

```text
# conan get()/unzip() 处理 xxx.tar.Z
BadZipFile: File is not a zip file

# ohc-run.py init-build <pkg> <ver> --url=.../xxx.tar.Z
  ❌   解压失败: not a gzip file

# 设备（toybox）上 gzip -dc xxx.tar.Z
gzip: not gzip
```

文件头两个字节是 `1f 9d`（compress/LZW 魔数），而不是 gzip 的 `1f 8b`。

## 触发条件

- 构建系统：任意（问题出在 source 阶段，与后续构建系统无关）
- 阶段：`init-build` 解包 / 配方 `source()`
- 典型来源：Aminet `misc/unix/*.tar.Z`、NAIF CSPICE、早期 netlib/BSD 归档

## 根因分析

1. `conan.tools.files.unzip()` 按扩展名识别格式，只认 `tar.gz/tgz/tbz2/tar.bz2/tar/gz/tar.xz/txz`，
   其余全部当 zip 处理，于是 `.tar.Z` 报 `BadZipFile`。签名与 E483 相同，但 E483 是 URL 末段缺扩展名；
   这里扩展名是对的，只是 LZW 格式本身不被支持，传 `filename=` 也救不了。
2. `init-build` 的 `_guess_tar_format()` 对未知扩展名缺省 `tar.gz`，按 gzip 解，报 `not a gzip file`。
3. 鸿蒙设备用户态是 toybox，其 `gzip` 没有 LZW 解码；x86 构建机上的 GNU gzip 能解 `.Z`，
   所以「本地手工解包成功、CI 设备 `source()` 失败」。
4. `source()` 执行时 profile 的 `[buildenv]`（含 `/data/service/hnp/bin`）还没生效，
   `cmake -E tar` 能否找到 cmake 不受配方控制（本 x86 runner 的默认 PATH 里就没有 cmake）。

## 解决方案

### 推荐方案：配方内置纯 Python LZW 解码

```python
def source(self):
    src = self.conan_data["sources"][self.version]
    archive = os.path.join(self.source_folder, "pkg.tar.Z")
    download(self, src["url"], archive, sha256=src["sha256"])   # 支持 CI 预下载的 file://
    with open(archive, "rb") as f:
        tar_bytes = _unlzw(f.read())       # gzip unlzw.c 的约 50 行 Python 移植
    os.remove(archive)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        ...  # 逐成员解出：剥顶层目录，拒绝绝对路径与 ".."
```

要点：9→16 位变宽码；码宽切换和 CLEAR(256) 时跳到当前「8 个码一组」的边界；
`code == free_ent` 的 KwKwK 情况。参考实现见 `archives/p/ppunpack/1.0/conanfile.py`。

### 回退方案

能保证 cmake 可用时（例如 `tool_requires` cmake）用 `cmake -E tar xf xxx.tar.Z`，
CMake 内置的 libarchive 支持 compress。先例：`archives/c/cspice/67.0.0.1`。

### 手工探索阶段（init-build）

先按 `.orig` 约定手工解包，再重跑 `init-build` 走「.orig 已存在」分支：

```bash
mkdir -p ~/tmp/builds/<pkg>-<ver>.orig
zcat ~/tmp/builds/<pkg>-<ver>.tar.gz | tar xf - -C ~/tmp/builds/<pkg>-<ver>.orig --strip-components=1
python3 scripts/ohc-run.py init-build <pkg> <ver> --url=<url>
```

（下载文件会被存成 `.tar.gz` 后缀，但内容仍是 compress 格式；x86 上 GNU `zcat` 可以解。）

### 禁止做法

- ❌ 在 `source()` 里调用 `gzip -dc` / `zcat` / `uncompress`：鸿蒙设备 toybox 不支持，CI 必红。
- ❌ 把 `.tar.Z` 重打包成 `.tar.gz` 放到第三方位置，或给 `get()` 伪造 `filename=...tar.gz`：
  违反 R39 官方源，而且格式并没有变。

## 验证

```bash
head -c 2 xxx.tar.Z | od -An -tx1        # 1f 9d = compress
# 在构建机（GNU gzip 可解 .Z）上把配方里的解码结果与 zcat 对拍
cd archives/p/ppunpack/1.0 && python3 -c "
import subprocess, conanfile
data = open('/path/to/xxx.tar.Z', 'rb').read()
ref = subprocess.run(['zcat', '/path/to/xxx.tar.Z'], capture_output=True).stdout
print(conanfile._unlzw(data) == ref)"
```

ppunpack 1.0 实测：解出的 16384 字节 tar 与 GNU `zcat` 逐字节一致（码宽 9→12 均被覆盖），
`conan create` 在 ohos-aarch64 profile 下通过。

## 关联条目

- 相似：E483（`get()` 因 URL 缺扩展名落入 zip 分支，同签名不同根因）、E271（单文件非归档被当 gzip 解）
- 先例：`archives/c/cspice/67.0.0.1`（`cmake -E tar` 方案）
