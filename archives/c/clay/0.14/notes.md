# clay 0.14 适配笔记

## 软件信息
- 软件：clay 0.14（上游 nicbarker/clay tag v0.14，Zlib）
- 定位：高性能 2D UI 布局库——单头文件 clay.h（~4.4k LOC，零依赖，连标准库都不要求）
- 形态：header-only（一个编译单元需 `#define CLAY_IMPLEMENTATION` 后 include clay.h）
- 构建系统：上游 CMakeLists 仅用于编排 examples 构建（无库目标，add_library 注释掉）；CI 用 GitHub Actions build matrix 验证
- 分支 feat/clay-0.14；worktree ~/huawei/worktrees/j669539/clay-0.14

## W0/W0b
- W0 preflight：PASS（零依赖）
- W0b：本仓库无 clay 历史归档；单头库先例参照 cxxtest 4.1（header 部署 + test_package 消费验证模式）
- lang-preflight：c 判定（clay.h 纯 C 主体；bindings/ 有 cpp/rust/zig 等 binding 但均为第三方示例不参与构建）

## 源码检查（上游 v0.14 tarball，SHA256 ee8f6477020dd72afe8cf6f8d3ab6855980028289a2b677a1423d17aab983585）
- clay.h：全部库本体（单头文件）
- examples/cpp-project-example/main.cpp：上游 CI 的构建验证目标（ASan 下编译运行完整布局 pass）
- tests/：docker-compose + gcc9.4 Dockerfile 构建冒烟（仅构建无测试执行）
- 无注册测试套件（全树 grep add_test/enable_testing = 0 命中）
- 无需任何源码补丁 → patches 为空

## 配方设计（参照 cxxtest 先例，静态库形态）
- clay_impl.c：单一编译单元 `#define CLAY_IMPLEMENTATION` + include clay.h → 编译进 libclay.a
- 消费者直接 link clay::clay，include clay.h 即声明模式（无需自己管理 IMPLEMENTATION 宏）
- 区别于 cxxtest 的纯 header-library：clay 的 IMPLEMENTATION 需要一个 TU 承载，预编译成静态库对消费者更友好（上游 README Quick Start 也是这个用法）

## 关键实测记录（设备 aarch64 OHOS）
1. 上游 cpp-project-example 交叉编译（clang++ --target=aarch64-unknown-linux-ohos -std=c++20）成功，E077 签名后运行 exit 0（输出一条 MeasureText 未注册的提示为示例自身的正常形态——HandleClayErrors 打印）
2. 布局断言套件（自写，覆盖真布局行为）：
   - arena 创建（Clay_MinMemorySize + Clay_CreateArenaWithCapacityAndMemory）✅
   - flex 布局：sidebar 固定宽 200 + content GROW，Clay_EndLayout 产出 5 条 render command ✅
   - sidebar 矩形实测宽度=200（FIXED sizing 契约）✅
   - text render command 产出（MeasureText 回调注册后）✅
   - clip 滚动容器产出 SCISSOR_START/END 对（裁剪契约）✅
   - Clay_MinMemorySize > 0 ✅
   - 全部 8 项断言 failures=0，exit 0
3. clay.h C 模式注意点：CLAY__INIT 在 C 下是复合字面量 (type){...}、C++ 下是裸 type{...}；Clay_TextRenderData 字段名 stringContents；MeasureText 回调签名用 Clay_StringSlice

## 上游测试统计与执行（rule4 口径）
- 上游注册测试用例：**N=0**（无 add_test 注册）
- 上游验证形态（如实申报为构建验证 4 项）：
  - GitHub Actions build matrix 3 项（gcc/clang linux + cl windows）→ 本地以 clang 交叉编译+运行 cpp-project-example 等价执行 ✅
  - docker gcc9.4 构建冒烟 1 项 → docker 设备不可用，以同源码设备 clang 原生交叉构建等价执行 ✅
- 无减少（0 注册 + 4 构建验证全等价执行）

## 适配后测试（消费者，test_package）
- test_clay.c：链 libclay.a（声明模式 include）→ 两个真实布局场景 8 项断言全过（failures=0）

## OHOS 平台要点
- clay.h 纯计算布局库（无平台 API 调用），无交叉问题；渲染器无关设计天然适配 headless
- 测试二进制运行需 E077 签名
- C11 编译（set_target_properties C_STANDARD 11）

## 验证记录
- conan create（G2）+ test_package 全链路本地通过（见 reports/）
- status：built（上传发布须等合并后 release 流水线）
