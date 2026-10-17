# ═══ Draft knowledge entry — meson both_libraries() 连带构建 .so,非 PIC 静态依赖链接必败 ═══
# Timestamp: 2026-09-21
# Software: libaudec 0.3.4（both_libraries + conan 非-PIC 静态依赖的 meson 包通例）
# Gate: conan create build() / meson compile
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-E644
severity: 2
category: platform|build-system|meson
trigger_tool: meson / ld.lld
phase: build
approach: default_library=static 仍失败时，先 `llvm-readelf -r` 抽查依赖静态库对象确认
  非 PIC（R_AARCH64_ABS64 绝对重定位），再把 both_libraries( 改 static_library( 并
  同步改写**全部** .get_static_lib() 调用点（主 meson.build 之外，tests/meson.build
  里通常还有一处——漏改报 Unknown method "get_static_lib"）

keywords: meson, both_libraries, static_library, default_library, R_AARCH64_ABS64,
  非 PIC, fPIC, libsamplerate, lld, StaticLibraryHolder, get_static_lib,
  recompile with -fPIC

error_signature: can not be used when making a shared object|can't create dynamic relocation R_AARCH64_ABS64|recompile with -fPIC|can't create dynamic relocation R_AARCH64_ADR_PREL_PG_HI21
match_keywords: both_libraries,R_AARCH64_ABS64,shared object,StaticLibraryHolder,get_static_lib

root_cause: both_libraries() 的语义是 static+shared 双建，与 default_library 无关；
  conan 侧依赖（如 libsamplerate/0.2.2）只发布 shared=False 静态库且配方未设
  fPIC/CMAKE_POSITION_INDEPENDENT_CODE，对象含绝对重定位（实测 src_sinc.c.obj
  31 处 R_AARCH64_ABS64），lld 拒绝非 PIC 对象链入共享库。消费侧注入 -fPIC 只
  影响本项目对象，救不了预编译依赖——唯一出路是不构建 .so
affected_scope: OHOS 上全部「meson 上游用 both_libraries/显式 shared 变体 × conan
  非-PIC 静态依赖」组合；判定不看 fPIC 选项名，readelf 重定位类型才是权威

rec_priority: 1
