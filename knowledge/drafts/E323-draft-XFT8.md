# E323 — PkgConfigDeps 不扩展 PKG_CONFIG_PATH，上游 PKG_CHECK_MODULES 探测不到 Conan 元数据

## 错误特征

生成器目录里明明有 `.pc` 文件，configure 却说找不到：

```
Package xorg-macros was not found in the pkg-config search path.
Perhaps you should add the directory containing `xorg-macros.pc'
to the PKG_CONFIG_PATH environment variable
No package 'xorg-macros' found
```

或在别的包里直接以 `configure: error: Package requirements (foo >= 1.2) were not met` 收场。

## 触发条件

- 构建系统: autotools（上游用 `PKG_CHECK_MODULES`）
- 阶段: configure
- 前提: 依赖由 Conan 提供，`PkgConfigDeps` 已生成 `.pc`

## 根因分析

两个独立缺口叠加：

1. `PkgConfigDeps` 只负责把 `.pc` 写到 generators 目录，**不会**把该目录追加到
   `PKG_CONFIG_PATH`；`AutotoolsToolchain` 也不保证包含它。于是上游探测只看得到
   系统路径，看不到 Conan 生成的元数据。
2. 上游 `.pc` 之间的引用名可能与 Conan 包名不一致（如 `freetype` 需以
   `freetype2` 被探测、`xorgproto` 需以 `xproto` 被探测），名字不匹配时同样
   表现为"找不到包"。
3. X.Org 类库还额外需要 `xorg-macros.pc`（由 `util-macros` 提供）。它缺失时
   configure **不报错**，只是 `macros_datadir` 为空、man/DOCUSER 一组替换退化，
   属于静默降级，后续排查代价更高。

## 解决方案

### 推荐方案

在 `generate()` 内做三件事，全部留在配方局部：

1. `self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)`
2. 用 `PkgConfigDeps.set_property("<pkg>", "pkg_config_name", "<探测名>")`
   把生成名对齐上游探测名
3. 需要 `.m4`/`.pc` 的构建工具用 `tool_requires` 声明（例如
   `util-macros/1.20.1`），由其 `package_info()` 暴露
   `PKG_CONFIG_PATH`/`ACLOCAL_PATH`，经 `VirtualBuildEnv` 生效

### 禁止做法

- ❌ 为救单个包去改**共享的** OHOS profile 或写全局 shell 配置的
  `PKG_CONFIG_PATH`/`CPATH`/`LIBRARY_PATH`（profile 是共享文件；全局路径还会被
  pkg-config 当作系统路径处理）
- ❌ 只改 `build()` 里的 `os.environ` 就想覆盖 profile 环境——
  `ConanFile.run()` 会重新加载 `conanbuild`，配方进程环境可能被覆盖
- ❌ 忽略 `xorg-macros` 缺失的告警继续交付（静默降级会带进产物）

## 验证

```bash
cd <build_folder> && source conanbuild.sh
pkg-config --exists xrender && pkg-config --modversion xrender
pkg-config --exists xorg-macros && pkg-config --variable=pkgdatadir xorg-macros
ls <generators_folder>/*.pc | xargs -n1 basename
```

## 关联条目

- 相关: E322（同属 configure 阶段环境注入问题）、E075（LIBRARY_PATH/CPATH 口径）
- 来源: libxft 2.3.8 适配，2026-08-28（`util-macros` 与 `freetype2`/`xproto`
  探测名实测）
