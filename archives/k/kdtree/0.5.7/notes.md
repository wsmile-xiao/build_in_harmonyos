# kdtree 0.5.7 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 configure + Makefile.in）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 / llvm-ar / llvm-ranlib
- 状态: published

## 编译步骤

```bash
# 源码：官方 GitHub tag v0.5.7（codeload），SHA-256 已核验
#   15ba4d423bf85bf3247fbf256648f273b5792bcb87711b9fc121c0beffba66af
./configure --prefix=$DEFAULT_PREFIX --disable-debug   # 手写 configure，静默忽略未知选项
make -j1                                               # 产出 libkdtree.a + libkdtree.so.0.1
make install DESTDIR=$TEST_PREFIX                      # staging 隔离安装
make -n check                                          # 无 check 目标（上游无测试框架）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 100% 满（4.4G/4.4G），curl 写盘失败 | 平台临时分区耗尽 | 按技能规则在 /data/storage/el2/base/cache 创建 0700 专用临时目录，设置 TMPDIR/TMP/TEMP 后恢复下载与构建 |
| 2 | Savannah/waterlan 官方下载地址 404 | 上游镜像失效 | 改用 GitHub 官方 codeload 源 `https://codeload.github.com/jtsiomb/kdtree/tar.gz/refs/tags/v0.5.7`，核验 SHA-256 通过 |
| 3 | worktree 首次创建被超时打断，`locked initializing` | 工具调用超时中断 checkout | `git worktree unlock` + `--force` 清理半创建 worktree，从可审计 main(1326b73f4e) 重建唯一专用 worktree |
| 4 | git status 出现 libXext/libxext 大小写目录碰撞 | 仓库既有两目录 + HMDFS 大小写不敏感（core.ignorecase=true） | 确认属仓库既有基线噪声（主 worktree 同样存在），与 kdtree 无关，不进入 commit/PR |

## 源码修改

无补丁（kdtree 为纯 ANSI C，上游 Makefile 可直接在 OHOS clang 下编译）。

## 依赖版本

无第三方依赖（纯 C，仅链接系统 libpthread/libm）。

## 上游测试枚举台账（全量）

枚举方法：解压官方 tag 源码后 `find . -type f \( -iname '*test*' -o -iname '*check*' -o -iname '*bench*' -o -iname '*fixture*' \)` 全目录扫描 + `grep -rn 'check_PROGRAMS\|TESTS\|add_test\|ctest'` 注册扫描。

| 条目 | 路径 | 分类 | 是否独立上游用例 | 是否实际运行 | 结果 |
|------|------|------|------------------|--------------|------|
| test.c | examples/test.c | 样例（示例程序，含 assert 自校验） | 否（样例不计独立用例） | 是 | 通过（exit 0，100/1000 向量插入+范围查询） |
| test2.c | examples/test2.c | 样例（扩展测试程序，含 assert） | 否（样例不计独立用例） | 是 | 通过（exit 0，100 点范围查询 67 结果） |
| 构建目标 libkdtree.a/.so | 根目录 | 构建目标 | 否 | 是 | 通过（make 成功） |
| 测试框架注册 | 全目录 | 无 ctest/autotools/GTest 注册，无 check 目标 | 无 | - | 无 |

**统计口径（双口径台账）**：
- source_declared_total（官方 tag 源码可复制枚举的独立测试用例数）：**0**（上游无测试框架，无独立 TEST_CASE/注册项）
- configured_executable_total（当前 OHOS 配置实例化/注册的可执行用例数）：**0**
- executed_passed_total：**0**（独立用例口径）
- 失败数：0；未运行/未实例化数：0
- 样例程序实际运行验证：examples/test.c 与 examples/test2.c 均编译并运行通过（2/2），作为样例级验证证据，不计入上游独立用例分母

说明：全量通过率分母为发现的独立上游用例总数 0，因此独立用例口径为 0/0；上游确无独立测试框架与用例，已附清点证据（全目录文件清单 + 注册扫描）。样例程序 2/2 实际运行通过，无未运行或硬阻塞项。

## 验证结果

```bash
# 库构建
make -j1            # exit 0，产出 libkdtree.a / libkdtree.so.0.1
# 样例程序（上游示例）编译运行
clang -std=c89 -pedantic -Wall -g -I. -o test_example examples/test.c libkdtree.a && ./test_example 1000   # exit 0
clang -std=c89 -pedantic -Wall -g -I. -o test2_example examples/test2.c libkdtree.a -lm && ./test2_example 100  # exit 0
# staging 安装验证
make install DESTDIR=$TEST_PREFIX   # exit 0，头文件+静态/动态库齐全
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 项目配方（R33 显式传 CC/AR/RANLIB，R9 -j1） |
| conandata.yml | 官方 codeload 源 + SHA-256 |
| test_package/ | CMakeLists.txt + conanfile.py + test.c + MANIFEST.yml |
| manifest.yaml | version/software/sha256/build_system 已填 |

## 注意事项

- kdtree 为纯 C 单文件库，无测试框架，双口径统计中独立用例为 0，样例程序作为验证证据。
- 配方静态构建（default shared=False）只构建 libkdtree.a，避免与系统动态库冲突（R26 语义下纯库无系统同名库，静态默认即可）。
---

**编译结束**: 2026-09-21 00:51
**最终状态**: built
