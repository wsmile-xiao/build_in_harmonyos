# E429 — autotools 应用型配方给 AutotoolsToolchain 传绝对 prefix 会破坏 DESTDIR staging

> Draft（待知识库主编审核 promote）｜对应: `knowledge/drafts/E429-draft-996F.kv`
> 来源包：spinner/1.2.4（OHOS PC aarch64）

## 错误特征

`conan create` 本身 rc=0、编译链接全部成功，但包内没有 `bin/`，产物被放到了一个
被拼接过的嵌套路径里：

```
make[1]: /bin/bash .../mkinstalldirs /root/.conan2/p/b/spinnXXX/p/root/.conan2/p/b/spinnXXX/b/build-release/prefix/bin
/usr/bin/install -c spinner /root/.conan2/p/b/spinnXXX/p/root/.conan2/p/b/spinnXXX/b/build-release/prefix/bin/spinner
```

随后 test_package 阶段失败：

```
FAIL A0 - binary not executable: /root/.conan2/p/b/spinnXXX/p/bin/spinner
```

注意 `p/` 之后**又出现了完整的绝对路径**——这是本错误的判定特征。

若改传相对路径，则更早在 configure 阶段就失败：

```
configure: error: expected an absolute directory name for --prefix: prefix
```

## 触发条件

- 构建系统: autotools（`bin_PROGRAMS`，application 型配方）
- 阶段: installation → testing
- 关键: 在 `generate()` 里给 `AutotoolsToolchain` 传了非默认 `prefix`

## 根因分析

`--prefix` 与 `DESTDIR` 是两个独立的拼接项，谁在前谁在后决定了 staging 是否生效：

1. conan 的 `Autotools.install()` 会自动给 `make install` 追加
   `DESTDIR=<package_folder>`；
2. autotools 的 install 规则再把 `--prefix=<prefix>` 拼在其**后**。

于是当 `prefix` 是绝对路径时，最终目录变成
`DESTDIR + 绝对前缀` = `<package_folder>/root/.conan2/.../prefix/bin/`，
DESTDIR staging 完全失效。

而 R49 强调"用 build_folder 私有 prefix、不要写死 /usr/local"，很容易让人
下意识写 `prefix=os.path.join(self.build_folder, "prefix")` —— build_folder
是绝对路径，恰好踩中本坑。而想用相对路径又会被 autotools 硬性拒绝，
形成"绝对路径破坏 staging、相对路径不被接受"的两难。

## 解决方案

### 推荐方案

保持默认 `prefix=/`，让 conan 的 DESTDIR staging 正常生效：

```python
def generate(self):
    tc = AutotoolsToolchain(self)   # 默认 prefix="/"
    tc.generate()
```

产物落在 `<package_folder>/bin/`，且不会写入任何系统位置——这已经同时满足
R49 的"不得注入共享前缀"要求。

### 禁止做法

- ❌ `AutotoolsToolchain(self, prefix=os.path.join(self.build_folder, "prefix"))`
  —— 绝对路径会被拼在 DESTDIR 之后
- ❌ `AutotoolsToolchain(self, prefix="prefix")`
  —— 相对路径被 configure 直接拒绝

### 回退方案

若确实需要非 `/` 的 prefix，放弃 `make install`，在 `package()` 里精确取产物：

```python
copy(self, "<可执行文件名>", self.build_folder,
     os.path.join(self.package_folder, "bin"), keep_path=False)
```

## 验证

```bash
conan create <配方目录> -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
find <package_folder> -type f          # 应看到 bin/<可执行文件名>
ls <package_folder>/bin/               # 产物必须在包内 bin/，而非嵌套路径
```

## 关联条目

- 原则: R49（依赖注入必须用私有 prefix，不得污染共享系统前缀）
- 类似场景: 库型配方因产物在 `lib/` 且常忽略 `--prefix`，较少触发本问题
