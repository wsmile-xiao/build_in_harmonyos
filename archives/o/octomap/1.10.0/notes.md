# octomap 1.10.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 liboctomap.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

产两个库 liboctomap + liboctomath，test_package 23 条断言两个都真实调用（八叉树占据/自由/未知三态、光线投射、二进制序列化往返；四元数与位姿复合用闭式解对账）。
