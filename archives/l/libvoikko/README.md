# libvoikko

## 简介
拼写检查、断词与语法检查库，为 Voikko（芬兰语 NLP）提供 C API（C++17 实现）。
对外头文件 `voikko.h`，导出 `voikkoInit` / `voikkoSpellCstr` / `voikkoHyphenateCstr` 等。

## OHOS 适配
- Autotools：config.sub 不识别 `aarch64-linux-ohos`，configure 覆盖 `--host/--build`
  为 gnu 三元组（本机原生 build==host，真正编译器由 OHOS clang profile 决定）。
- uname-shim：设备 `uname` 报告 HarmonyOS，对 config.guess/特性探测返回 Linux。
- `--disable-hfst --disable-vislcg3 --disable-lttoolbox`：仅用内置 VFST 后端，不引入
  hfstospell / cg3 / tinyxml2 / lttoolbox。
- `--disable-buildtools --disable-testtools`：纯库包，不产出 CLI，无需 commands.json。

## 依赖
- 无 Conan 依赖（pthread/libm 为 bionic 系统库）。
- 构建工具：clang++, autotools, libtool, pkg-config, python3（configure 探测用）。
- 运行期真正的芬兰语词典来自独立数据包 voikko-fi（未随本包发布）。

## 参考
- 官方：https://voikko.puimula.org/
