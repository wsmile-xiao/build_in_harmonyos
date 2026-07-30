# console_bridge 1.0.2.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libconsole_bridge.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

重做原 1.0.2：其产物无 SONAME，且自带 cmake target 写了 IMPORTED_NO_SONAME TRUE，下游链接后 DT_NEEDED 被烤成构建机 conan cache 绝对路径（A/B 实测：搬移目录后即无法加载）。本版 SONAME=libconsole_bridge.so.1.0，与上游 SOVERSION 一致。test_package 10 条真实行为断言。
