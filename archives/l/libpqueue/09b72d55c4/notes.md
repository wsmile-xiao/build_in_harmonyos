# libpqueue 09b72d55c4 适配笔记

## 编译环境
- 构建系统: custom（上游无 configure/Makefile/CMakeLists，单文件直编）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / llvm-ar
- 状态: published

## 编译步骤

libpqueue 是 Apache HTTP Server 项目使用的通用优先队列（二叉堆）实现，
上游 tarball 仅含 `src/pqueue.c`、`src/pqueue.h` 和两个样例，无构建系统。

1. 源码下载（官方 GitHub archive，commit 09b72d55c482f8c9e4d8416d24978ee73ce4b420）：
   `curl -o libpqueue-09b72d55c4.tar.gz https://codeload.github.com/vy/libpqueue/tar.gz/09b72d55c482f8c9e4d8416d24978ee73ce4b420`
   sha256 = 94b37f3fcd98fc115f66006970b87f4a2c6af22f91044574e89b9a9047beb8fb
2. 手动编译（Adapt 阶段）：
   ```bash
   clang -Wall -O2 -fPIC -c pqueue.c -o pqueue.o
   llvm-ar rcs libpqueue.a pqueue.o
   ```
3. 上游样例编译并运行：sample.c / sample-multiattr.c 均编译成功、运行通过（2/2）。
4. conan-init 生成骨架后改写 conanfile.py 为直编模式（build() 用
   `tools.build:compiler_executables` 取 CC/AR，`-fPIC` 编 `.o`，`ar rcs` 打包，
   可选 `-shared` 出 .so），package() 安装 libpqueue.a/.so 与 pqueue.h。
5. test_package 真实调用 pqueue_init/insert/peek/change_priority/pop 并断言
   size、peek、pop 顺序（5 项期望值），本地编译运行通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载超时 | github.com 主域在当前执行端网络不可达（E017 类） | 改用 GitHub 官方归档主机 codeload.github.com 预置 tarball 后重跑 init-build |
| 2 | 生成的 autotools 配方与上游不符 | 上游无 configure 脚本，模板按 URL 猜测为 autotools | 重写 conanfile.py 为直编模式（custom 构建系统） |
| 3 | /tmp 只读 | HarmonyOS 平台 /tmp 为只读（E002） | 测试输出改用 $HOME/tmp |

## 依赖版本

无第三方依赖（纯 C 单文件库）。

## 验证结果

```bash
# 上游样例（适配阶段实际运行）
$ ./sample
peek: 6 [-6]
pop: 8 [-1]
pop: 7 [-2]
pop: 6 [-6]
pop: 5 [-5]
pop: 4 [-4]
exit=0

$ ./sample-multiattr
initial: pri: 2/1/0/3 ... [pop] 顺序符合预期
exit=0

# test_package 消费者测试（本地编译运行）
$ clang -Wall -O2 -I src test.c src/pqueue.c -o test_libpqueue && ./test_libpqueue
peek: 6 [-6]
pop: 8 [-1]
pop: 7 [-2]
pop: 6 [-6]
pop: 5 [-5]
pop: 4 [-4]
test libpqueue 09b72d55c4: OK
exit=0
```

上游测试统计：2/2 通过（sample、sample-multiattr，均为上游自带可执行样例，
无 make check/ctest 注册——上游无测试框架）。

## 软件级归档

软件级 `archives/l/libpqueue/manifest.yaml`/README 无既有归档（首版适配），
版本级 manifest.yaml/notes.md 本次创建。

## 注意事项

- 上游唯一正式发布标识为 commit 09b72d55c4（"Add FUNDING.yml."，2022-04-20，
  官方仓库 https://github.com/vy/libpqueue，无 release tag），版本号采用该短哈希。
- 库类型（package_type=library），产物仅 .a/.so + 头文件，无可执行文件，无需 commands.json（R38）。
- 无平台相关代码（纯 C 二叉堆），无需 OHOS 平台宏或补丁。
---

**编译结束**: 2026-09-28 11:13
**最终状态**: built
