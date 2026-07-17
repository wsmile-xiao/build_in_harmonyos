# qpdf 12.3.2 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libqpdf.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
pending — 配方已生成（glfw 式 cmake + zlib/jpeg 依赖接线），待真机验证
