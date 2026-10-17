# bali-phy

## 简介
bali-phy（BAli-Phy）是一个基于贝叶斯框架联合估计多序列比对（MSA）与系统发育树的
统计推断工具，通过马尔可夫链蒙特卡洛（MCMC）对“比对 + 树 + 进化模型”的联合后验进行采样。

## 功能概述
- 联合估计序列比对与系统发育树（MCMC，含 5d 分析等长用例）
- 插入-删除与替换模型（SModel）建模
- 命令行工具集：bali-phy 主程序 + 44 个配套工具（cairo 可用时含 draw-tree 共 45 个）
- Haskell 风格计算语言子集（mcon/computation 模块），支持用户自定义模块

## OHOS 适配
- 构建系统：Meson（>=1.1，C++20）；OHOS/aarch64 + musl + clang 15 实测可用
- Boost 头文件缺口：ohpcd boost 配方未安装 json/uuid/convert/rational/compute 头，
  配方在 patches/boost-extra 内逐字 vendor（183 个头文件，BSL-1.0，无 OHOS/musl 修改）
- 跨模块 RTTI：dlopen 的 builtins 模块需要主程序导出 Box<T> typeinfo（补丁 0003，
  对应上游 issue #23 的 aarch64 问题）
- libc++15 缺 std::string/vector/variant 的 <=>（LLVM17+ 才有）：补丁 0002 提供等价实现
- ELF 签名：29 个 builtins 共享模块经 OHOS binary-sign-tool selfSign 签名后方可 dlopen
- 运行期自包含：boost/fmt 共享库随包拷贝，可执行文件设 $ORIGIN/../lib DT_RUNPATH

## 依赖
- boost/1.91.0.1.1（program_options/random/system/chrono 编译件；json/uuid/convert/rational/compute 头 vendor）
- eigen/3.4.1
- fmt/8.1.1（shared）
- cereal/1.3.2
- 可选：range-v3（使用上游 internal 副本）、cairo（draw-tree 不建）、MPI（关闭）

## 参考
- 官网: https://www.bali-phy.org/
- 源码: https://github.com/bredelings/BAli-Phy
