# coal 3.0.3 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libcoal.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

依赖 eigen + boost + octomap + qhull + assimp 五者。两个关键点：① cmake/ 是 git submodule(jrl-cmakemodules)，GitHub archive 不含子模块，故 conandata 单列一条源、按该 tag 记录的 submodule commit 精确固定；② 依赖自己的 cmake config 会做嵌套 find_package，被 ohos.toolchain 的 FIND_ROOT_PATH_MODE_PACKAGE=ONLY 挡住，而 -D 压不住 toolchain 的普通 set()，须用 CMAKE_PROJECT_TOP_LEVEL_INCLUDES。test_package 8 条碰撞/距离数值断言（闭式解对账）。
