# Draft: meson dependency('liblzma') 找不到 — PkgConfigDeps 组件名与上游 pkg-config 名不匹配

- **Draft ID**: DRAFT-libxmlb-liblzma-pc-shim
- **来源软件**: libxmlb 0.3.19
- **发生阶段**: conan create build() → meson.configure()
- **状态**: 待人工审核提升为正式 E 条目

## 错误特征

```
../meson.build:134:7: ERROR: Dependency "liblzma" not found (tried pkg-config)
```

meson 按上游 pkg-config 名 `liblzma` 查找 liblzma.pc，但 conan 生成的 generators 目录里只有
`xz.pc`（PkgConfigDeps 按 xz 依赖组件名生成）。

## 根因

conan PkgConfigDeps 生成 .pc 的文件名 = 依赖包组件声明的 `pkg_config_name`（xz → xz.pc）；
而上游 meson.build 的 `dependency('liblzma')` 按上游 pkg-config 名字（liblzma.pc）查找。
两者不同名且无转发文件时，meson 检测失败。这是 PkgConfigDeps 生成名与上游查找名的通用落差。

## 修复

消费方配方 `generate()` 内、`PkgConfigDeps(self).generate()` 之后补写 `liblzma.pc` shim
（幂等：已存在则跳过）：

```python
def _fix_xz_pc_files(self):
    gens = self.generators_folder
    xz_pc = os.path.join(gens, "liblzma.pc")
    if os.path.isfile(xz_pc) or "xz" not in self.dependencies:
        return
    xz = self.dependencies["xz"]
    libdir = xz.cpp_info.libdirs[0]
    prefix_dir = libdir[:-len("lib")] if libdir.endswith("lib") else os.path.dirname(libdir)
    ...
    # 写 prefix/libdir/includedir + Libs: -llzma + Version: xz.ref.version
```

## 验证

- 修复前: `grep -n "liblzma" build/meson-logs/meson-log.txt` 显示 `Dependency "liblzma" not found`
- 修复后: meson-log.txt 出现 `Run-time dependency liblzma found: YES`；conan create 全流程通过；
  上游 lzma 压缩测试 `builder{source-lzma}` 实际运行 OK

## 适用边界 / 反例

- 适用: 任意 meson 消费者 + xz 依赖的 PkgConfigDeps 场景；推广到其他"组件名 ≠ 上游 pkg-config 名"依赖
- 反例: 依赖方（xz 配方）若已把组件 pkg_config_name 别名设为 liblzma，则无需消费方 shim

## 查重差异（vs E348）

- E348: 上游多 .pc 体系（glib-2.0/gobject-2.0/gio-2.0）缺副 .pc → generate() 转发型 .pc；
  根因是"每包单 .pc 输出 vs 多 .pc 体系"
- 本候选: 单组件 xz 单 .pc（xz.pc），但文件名与上游 meson 查找名（liblzma）不匹配 → shim 生成；
  根因是"组件名 vs 上游依赖名"
- 触发与解决同族（PkgConfigDeps 生成名 ≠ 上游查找名 + generate() 补 pc），库、组件、文件名模式均不同，
  存在独立新增差异（点 vs 面），可跨库复用，已实测验证