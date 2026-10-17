# rcheevos 12.2.1 适配笔记

## 软件信息

- 上游: <https://github.com/RetroAchievements/rcheevos>（RetroAchievements 工具集：
  成就触发器/排行榜/rich presence 运行时 + API 帮手 + ROM/光盘/zip 哈希识别）
- 版本: 12.2.1（release tag v12.2.1）
- 特征: 纯 C89、零第三方依赖（内置 MD5/AES）、库本身无构建系统（消费者直接编源码）、
  上游自带完整测试框架（test/Makefile + test_framework.h）
- 任务: ohpcd contrib-10027（开源鸿蒙PC专项积分赛，10 火种；领取时无人认领、无 PR 记录）

## 编译环境

- 真机: 10.195.180.238（隔离 job `device-b/rcheevos-kb-20260920`）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）；Conan 2.29.1
- 状态: built

## 上游测试清点（R51 第 1 步）

| 清点项 | 结果 | 依据 |
|---|---|---|
| 测试框架 | 自研（test/test_framework.h，TEST_SUITE/ASSERT 宏，run_count 计数） | 源码 |
| 套件入口 | test/test.c main 注册约 20 个 test_* 套件 | grep extern 声明 |
| 构建入口 | make -C test runtests | test/Makefile |
| ARCH 参数 | 仅 x86/x64（-m32/-m64）——aarch64 适配点 | test/Makefile |
| 断言总数 | 以真机运行输出回填 | — |

## 编译步骤

1. 官方 tag tarball 下载校验（sha256=14b3fd7d…）
2. 真机 `conan create`：build() 内 `make -C test ARCH=x64 CC=<conf 编译器> runtests`
   （上游全量测试真实运行）→ 归档 src/**.o 为 lib/librcheevos.a
3. test_package 消费者测试（8 项断言，含非法输入负例）
4. 影子 CI（提交后）

## 遇到的问题与解决方案（真机实测后回填）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建失败：fseeko/ftello 隐式声明（-Werror） | musl 将 fseeko64/ftello64 定义为无条件宏别名，严格 -std=c89 下 POSIX 声明不可见 | 补丁 0001：Makefile 追加 -D_DEFAULT_SOURCE（EVID-01） |
| 2 | 上游测试 2707/2712，5 项浮点转无符号失败 | (unsigned)f32 负值 UB：aarch64 fcvtzu 饱和为 0，MSVC/x86 参考产出补码模式 | 补丁 0002：(unsigned)(int64_t)f32 中转（EVID-02/03 → 2712/2712） |
| 3 | 上游 test/Makefile ARCH 仅 x86/x64 | 上游仅考虑 Windows/MSVC 与 x86 Linux | aarch64 传 ARCH=x64，clang 接受 -m64（实测无警告） |

## 依赖版本

- 无第三方 Conan 依赖（自包含 C89）

## 验证结果（真机实测后回填）

- 上游测试: **2712/2712 全部通过**（修复前 2707/2712，失败明细见 reports/knowledge-evidence.md）
- 消费者测试: **8/8 断言通过**（ctest 1/1 + 直接执行）
- 包产物: include/*.h + lib/librcheevos.a

## 注意事项

- PR 前缀【知识库扩展】；任务分支 feat/rcheevos-12.2.1
