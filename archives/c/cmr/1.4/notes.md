# cmr 1.4 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libcmr.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 让上游 Find*.cmake 生效：GMP（CMakeDeps 的 config 会抢走 find_package）

## 状态
generated —— **recipe 已生成，真机尚未验证**。
跑通 `conan create <recipe> -pr ohos-native` 并确认 test_package 通过后，
把本行与 manifest.yaml 的 status 一并改成 built，并在下方补真机证据。
