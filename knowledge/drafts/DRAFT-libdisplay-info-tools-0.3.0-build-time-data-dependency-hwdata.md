# DRAFT: 构建期的"纯数据依赖"（hwdata / IANA / tzdata）没有 conan 配方时怎么处理

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libdisplay-info-tools 0.3.0 适配（`tool/gen-search-table.py` 需要 hwdata 的 `pnp.ids`）

## 症状

`meson setup` 直接中断：

```
meson.build:24:10: ERROR: File /usr/share/hwdata/pnp.ids does not exist.
```

上游那段代码长这样（libdisplay-info 0.3.0，`meson.build`）：

```meson
dep_hwdata = dependency('hwdata', required: false, native: true)
if dep_hwdata.found()
	hwdata_dir = dep_hwdata.get_variable(pkgconfig: 'pkgdatadir')
	pnp_ids = files(hwdata_dir / 'pnp.ids')
else
	pnp_ids = files('/usr/share/hwdata/pnp.ids')
endif
```

注意 `native: true`：这是给**构建机**找数据，不是给目标机，所以它既不会随
`requires()` 传播，也绕不开设备上的路径缺失。`pnp.ids` 随后由
`custom_target` 喂给 `gen-search-table.py` 生成 `pnp-id-table.c`。

## 两类常见的错误自救

**(a) 伪造 `hwdata.pc`** —— 造一个最小 pkg-config 文件骗过 `dependency()`。
能跑通，但等于给构建期塞了一份与真实数据脱钩的假元数据：路径、版本都得自己编，
而且每个用到 hwdata 的配方都要各造一份。

**(b) 在 `build()` 里 curl 下载 `pnp.ids`** —— 把原本离线的配方变成联网配方。
镜像不可达时的表现非常有误导性：不是一条"下载失败"，而是

```
curl: (28) timed out after 60001 ms
```

整条 `conan create` 一直等到任务超时（本包第一次设备验证因此跑满 50 分钟）。

## 修复：数据文件随配方携带 + 补丁改写兜底路径

1. 数据文件放进配方目录（`data/pnp.ids`），`export_sources()` 导出：

```python
def export_sources(self):
    export_conandata_patches(self)
    copy(self, "data/pnp.ids", src=self.recipe_folder, dst=self.export_sources_folder)
```

2. 补丁把上游写死的兜底路径改成配方内的相对路径：

```diff
-	pnp_ids = files('/usr/share/hwdata/pnp.ids')
+	pnp_ids = files('data/pnp.ids')
```

`dependency('hwdata')` 依旧 not found，但兜底现在命中随配方携带的文件，全程离线。

3. `source()` 里确认文件确实落在源码树里，并加一条自检——数据文件悄悄丢失时
   应当直接报错，而不是让 `custom_target` 生成一张空表：

```python
pnp_ids_path = os.path.join(self.source_folder, "data", "pnp.ids")
if not os.path.isfile(pnp_ids_path):
    raise ConanException("pnp.ids is missing from the source folder ...")
```

## 一个 Conan 2.30 的坑

`export_sources_folder == source_folder`（Conan 2.30 把导出源码直接铺进源码树），
此时从导出目录往源码树 copy 同一个文件会抛：

```
ConanException: copy() 'src' and 'dst' arguments must have different values
```

老的 Conan 把两者分开放，所以这个写法在老版本上没事、在 2.30 上必炸。
staging 逻辑要先判断目标已存在、再 `os.path.normpath` 比较后决定是否 copy。

## 数据本身的健壮性

hwdata 的 `pnp.ids` 里有**只有 ID 没有厂商名的行**（例如单行的 `MV`）。
上游 `tool/gen-search-table.py` 无条件解包：

```python
[pnpid, name] = line.split(maxsplit=1)
```

于是抛 `ValueError: not enough values to unpack (expected 2, got 1)`，
custom_target 失败、构建中断。这类"数据文件比上游假设的更脏"的问题，
在换一份更新的数据文件时一定会遇到，处理方式要和已有的"非法 ID"分支一致
（跳过 + 告警，而不是崩溃）。

## 判据

```sh
# 设备/容器上直接复现
grep -n "pnp.ids\|hwdata" meson.build
meson setup builddir

# 打包后确认配方已经完全离线
grep -n "get(self" conanfile.py     # 只允许 source() 里的源码下载
ls <recipe>/data/pnp.ids            # 数据文件随配方携带
```
