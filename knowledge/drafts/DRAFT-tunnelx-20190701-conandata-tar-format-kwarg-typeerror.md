# DRAFT-tunnelx-20190701-conandata-tar-format-kwarg-typeerror：`conandata.yml` 的 `tar_format` 被直接 `**` 展开传给 `conan get()`，`source()` 报 `TypeError`

> Contributor: 1748 | Status: Draft | Updated: 2026-10-04
> Source: tunnelx 20190701 适配（Java / HarmonyOS PC，PR 待提）
> 对应：`knowledge/drafts/DRAFT-tunnelx-20190701-conandata-tar-format-kwarg-typeerror.kv`

## 现象

按归档规范生成的 `conandata.yml`（`sources.<version>` 下含 `url` / `sha256` /
`tar_format`），配合同样"自然"的 `source()` 写法，`conan create` 在 **source()
阶段**即失败：

```console
======== Installing packages ========
tunnelx/20190701: Calling source() in /…/.conan2/p/tunne…/s
ERROR: tunnelx/20190701: Error in source() method, line 94
	get(self, **self.conan_data["sources"]["20190701"], strip_root=True)
	TypeError: get() got an unexpected keyword argument 'tar_format'
```

注意错误形态：不是下载失败、不是解压失败，而是 **Python 参数绑定失败**——
`get()` 还没开始工作就抛异常了。

## 根因

两个"各自都对"的约定不一致：

| 约定 | 内容 | 来源 |
|------|------|------|
| 归档规范 `conandata.yml` | `sources.<ver>` 声明 `url` / `sha256` / `tar_format` | 归档 spec / `templates/conandata.yml.tmpl` |
| `conan.tools.files.get()` 签名 | `url` / `sha256` / `destination` / `strip_root` / `verify` / `filename` | Conan 2.x API |

`get(self, **self.conan_data["sources"][ver], strip_root=True)` 会把
`tar_format` 也当作关键字参数传进去，Python 在函数调用绑定阶段就抛
`TypeError`。

需要特别注意的是：`tar_format` **既不能当参数传，也不能指望 get() 读它**。
后者正是 E483 记录的方向——`get()` 不读取 `conandata.yml` 的 `tar_format`
来推断压缩格式（E483 的失败形态是 `BadZipFile`）。本条是同一事实的另一个
表现面（`TypeError`），失败阶段与签名都不同。

## 影响范围

任何用该模板生成 `conandata.yml`、且 `source()` 采用 `**` 展开写法的 Conan
配方——也就是**首次适配的新包最常见**。仓内已有多个配方显式规避：

```console
$ grep -rn "tar_format in conandata.yml" archives --include=conanfile.py | head
archives/a/accountsservice/26.27.3/conanfile.py:76:        # tar_format in conandata.yml is only for validation; get() does not
archives/m/motif/2.3.8/conanfile.py:98:        source_data.pop("tar_format", None)
archives/d/dbus/1.14.10/conanfile.py:49:        # 显式传 url/sha256（conandata.yml 中的 tar_format 仅供校验，
```

说明这是**高频、可复现**的踩坑点，而非个案。

## 推荐方案（优先级 1）

`source()` 内复制 dict 并剔除 `tar_format`，保留 `conandata.yml` 的规范字段：

```python
def source(self):
    source_data = dict(self.conan_data["sources"]["20190701"])
    source_data.pop("tar_format", None)
    get(self, **source_data, strip_root=True)
```

判别三行：

```console
① grep -n 'tar_format'  archives/<l>/<pkg>/<ver>/conandata.yml
② grep -n 'def source' -A5 archives/<l>/<pkg>/<ver>/conanfile.py
③ conan create archives/<l>/<pkg>/<ver> -pr:h=<profile> -pr:b=<profile>
```

## 回退方案（优先级 2）

不展开 dict，显式传 `url` / `sha256`：

```python
get(self, url=self.conan_data["sources"][ver]["url"],
        sha256=self.conan_data["sources"][ver]["sha256"], strip_root=True)
```

同样规避 `TypeError`，代价是多版本 `conandata` 场景下维护成本更高。

## 禁止做法

- ❌ **删掉 `conandata.yml` 的 `tar_format`**：会丢归档规范字段（CI 索引/人工核对
  依赖它），且下次按模板重生成时问题复现。
  后果：归档元数据不完整，问题被推迟且更难发现。
- ❌ **用 `--build=missing` / 跳过 source / 本地缓存绕过**：这是配方缺陷，
  绕过后 CI 的 G2 干净构建仍必红。
  后果：本地假绿、CI 红，白费一轮 CI 与环境。

## 实证

- 包：`tunnelx/20190701`（Java / javac+jar，HarmonyOS PC）
- 首个错误：`conan create` → `source()` 第 94 行 `TypeError`
- 修复：`source_data.pop("tar_format", None)` 后重新 `conan create` → **rc=0**，
  包 `6b129b068851896169fae42d399fa922d239ce8a` 正常产出，
  `test_package` 11/11 通过（含 T5b 启动器 CLI 契约检查）
- 后续 `conan-verify` G1–G4 + L2/L4/L5 全 PASS
