# E597：conandata.yml sources 带 filename 键时配方 get() 再传 filename 关键字冲突

## 错误特征

`conan create` 在 source() 阶段立即失败（G2 FAIL），日志形态固定两行：

```text
ERROR: libsmraw/20240506@ohpcd/stable: Error in source() method, line 82
	get(
TypeError: conan.tools.files.files.get() got multiple values for keyword argument 'filename'
```

失败点在 `get()` 的**参数绑定**，先于任何网络/解压动作——上一行往往还是
`Calling source() in ~/.conan2/p/...`，容易被误读成下载或 conandata 字段名问题。

## 根因

conandata.yml 的 `sources:` 段存在 `filename` 键（url/sha256/filename 三键形态，
用于显式指定归档名、避免 Conan 按镜像 URL 末段误判压缩格式）：

```yaml
sources:
  url: "https://deb.debian.org/debian/pool/main/libs/libsmraw/libsmraw_20240506.orig.tar.gz"
  sha256: "1d928be52646d4e8283e452824c1839b0f844438848efe7888cc2c5613d12d58"
  filename: "libsmraw_20240506.orig.tar.gz"
```

而配方 `source()` 用字典展开的同时**又**显式传了同名关键字：

```python
def source(self):
    get(self, **self.conan_data["sources"],
        filename="libsmraw_20240506.orig.tar.gz", strip_root=True)   # ← TypeError
```

`**conan_data["sources"]` 展开出的 `filename` 与显式 `filename=` 冲突，Python
调用绑定直接抛 `TypeError: get() got multiple values for keyword argument 'filename'`。

## 修复（二选一，保持单一事实来源）

① 推荐：conandata 保留三键，调用点不重复任何键（libfsapfs/20240429 同款先例）：

```python
def source(self):
    get(self, strip_root=True, **self.conan_data["sources"])
```

② conandata 只留 `url`/`sha256`，归档名由配方持有：`get(self, **self.conan_data["sources"], filename="...", strip_root=True)`。

## 设备复现（不联网、不建文件，$TASK_DIR 可直接执行）

```sh
python3 -c "from conan.tools.files import get; d={'url':'u','sha256':'s','filename':'a.tar.gz'}; get(None, **d, filename='b.tar.gz', strip_root=True)"
# → TypeError: get() got multiple values for keyword argument 'filename'
```

（完整脚本：`$TASK_DIR/repro-e597-get-filename-dup.sh`，含修复形态的对照断言。）

## 边界

- 只影响「conandata 带 filename 键 + 调用点显式 filename=」的组合；缺一不触发。
- `libbfio` 等以两键形态书写 conandata 的包不受影响。
- 相关条目：E549（conandata 多 URL 列表破坏 CI mirror fallback，同属 sources 段
  形态敏感，但错误面在 CI 下载器、非 get() 参数绑定）。

## 实测

libsmraw 20240506 首轮采信轮 G2 即此错误（reports/conan-create.log 尾部）；
按 ① 修复后第二轮 G2 进入完整构建（make + make check 全绿），配方无其他改动。
