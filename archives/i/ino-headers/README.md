# ino-headers — OpenHarmony 编译档案

## 软件简介
ino-headers 是 NASPRO 声音处理架构（NASPRO Architecture for Sound Processing）
中 ino 组件的公共头文件库：为所有 ino 实现（JavaScript 执行引擎绑定）提供统一
的 C API 声明——执行上下文（`ino_context`）、变体类型（`ino_variant`）、原生
方法回调（`ino_method_cb`）等类型定义与函数声明。**纯头文件库**：单个
`lib.h`（约 720 行，仅声明无实现），无任何需要编译的 C 源码。版本 0.4.0，
API 0.0.0。许可证为 ISC 风格（COPYING 文件，见 notes）。

## OHOS 适配要点
- 手装范式（对齐已合入 kicad-demos 10.0.4 先例）：跳过上游 autotools
  （上游 `make all`/`make check` 均为 no-op；autoconf 2.68 生成的 configure
  以 `umask 077` 建临时目录，OHOS HMDFS 拒绝写入 0700 目录——E011 路径陷阱，
  零收益引入高风险）。零补丁、零 configure
- `package()` 按上游 Makefile.am `inoincludedir` 规则把 `lib.h` 装到
  `include/ino-0/ino/lib.h`；上游仅发 `ino-headers-0.pc.in` 模板，配方在
  `package()` 内生成 `ino-headers-0.pc`（`Cflags: -I${includedir}/ino-0`，
  采用 `${pcfiledir}/../..` 可迁移前缀，包移动后 pkg-config 仍可用）；
  `cpp_info` 声明 cmake/pkg_config 属性并暴露 PKG_CONFIG_PATH
- `lib.h` 的可见性宏（INO_PUBLIC/INO_PRIVATE 等）在非 GCC 下自动退化为空
  宏，OHOS clang 走 GCC 分支（`__attribute__((visibility))`）语义正确；
  C++ 下经 `INO_BEGIN_C_DECLS` 包裹为 `extern "C"`，声明消费无碍
- `build()` 防漂移校验 8 个关键源文件在位；`package_id` 清空（内容与
  settings 无关）；R32 仅支持 Linux/OHOS

## 依赖关系
- 无编译/运行依赖（纯头文件，零编译产物零可执行文件，R38 无需 commands.json）
- 被依赖: 无（供各 ino 实现编译期消费，非 conan 依赖）

## 参考资料
- [NASPRO: ino library](https://naspro.sourceforge.net/libraries/ino/)
- [SourceForge: NASPRO releases](https://sourceforge.net/projects/naspro/files/releases/)
