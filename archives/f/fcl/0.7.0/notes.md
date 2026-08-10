# fcl 0.7.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libfcl.so 等 1 个库，供链接与 dlopen。

## 关键适配
- **补丁 `fcl-0001-libm-optional-on-musl.patch`：让链接 libm 变成可选。**
  musl 把数学函数并入了 libc，sysroot 里只有静态 `libm.a`、没有 `libm.so`，
  所以上游 `find_library(M_LIBRARY m)` 必然落空。上游随后无条件把该变量塞进
  `set(CCD_LIBRARIES "${CCD_LIBRARY}" "${M_LIBRARY}")`，NOTFOUND 一直拖到
  generate 阶段才炸：`variables are used in this project, but they are set to NOTFOUND`。

  补丁改成「找到才链、找不到就跳过」。**不填假值**是有意的：试过
  `-DM_LIBRARY=m` 与 `=-lm` 两种填法，CMake 都把它当**文件依赖**，
  报 `No rule to make target`。设备实测带不带 `-lm` 都能链接并运行 ——
  这个链接项在 musl 上本就多余。

  对 glibc 平台无影响：那里 `find_library` 找得到，走的还是原来的分支。

  ⚠️ 报错里出现的是**下游 fcl 的变量名**（`M_LIBRARY`/`CCD_LIBRARIES`），
  很容易误判成 libccd 那个包的问题 —— 根因其实在 fcl 自己的 CMakeLists。

## 状态
built（真机 conan create + test_package 通过）
