# libok 0.6.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS 工具链）
- 状态: built

## 编译步骤

```bash
# 上游无 configure，直接 make
cd $BUILD_SRC_DIR
export CC=clang CFLAGS='-fPIC -O2'
make clean && make all        # 产出 libok.a + libok.so.0.6
make test                     # 编译并运行 ok-test（test.c 单 main TAP 程序）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed(npm) 并写 env_unsupported 终态 | 检测工具 `_manifest_scan` 在检查 Makefile 之前先命中 package.json 的 `"scripts"` 键（仅发布辅助脚本 `update-clib-json`，node 实现），把 clib 生态 C 库误判为 nodejs → 与 100% C 源码统计冲突 → mixed | 按 R47 边界规则"辅助脚本不算主体"+ c↔cpp 兼容族：真实语言为 C（clib.json src=[ok.h,ok.c,Makefile]、Makefile 构建、源码 100% C），正常继续适配；误判产物在最终 result 覆盖 |
| 2 | ok-test 输出含乱码字节（hexdump 见 0x0c 0x1d 0x10 0x9e 等） | 上游 ok.h `ok_explain()` 的 `while (explaination[i] != '0')` 把 `'\0'` 误写成字符 `'0'`，多行注释解析读越界 | 上游缺陷，不影响断言与退出码（TAP 输出完整、exit 0）；记录为知识候选，不阻塞 |

## 源码修改

无补丁：上游 Makefile 直接以 clang 交叉编译通过；配方在 conanfile.py 内以
`make all CC=... CFLAGS=...` 驱动并手工 copy 头文件/库到 include/、lib/。

## 依赖版本

- 无第三方依赖（仅 libc/m 系统库）

## 验证结果

```bash
# 上游测试（test.c 单 main TAP 程序，6 个断言行：计划 1..4 的 4×ok + 计划 1..2 的 1×ok + 1×notok；
# ok_expect(4) 设置计划、ok_done()×2 输出汇总校验，均不计入断言数）
./ok-test            # TAP version 14, 1..4, 1..2, exit 0
# conan 配方验证（G0-G4 + L2/L4/L5）
ohc-run.py conan-verify libok 0.6.5   # PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | makefile 驱动配方（R33 从 toolchain conf 取 CC/CFLAGS，R26 非系统同名库） |
| conandata.yml | 官方 tag 归档 URL + sha256 10760128… |
| test_package/ | 消费者测试（调用 ok_expect/ok/ok_done 公开 API）+ MANIFEST.yml |
| 归档 | archives/l/libok/0.6.5/ |

## 注意事项

- conan-verify E017 镜像注入会在归档目录残留 conandata.yml.ghfast-bak，提交前已清理。
- 纯 Makefile 库无 configure，conan-init 模板误用 autotools，配方需手工改写为 make 驱动。
---

**编译结束**: 2026-09-20 10:55
**最终状态**: built
