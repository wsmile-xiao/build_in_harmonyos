# imlib2 1.9.1：依赖包 .pc 名称缺失 / DESTDIR 破损 → generators_folder 绝对路径桥接

## 场景

imlib2 1.9.1（autotools）configure.ac 硬性
`PKG_CHECK_MODULES(FREETYPE, freetype2)`。conan 依赖 freetype/2.14.3.1
配方**未设 `pkg_config_name`** → PkgConfigDeps 生成 `freetype.pc` 而非
`freetype2.pc`；同时包内自带的 `lib/pkgconfig/freetype2.pc` 是 DESTDIR 安装的
原始文件（`prefix=/`、`Cflags: -I//include/freetype2` 指向无效路径）。

## 现象

```text
configure: error: Package requirements (freetype2) were not met:
No package 'freetype2' found
```
或（用包内 .pc 直连时）：
```text
fatal error: 'ft2build.h' file not found
```

## 根因

1. 配方未设 `pkg_config_name` → PkgConfigDeps 用包名生成 .pc，configure 按官方
   模块名（freetype2）找不到。
2. 包内自带官方 freetype2.pc 的 prefix 是 DESTDIR 安装残留的 `/`（`//include`
   等），消费者/configure 拿到的是死路径——**不能只把包内 pkgconfig 目录加进
   PKG_CONFIG_PATH**。

## 修复（conanfile.py generate()）

```python
def generate(self):
    PkgConfigDeps(self).generate()
    if "freetype" in self.dependencies:
        _pf = self.dependencies["freetype"].package_folder
        if _pf:
            save(self, os.path.join(self.generators_folder, "freetype2.pc"),
                 "prefix={0}\nlibdir={0}/lib\nincludedir={0}/include\n"
                 "Name: freetype2\nVersion: 2.14.3\n"
                 "Libs: -L{0}/lib -lfreetype\n"
                 "Cflags: -I{0}/include/freetype2\n".format(_pf))
    # configure_args 追加 PKG_CONFIG_PATH=generators_folder
```

要点：桥接 .pc 用**依赖包实际绝对路径**（self.dependencies[..].package_folder，
不能用 glob 硬编码 conan 缓存路径——CI 缓存目录名不同）；绝对路径避免
pkg-config 相对解析歧义。

## 验证

- `conan create`：configure 正确输出 `FREETYPE=yes`、`PNG/ZLIB loader=yes`；
  test_package（find_package imlib2 + 公开 API）编译链接运行 **RC=0**。
- 修复前：configure "No package 'freetype2' found"（first error 可复现）。

## 边界

- 前置检查：先 `cat <包>/lib/pkgconfig/*.pc` 看 prefix 行——若已是
  `${pcfiledir}` 相对形式或正确绝对路径，直接用即可，不需要桥接。
- 依赖配方已设正确 `pkg_config_name` 时也不需要桥接。
- 反例：包内 .pc 正常而仅名称不符时，也可在依赖方修正 pkg_config_name
  （需动该依赖配方，走依赖库 PR），桥接是当前库自包含的最小方案。

## 查重

| 既有条目 | 关系 |
|---|---|
| DRAFT-ncdc-1.25-glib-pc-name-autotools-ac-check-lib | similar_to：同为 PKG_CHECK_MODULES 找不到 .pc；新增差异=**DESTDIR 破损 pc 检测** + **generators_folder 绝对路径桥接** |
| E072（config.sub linux-ohos） | 相邻但不同面 |
| E089（pkg.m4/pkgconfigdir） | 弱相关 |

同 stem 草稿：DRAFT-imlib2-1.9.1-pc-name-destdir-bridge.kv