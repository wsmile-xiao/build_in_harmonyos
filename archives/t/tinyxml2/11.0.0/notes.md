# tinyxml2 11.0.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libtinyxml2.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

test_package 15 条断言：解析/类型化取属性/实体与 CDATA/序列化往返保真/错误路径。
