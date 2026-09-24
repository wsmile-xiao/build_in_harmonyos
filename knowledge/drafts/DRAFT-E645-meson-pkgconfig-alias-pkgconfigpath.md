# ═══ Draft knowledge entry — meson dependency 按 .pc 文件名解析，pkg_config_aliases 桥接 ═══
# Timestamp: 2026-09-21
# Software: libaudec 0.3.4（meson+pkg-config 依赖组合通例）
# Gate: conan create build() / meson setup
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E645
severity: 2
category: platform|build-system|meson
trigger_tool: meson / pkg-config / conan PkgConfigDeps
phase: configuration|dependency-resolve
approach: 两层排查：① generate() 里用 conan.tools.env.Environment 显式 prepend
  PKG_CONFIG_PATH=self.generators_folder（Conan 不自动注入），build() 以
  vars().apply() 包住 meson 调用；② 依赖包缺 pkg_config_name 时
  pc=PkgConfigDeps(self); pc.set_property("<依赖名>","pkg_config_aliases",
  ["<上游检索名>"]); pc.generate() 生成官方薄别名

keywords: meson, dependency, pkg-config, PkgConfigDeps, pkg_config_name,
  pkg_config_aliases, PKG_CONFIG_PATH, samplerate, sndfile, generators_folder,
  not found, tried pkgconfig

error_signature: Dependency "[^"]+" not found, tried pkgconfig|Dependency "[^"]+" not found
match_keywords: Dependency,not found,tried pkgconfig,pkg_config_aliases,PKG_CONFIG_PATH

root_cause: pkg-config 按 .pc 文件名精确匹配；PkgConfigDeps 命名缺省回落 conan 包名
  （libsamplerate.pc），与上游 dependency('samplerate') 检索名错位即报 not found。
  同包的 sndfile 恰好设了 pkg_config_name='sndfile' 故解析成功——同配方内两种命运
  并存是识别本缺陷的强信号
affected_scope: 全部 meson + conan 包，上游 pc 名≠conan 包名的依赖
  （libsamplerate→samplerate、mpg123→libmpg123 等）；audiowmark copyfile 补
  libmpg123.pc、at-spi2-core 手写兼容 .pc 均为同一错位的替代修法

rec_priority: 1
