# draft-mklibs-0.1.46-conandata-patch-strip-default-zero

## 症状

`conan create` 在 `build()` 第一步（`apply_conandata_patches(self)`）失败：

```
mklibs/0.1.46@ohpcd/stable: Apply patch (portability): Use integer division for the VERBOSE log level constant ...
mklibs/0.1.46@ohpcd/stable: .../patches/0001-lib-mklibs-utils-logging.py.patch: source/target file does not exist:
  --- b'a/lib/mklibs/utils/logging.py'
  +++ b'b/lib/mklibs/utils/logging.py'
ERROR: mklibs/0.1.46@ohpcd/stable: Error in build() method, line 155
	apply_conandata_patches(self)
	ConanException: Failed to apply patch: .../0001-lib-mklibs-utils-logging.py.patch
```

给 conandata 加 `strip: 1` 后，报错变成（路径已剥离但仍找不到）：

```
  --- b'lib/mklibs/utils/logging.py'
  +++ b'lib/mklibs/utils/logging.py'
```

此时才是第二个独立问题（源码 tarball 顶层目录未剥离，见下文"易混淆点"）。

## 根因

1. `conan.tools.files.patches.patch()` 的签名默认 `strip=0`，`apply_conandata_patches()` 把 conandata
   entry 中除 `patch_file` 外的字段作为 kwargs 透传给 `patch()`；
2. `refresh-patch --auto`（ohc 框架）生成的补丁使用 `--- a/<path>` / `+++ b/<path>` 前缀；
3. patch_ng 在 `strip=0` 时按原样拼路径（`a/lib/...`），仓库工作目录中不存在该路径 → 报
   `source/target file does not exist`。

## 修复

conandata.yml 每条 patch entry 显式声明：

```yaml
patches:
  - patch_file: "patches/0001-....patch"
    strip: 1
    patch_description: "..."
    patch_type: "portability"
```

仓库既有 125 个 `conandata.yml` 均采用 `strip:` 写法（`grep -rl "strip:" archives/*/*/*/conandata.yml | wc -l`）。

## 易混淆点（同版本另一个坑）

`strip: 1` 解决补丁路径后，仍可能报 `source/target file does not exist: lib/mklibs/utils/logging.py`，
此时根因是 **`source()` 的 `strip_root`**：Debian native 源码包（`mklibs_0.1.46.tar.xz`）顶层带目录
`mklibs-0.1.46/`，conan 解压到 cache `s/` 后源码位于 `s/mklibs-0.1.46/`，而 patch 的 root 是
`conanfile.source_folder`。`init-build` 工具会自动剥离顶层目录，容易让人误判为"无顶层目录"，
从而写出 `strip_root=False`。正确写法是 `get(self, **self.conan_data["sources"], strip_root=True)`。

## 相关条目

- `E282`（conandata 逐条 base_path）
- `E254`（toybox patch dry-run / 新文件补丁）
- `E248`（补丁后 mtime 与 automake 重生成）
