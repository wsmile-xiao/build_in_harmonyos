# urdfdom 6.0.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 liburdfdom.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

依赖 console_bridge + tinyxml2 + urdfdom_headers 三者，全走 find_package CONFIG，三个 config 目录布局各不相同（tinyxml2 用 lib/cmake/<name>，另两个用 lib/<name>/cmake），逐个显式给 <Pkg>_DIR。test_package 20 条断言解析一段两连杆 URDF 并逐项对账 —— 同时是三个接线正确性的端到端证据。
