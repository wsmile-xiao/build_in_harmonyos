# opustags 1.10.1 适配笔记

## 任务
- contrib 9188,分支 feat/opustags-1.10.1,认领 2026-09-25
- 上游:github fmang/opustags tag 1.10.1(C++,CMake,libogg 依赖)

## 交付物
- bin/opustags(Ogg Opus 标签读写 CLI)

## 配方机制
- CMake + C++20(OHOS clang 15 支持);零三方依赖,唯 libogg
  (pkg_check_modules 探测,制品仓 ogg/1.1.1,pkg_config_name=ogg,
  PkgConfigDeps + PKG_CONFIG_PATH 喂探测)
- 补丁 0001:libogg 1.1.1 兼容 shim(内嵌 opustags.h)——
  ogg_{stream,sync}_check(libogg 1.3.5 framing.c 原实现)+ ogg_page
  访问器 const 重载;可退化适配,语义一致
- 不做 strip;不做签名(CI 先例)

## 上游测试真机执行(2026-09-25)
- 5 个 C++ TAP 测试程序直接执行(perl prove 编排平台不可行):21 断言 19 过 2 败
- 失败归因:ogg.t 页面尺寸断言(libogg 1.1.1 封帧行为差异);
  cli.t 错误信息文本(musl getopt_long optopt 语义)
- oggdump 工具未构建:上游 1.10.1 自身缺陷(引用不存在的 ot::st::end_of_stream)
- 环境适配:消费者/上游测试运行需 LD_LIBRARY_PATH 含依赖库目录

## 消费者测试
- test_opustags_cli.sh:--help 断言 + 错误路径断言
