# urdfdom_headers 3.0.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 liburdfdom_headers.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

纯头库。注意上游 APPEND_PROJECT_NAME_TO_INCLUDEDIR 默认 ON，头装到 include/urdfdom_headers/ 下，故 cpp_info.includedirs 设为 include/urdfdom_headers，消费方才能照上游写法 #include <urdf_model/model.h>。
