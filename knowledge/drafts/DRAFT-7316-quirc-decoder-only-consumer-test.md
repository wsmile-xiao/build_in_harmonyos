# DRAFT-7316：纯解码库（decoder-only）的消费者测试构造——自研对端编码器 + 标准向量校验 + round-trip 定位

> Contributor: wanderlust_0823（GLM-14） | Status: Draft | Updated: 2026-09-12
> Source: 任务 7316 quirc 1.2 适配（分支 feat/quirc-1.2，PR 编号创建后回填）

## 背景

quirc 1.2 是 QR 码解码库（lib/ 只有解码路径，无任何编码器）。上游 tests/ 目录只有
3 个**手动**工具（qrtest / inspect / inspect_opencv），Makefile 无 check 目标、源码
无任何测试框架注册宏（`TEST(`/`add_test(` 均为 0），仓库不自带测试图片。按测试四维
账本口径：N_static=0、N_registered=0——"上游无自动化测试"属实，但赛道二硬门禁仍要求
至少 1 个真实消费者程序调用公开 API 并断言行为。矛盾点在于：断言解码行为需要"已知答案"
的输入图像，而上游无处获得。

## 症状（可复现）

- `grep -rE "TEST\(|add_test\(" .` 为空；Makefile 无 check/test 目标；
- tests/qrtest.c 是手动工具：吃目录里的图片文件，没有内置输入，仓库不带任何 .png/.jpg；
- 直接拿随机图片喂解码器只能断言"解不出码"，不能证明"解码正确"。

## 根因

decode-only 库没有对端（encoder），无法像编解码器（codec）库那样用 round-trip 生成
测试素材；"已知答案"（known-answer test）输入必须外造。

## 方案（三步，可跨库复用）

1. **自研最小对端编码器**：按规范实现恰好覆盖被测库支持子集的生成器。本次用 Python
   实现 QR byte 模式编码器（版本选择、掩码、RS 纠错），输出 PNG 与原始矩阵。
2. **编码器先独立校验，再联调**：RS 纠错码字与 ISO/IEC 18004 附录 I 的标准向量逐位
   比对（伽罗瓦域运算与生成多项式是易错点）。**没有这一步的 round-trip 会双错抵消**：
   自研编码器错 + 解码器对 → 解码失败（好发现）；两者错法互补 → 假通过（坏，且极难察觉）。
3. **设备端 round-trip 定位 + 已知答案固化**：编码器输出喂解码器，失败时逐层 dump
   （finder 图案极性、format 信息位序、模式指示位），三轮定位出 3 处自研编码器 bug；
   通过后把最终矩阵（21×21，v1/L/mask0）以常量数组内嵌进 test_package/test.c，
   断言 payload、版本、ECC level、mask、数据类型与模块网格共 18 项——测试不再依赖
   PNG 解码与外部素材，纯内存输入。

## 真实验证

- 上游工具 qrtest（依赖 libjpeg-turbo/3.0.4 + libpng/1.6.39 + zlib/1.3.1，制品仓
  预编译包直接命中）：3 张自研 PNG 设备实跑输出
  `3 files, 3 codes, 3 decoded (0 failures), 100%`；
- 消费者测试 test_quirc：18/18 断言通过（内嵌矩阵 → 公开 API
  quirc_new/quirc_resize/quirc_identify/quirc_decode；另含全白图 0 码行为测试）；
- `conan create` 全量验证通过（W3 exit_code=0）。

## 适用范围与边界

- 适用：一切只带"解码/解析"方向的库（QR、条码、文档与容器格式解析、协议解析）的
  消费者测试构造；QR/条码类可直接复用本策略与编码器骨架。
- 反例/边界：
  - 上游自带官方测试向量的库**必须优先用官方向量**，本策略仅在无素材时使用；
  - 自研编码器必须先过独立权威标准向量（ISO/IEC 18004 附录 I 或等价来源）再联调，
    防止双错抵消的假通过；
  - 上游本就有编码器的库直接 round-trip 即可，不必内嵌矩阵。
- 解除条件：上游未来版本附带测试素材或编码器时，本策略降级为补充手段。

## 与现有知识库的查重

knowledge/graph/index.tsv（766 条）按 decode / encoder / test vectors / consumer test /
QR 检索：命中 E252（消费者测试必须真实调用 API 与生命周期）、E239（test_package 断言
聚合模式）、E292（gtest/CTest 迁移）——均为"怎么断言"，无一条覆盖"被测素材从哪来"的
decode-only 构造策略。本条新增价值：无对端库的 known-answer 输入构造方法论，以及
"编码器先独立校验防双错抵消"的边界规则。
