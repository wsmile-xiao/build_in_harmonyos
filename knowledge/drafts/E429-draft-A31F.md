# E429 — Conan 2 zip strip_root 对扁平压缩包误判公共字符串前缀为根目录并 IndexError

## 错误特征

`conan create` / `conan source` 的下载解包阶段，配方 `get(..., strip_root=True)`
对**无顶层目录的扁平 zip** 直接崩溃：

```text
Uncompressing tnt_126.zip to ...
IndexError: list index out of range
  File ".../conan/tools/files/files.py", line 416, in unzip
    member.filename = name.split("/", 1)[1]
```

## 触发条件

- 构建系统: 任意（错误发生在 source() 解包，与构建系统无关）
- 阶段: 下载/解包（conan get/unzip，strip_root=True）
- 归档形态: zip 内文件直接位于压缩包根（无唯一顶层目录）；
  老牌官方网站手工分发的 zip 常见（如 NIST tnt_126.zip），
  GitHub codeload tarball 恒有 repo 根目录，不受影响

## 根因分析

Conan 2 的 zip strip_root 实现用 `os.path.commonprefix()`（**纯字符串前缀**，
不是路径组件）检测根目录名：

```python
common_folder = os.path.commonprefix(names).split("/", 1)[0]
if not common_folder and len(names) > 1:
    raise ConanException(...)   # 护栏对扁平包不生效
for member in zip_info:
    member.filename = name.split("/", 1)[1]   # 无 "/" 的条目 → IndexError
```

扁平包中所有文件共享文件名公共前缀（如 21 个 `tnt*.h` 的公共前缀
`tnt`），该前缀被误判为"根目录"，护栏条件 `not common_folder` 不触发，
随后对不含 `/` 的条目取 `split("/", 1)[1]` 直接越界。
tar.gz 的 strip_root 实现路径不同，无此问题。

## 解决方案

### 推荐方案

解包前先核实归档布局；扁平包（无顶层目录）必须 `strip_root=False`：

```python
get(self, **self.conan_data["sources"], strip_root=False)
```

conandata.yml / source() 注释记录布局特征，避免后人"顺手"改回 True。

### 禁止做法

- ❌ 对扁平 zip 保持 strip_root=True 并试图用 pattern/excludes 绕过
  （崩溃点在条目名重写，过滤救不了）
- ❌ 为绕过此问题改用 tar 重新打包源码上传个人源（违反 R39 官方源要求）

## 验证

```bash
# 判定归档是否扁平（True = 扁平 → strip_root=False）
python -c "import zipfile; n=zipfile.ZipFile('src.zip').namelist(); print(all('/' not in x for x in n))"
```

## 关联条目

- 相关: E276（Conan get() 对 URL basename 误判解压器报 BadZipFile——
  同属 get()/归档格式判定族）
- 实证案例: libtnt 1.2.6（NIST TNT），conan 2.31.2 本机复现，
  详见 kv 文件 evidence 字段
