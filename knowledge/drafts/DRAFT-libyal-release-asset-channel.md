# DRAFT: libyal 系库源码通道取舍——codeload git tarball 不可用时的 release 资产方案

- 状态：草稿（待知识库主编审核）
- 关联 PR：!15170（libvmdk 20260714）、!15182（libewf 20260924，草稿载体）
- 适用范围：libyal 系全部取证格式库（20+ 件）及任何"任务卡给定 git tarball 但上游有
  release 资产流水线"的同构场景

## 问题形态

任务卡给定 codeload git tarball，实际是裸源码快照：无 configure 预生成产物、无 vendored
子库。三条死路：synclibs.sh 构建期 clone（违反 never pulls unregistered dependencies）；
手工 bootstrap（CI worker 无 automake）；主仓预缓存（产物膨胀）。

## 方案

探测上游 release 资产三通道（alpha/experimental/裸名），取自包含快照，sha256 锁定。
channel 名不可先验必须逐一探测——libvmdk 是 alpha、libewf 是 experimental，无一规律。

## 与既有条目的差异

- DRAFT-6053（libmrss automake NEWS missing）：单文件缺失 touch 补齐——本条是整个
  通道级替换（vendored 子库集合+configure 全缺），非单点补文件。
- DRAFT-11327（rnnoise dist 丢头文件）：上游双通道都缺→改 CMakeLists——本条是
  git 通道缺而 release 通道全，通道取舍即可零 patch 解决。

## 验证

双件 conan create RC=0 + test_package 全绿（26/26 上游 autotest + 66 消费者检查点）。
