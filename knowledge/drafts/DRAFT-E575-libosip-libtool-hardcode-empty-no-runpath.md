# DRAFT: 无 patchelf 时置空 libtool hardcode_libdir_flag_spec，从链接源头消除 .so 的 DT_RUNPATH

- **包**: libosip/5.3.2 (autotools, libtool)
- **日期**: 2026-09-11
- **环境**: OHOS PC (aarch64, musl), OHOS clang/lld, 无 patchelf
- **状态**: 实测验证（构建 122/122 上游测试全过 + readelf 双 .so 均无 RUNPATH）

## 症状

autotools 包安装的 `libfoo.so` 携带绝对 `DT_RUNPATH=<pkgroot>/lib`。
本机所有已知消除手段均不可用：

| 手段 | 结果 |
|------|------|
| patchelf | 未安装 |
| configure `--disable-rpath` | libosip2 configure 无此选项（非自动生成） |
| lld `--no-rpath` | 不存在该选项 |
| `-Wl,-rpath,`（空参数） | lld 把空串当输入文件，链接失败 |
| LDFLAGS 清空 | 无效 — libtool `hardcode_into_libs=yes` 在 install 模式自动加 `-rpath $libdir` |

## 根因

libtool 脚本对共享库安装链接时通过 `hardcode_libdir_flag_spec`
（展开为 `$wl-rpath $wl$libdir`）把 `$libdir` 写入 RUNPATH。这是
libtool 的核心行为，LDFLAGS 控制不了。

## 修复

configure 之后、make 之前，对**生成的** build 树 libtool 脚本做替换：

```python
replace_in_file(self, os.path.join(self.build_folder, "libtool"),
    'hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
    'hardcode_libdir_flag_spec=""')
```

效果: `.so` 不再带 DT_RUNPATH，DT_SONAME/DT_NEEDED 完整保留，
重新链接符号全部正常。

副作用: 构建树内的测试程序失去对未安装 .so 的自动定位，需
`LD_LIBRARY_PATH=<build>/src/*/.libs` 运行（在配方的测试 runner 里
统一设置即可）。

## 验证

```bash
readelf -d libosip2.so.15.0.1 | grep -c "RPATH\|RUNPATH"   # 0
LD_LIBRARY_PATH=... make check                               # 122/122
```

## 与现有知识的关系

- E077: 事后 patchelf 改 RUNPATH 触发签名失效四步流程 → 本条是生成时
  预防，且覆盖无 patchelf 环境
- E088: musl namespace 忽略 RUNPATH/LD_LIBRARY_PATH 的运行时加载问题
  （加载侧）→ 本条是链接期生成侧，正交
- E504: CMake install 期 RPATH_CHANGE 重写 .so 致 musl loader 无法加载
  （CMake 特有）→ 本条是 autotools/libtool 通用
- E537: Conan cache 绝对路径 DT_NEEDED 泄漏（NEEDED 侧）→ 本条是
  RUNPATH 侧，且方案为链接期置空而非 link-time SONAME 改写
- E042: 仅 Python 扩展模块场景 → 本条是通用 autotools/libtool 包

## 通用性

所有用 libtool 的 autotools 包在无 patchelf 的 OHOS PC 上通用；
发布规范要求产物无 RPATH 时首选。
