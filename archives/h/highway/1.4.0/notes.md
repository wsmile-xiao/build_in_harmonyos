# highway 1.4.0 适配笔记

本次任务分支：feat/highway-1.4.0。团队：诶，云朵。日期：2026-10-13。

## 配置与依赖

core、contrib、测试支持共享库；保留原生 SIMD 和动态 dispatch。当前受测配置没有外部包依赖；编译器/CMake/签名工具属于设备工具链，不伪装成库依赖。官方源码及 SHA-256 由 conandata.yml 固定，任务本地源码覆盖仍校验同一 SHA-256。

## 适配与恢复

使用上游维护的 standalone 测试运行器，不引入外部 GTest，未禁用 tests/contrib/SIMD。PRE_TEST 仅延迟发现；hwy_list_targets POST_BUILD 仍运行，因此 cmake.build() 和测试阶段分别提供计算得出的构建树运行库。构建完成后签名，再发现并完整运行 861 个条目。

## 检测环境问题

设备只有 llvm-readelf，没有 CI 脚本调用的 readelf。先前扫描因空输出误报 SONAME；保存原失败/误报记录，不修改平台 ci 脚本。新独立事务仅在任务 PATH 增加调用已验证 llvm-readelf 的私有 readelf 桥接器，最终 L5=pass。桥接器不作为配方提交、不写系统目录、不代表比赛 worker 环境已修复。

## 最终验证

原生 HarmonyOS PC，aarch64，clang 15.0.4，Conan 2.29.1，CMake 4.1.2；上游 861/861，安装包消费者通过。详见 reports/test-report.md。

知识草稿：knowledge/drafts/E15139-draft-A715.kv + .md。只读复用现有 SONAME/运行库/签名知识，新草稿说明本次独立实质增量。

当前阶段为本地真机适配完成。聚合 finish/Pre-PR/Issue/PR/平台 Review/比赛 worker CI 尚未完成；不得将原生 W3 PASS 写成已合并或已发布。
---

**编译结束**: 2026-10-13 15:36
**最终状态**: built
