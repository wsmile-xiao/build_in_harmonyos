# DRAFT-astrometry.net-0.98-kv2 — Conan 依赖 include/lib 接入 raw Makefile 构建

> 对应 KV：`knowledge/drafts/DRAFT-astrometry.net-0.98-conan-dep-include.kv`
> 触发事件：astrometry.net 0.98 HarmonyOS PC 适配（R06–R14）

## 问题（error_signature）

raw Makefile 项目使用系统 pkg-config / include 路径查找依赖，而 Conan 依赖的头文件/库在
`.conan2/p/` 下且 `.pc` 可能损坏（`prefix=/`），导致头文件或链接符号不可见。典型报错：

```text
fatal error: 'xxx.h' file not found
No package 'xxx' found
undefined symbol
```

## 根因（root_cause）

raw Makefile 项目使用系统 pkg-config / include 路径查找依赖，而 Conan 依赖的头文件/库在
`.conan2/p/` 下且 `.pc` 可能损坏（`prefix=/`），导致头文件或链接符号不可见。

## 方案（fix_approach）

在 `conanfile.py` 的 `build()` 中对每个直接依赖执行：

```python
dep = self.dependencies.get('<name>')
if dep and dep.package_folder:
    os.environ["CPPFLAGS"] += f"-I{dep.package_folder}/include "
    os.environ["LDFLAGS"]  += f"-L{dep.package_folder}/lib -l<lib> "
```

注意：

1. 不能依赖 pkg-config（`.pc` 的 `prefix=/` 会产生 `-I//include` 空路径）；
2. 子目录头文件（如 `cairo.h` 在 `include/cairo/`）需额外 `-I{include}/cairo`；
3. 传递依赖链冲突时版本须与需求方一致（如 cairo 需 `libpng/1.6.58`，不能声明 `1.6.39`）。

## 验证（verification）

- 7 个依赖实例验证：gsl、bzip2、cfitsio、zlib、openssl、cairo、libpng
- 编译日志确认 `-I`/`-L` 路径正确传入；G1/G2/G3 PASS；`finish` EXIT=0

## 适用边界（applicable_to）

所有使用 raw Makefile + Conan 且需显式传递依赖 include/lib 的项目。

## 元信息

| 字段 | 值 |
|------|-----|
| id | `DRAFT-astrometry.net-0.98-kv2` |
| trigger_tool | `conan`/`make`/`pkg-config` |
| phase | `build`/`configuration` |
| severity | 2 |
| category | `conan`/`build`/`dependencies`/`packaging` |
| conan_package | cfitsio/4.6.4, gsl/2.8, bzip2/1.0.8, zlib/1.3.1.1, openssl/3.5.6.1, cairo/1.18.4, libpng/1.6.58 |
| platform | OHOS 6.0 arm64（适用于任何 Conan 环境） |
