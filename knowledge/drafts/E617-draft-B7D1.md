# E617 — 依赖只有动态 binary 时：静态库消费者/CLI 产物加 `-Wl,-rpath` 才能直接执行

> Contributor: libfreehand-tools 0.1.2 适配 | Status: Draft | Updated: 2026-09-20
> 对应：`knowledge/drafts/E617-draft-B7D1.kv`
> 触发场景：`lcms2/2.19` 制品仓只有 `.so`（无 `.a`），而 libfreehand 的 `FHParser.o`
> 需要它的符号

## 错误签名
```
error while loading shared libraries: liblcms2.so.2: cannot open shared object file
（CI L2）[warn] L2: <bin> --version/--help failed (non-blocking)
```

## 现象

构建、链接全部成功，`conan create` 也 PASS；但**运行**包内 `bin/` 或 test_package 里自己编的
消费者二进制时，动态加载器报找不到 `liblcms2.so.2`。OHOS 系统目录里只有**自研构建、soname 不同**
的 `/system/lib64/liblcms_shared.z.so`，所以系统库顶不上。

## 根因

1. `archives/l/lcms2/2.19` 的配方 `default_options = {"shared": True}`，制品仓只发布了动态
   binary：`conan install --requires=lcms2/2.19 -o lcms2/*:shared=False --build=never`
   实测 `Missing prebuilt package`（**不能**用 `-o shared=False` 绕开）。
2. 静态库本体（`libfreehand-0.1.a` 的 `FHParser.o`）引用该动态库符号 → 任何链接它的最终产物
   都带 `DT_NEEDED=liblcms2.so.2`。
3. 没有 RUNPATH/LD_LIBRARY_PATH 时，进程启动即失败——**症状出现在运行期**，容易被误读成
   "产物坏了/链接错了"。

## 识别特征
- **Severity**: 🟡 Medium
- **Trigger tool**: runtime（CI L2 `<bin> --version`、test_package `self.run`）
- **Phase**: runtime
- **Pattern**: `requires\(\s*["']lcms2/|PKG_CHECK_MODULES\(\[LCMS2\]|Missing prebuilt package.*lcms2`
- **Category**: conan, shared-library, rpath, ohos, autotools

## 修复方案

```python
# 主配方 generate()
def generate(self):
    tc = AutotoolsToolchain(self)
    ...
    lcms_libdir = self.dependencies.host["lcms2"].cpp_info.libdirs[0]
    tc.extra_ldflags.append("-Wl,-rpath,%s" % lcms_libdir)
    tc.generate()

# test_package/conanfile.py 里必须**再来一遍**：
# 消费者二进制是自己编的，不继承主配方的 LDFLAGS
lcms_libdir = self.dependencies["lcms2"].cpp_info.libdirs[0]
tc.extra_ldflags.append("-Wl,-rpath,%s" % lcms_libdir)
# 链接行仍需显式 -L<libdir> -llcms2（静态闭包不会自动带上动态依赖）
```

两个坑：
- 必须用 `-Wl,-rpath,<dir>` 形式；裸 `-rpath <dir>` 会被 **libtool** 当作它自己的安装路径选项吃掉。
- 别把依赖的 `.so` 拷进自己包里充数（会变成"包内携带系统同名库"，破坏 R26/G3 口径）。

## 参考实现
- `archives/l/libfreehand-tools/0.1.2/conanfile.py` + `test_package/conanfile.py`

## 验证方法
1. `conan install --requires=lcms2/2.19 -o lcms2/*:shared=False --build=never` → rc=1（只有动态）
2. `readelf -d <pkg>/bin/fh2raw` → 同时有 `RUNPATH=[…/lcms2…/p/lib]` 与 `NEEDED=[liblcms2.so.2]`
3. 包内 `bin/fh2raw --version` → rc=0（不手工设 `LD_LIBRARY_PATH`）
4. test_package 消费者二进制 `self.run` 通过（libfreehand-tools 0.1.2 实测 6/6 断言）
