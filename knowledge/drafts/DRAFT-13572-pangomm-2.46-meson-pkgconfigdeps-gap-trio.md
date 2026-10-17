# DRAFT-13572-pangomm-2.46-meson-pkgconfigdeps-gap-trio：conan 2 PkgConfigDeps 与 meson 依赖探测的三类缺口及配方侧补齐

> Contributor: LIMInGZE666 | Status: Draft | Updated: 2026-09-27
> Source: pangomm-2.46 2.46.5 适配（任务 13572）
> 对应：`knowledge/drafts/DRAFT-13572-pangomm-2.46-meson-pkgconfigdeps-gap-trio.kv`

## 问题

conan 2 的 PkgConfigDeps 按配方 package_info 生成 .pc，但只写标准变量
（prefix/libdir/includedir/Libs/Cflags/Requires）。GNOME mm 家族等上游 meson
项目的探测方式超出这个子集，pangomm 2.46.5 一次踩全三类缺口：

1. **自定义 pc 变量丢失** — meson.build L123 无条件调用
   `glibmm_dep.get_variable('gmmprocdir')`，上游自家 glibmm.pc.in 有
   `gmmprocdir=${libdir}/glibmm-2.4/proc`，但 conan 生成的 glibmm-2.4.pc
   没有这个变量 → configure 报 get_variable 未定义；
2. **别名 pc 查找落空** — 上游用 `dependency('pangocairo')`，pango 配方
   的 PkgConfigDeps 只生成 pango.pc（不感知组件名）→ Dependency found: NO；
3. **find_library 工具库不在搜索路径** — tools/extra_defs_gen 用
   `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')` 找 glibmm
   包内工具库（glibmm 侧 `subdir('tools')` 无条件构建安装），该库只在
   conan 的 glibmm package_folder/lib 里，meson 原生不搜 → 找不到后走
   `dependency('', fallback:...)` 直接报错（wrap_mode=nodownload 下必炸）。

## 配方侧补齐（generate() 三招，不改上游、零 patch）

```python
def generate(self):
    PkgConfigDeps(self).generate()

    # 缺口② 别名 pc：转发型 .pc，Name/Description/Version 三字段缺一不可
    # （pkg-config 0.29.2 校验），Version 从 pango.pc 实测读出
    for _al in ['pangocairo=pango', 'pangoft2=pango']:
        _pc, _req = _al.split("=", 1)
        _path = os.path.join(self.generators_folder, _pc + ".pc")
        if not os.path.isfile(_path):
            with open(_path, "w") as _f:
                _f.write("Name: %s\nDescription: Conan package: %s\n"
                         "Requires: %s\nVersion: %s\n" % (_pc, _pc, _req, _pango_ver))

    # 缺口① 自定义 pc 变量：读回依赖方 .pc，缺变量则追加
    # （取值照抄上游 .pc.in：gmmprocdir=${libdir}/glibmm-2.4/proc）
    for _pv in ['glibmm-2.4:gmmprocdir=${libdir}/glibmm-2.4/proc']:
        _pc, _kv = _pv.split(":", 1)
        _path2 = os.path.join(self.generators_folder, _pc + ".pc")
        if os.path.isfile(_path2) and "gmmprocdir" not in open(_path2).read():
            with open(_path2, "a") as _f:
                _f.write("%s\n" % _kv)

    # 缺口③ find_library：把 glibmm 的 libdir 注入链接参数
    # （经 MesonToolchain 落入 native file 的 cpp_link_args）
    dep_glibmm = self.dependencies.get("glibmm")
    if dep_glibmm:
        for _ld in dep_glibmm.cpp_info.libdirs:
            self.conf.define("tools.build:sharedlinkflags",
                             self.conf.get("tools.build:sharedlinkflags", default=[]) + ["-L" + _ld])
            self.conf.define("tools.build:exelinkflags",
                             self.conf.get("tools.build:exelinkflags", default=[]) + ["-L" + _ld])

    tc = MesonToolchain(self)
    tc.project_options["maintainer-mode"] = "false"      # tarball 预生成绑定
    tc.project_options["build-documentation"] = "false"  # doxygen/dot 缺失
    tc.project_options["wrap_mode"] = "nodownload"       # CI 无网
    tc.generate()
    self._inject_meson_binaries()   # 补 ar/ranlib/pkg-config 绝对路径
```

## 要点

- **取值照抄上游 .pc.in**：gmmprocdir 的值不是发明，是上游 glibmm.pc.in 的
  `${libdir}/glibmm-2.4/proc`；ABI 线不同则 proc 目录名不同（2.68 线是
  glibmm-2.68）；
- **转发 pc 四行**：Name/Description/Requires/Version 齐了才过 pkg-config
  0.29.2 校验，Version 不能写死——从真实 pango.pc 读出（meson 的
  `version: >= x` 断言靠它）；
- **零 patch 原则**：三类缺口都是 conan 生成侧缺失，配方补齐即可，改上游
  meson.build 是最后手段；
- **配套**：同栈钉版冲突用 `override=True` 统一（libsigc/2.12.1、
  fontconfig/2.18.1.1），sigc++-2.0 在 2.x 内 SONAME 不变、ABI 稳定。

## 跨库适用

pangomm/gtkmm/atkmm 全系对 glibmm 的 gmmprocdir、pango 的别名 pc、
extra_defs 工具库是同款需求；任何「meson 上游用 get_variable() /
dependency('别名') / find_library() 探测」的包，均可按本三招在 generate()
补齐。本任务真机八门禁 Verdict PASS 全实录见 MR 正文。
