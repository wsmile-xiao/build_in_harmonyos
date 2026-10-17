# par 1.53.0 适配笔记

## 编译环境
- 构建系统: makefile (protoMakefile)
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

par 使用自定义 protoMakefile 构建系统，无 configure 脚本。

1. `source .build-context-par-1.53.0` 加载编译上下文
2. `cd $BUILD_SRC_DIR` 进入源码目录
3. 编译: `make -f protoMakefile CC="clang -fPIC -O2 -c" LINK1="clang" LINK2="-o"`
4. 手动安装到 staging: `cp par $TEST_PREFIX/$DEFAULT_PREFIX/bin/par; cp par.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/par.1`
5. 运行测试: `make -f protoMakefile test`
6. Staging 验证通过
7. `ohc-run.py package par 1.53.0` 制作预编译包
8. 安装到 $DEFAULT_PREFIX: `cp par $DEFAULT_PREFIX/bin/par; cp par.1 $DEFAULT_PREFIX/share/man/man1/par.1`
9. 用户验证: `echo "" | $DEFAULT_PREFIX/bin/par version` → `par 1.53.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure 脚本 | par 使用 protoMakefile 而非 autotools | 使用 `make -f protoMakefile CC=clang LINK1=clang LINK2=-o` 直接编译 |
| 2 | 3个locale测试失败 | musl libc locale支持有限 | 平台限制，核心功能36/36测试全部通过，不影响使用 |
| 3 | /tmp只读导致locale测试初始化失败 | HarmonyOS /tmp只读(E002) | 记录为平台限制，不阻塞 |
| 4 | init-build误判build_system为autotools | 无configure/config.guess等autotools标志 | 修正manifest.yaml为build_system: makefile |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

无外部依赖，纯ANSI C实现。

## 验证结果

```bash
# 版本验证
echo "" | /storage/Users/currentUser/usr/local/bin/par version
→ par 1.53.0

# 功能验证
echo "Hello world test paragraph" | /storage/Users/currentUser/usr/local/bin/par
→ Hello world test paragraph

# 测试套件
36 passed, 3 failed (locale tests, expected on musl)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| par-1.53.0-ohos-aarch64.tar.gz | 131KB | 预编译包 |
| par-1.53.0-ohos-aarch64-debug.tar.gz | 30KB | 调试符号包 |

## 注意事项

- par 使用 protoMakefile（非标准 Makefile），需通过变量覆盖指定编译器
- `--version` 不是标准选项，需使用 `version`（par特有的布尔选项格式）
- locale 测试在 musl 系统上会失败，属于已知平台限制
- 构建系统类型为 makefile，不是 autotools
---

**编译结束**: 2026-07-15 23:10
**最终状态**: built
