# b64.c 0.1.0 适配笔记

## 编译环境
- 构建系统: 上游为 Makefile（仅测试目标）+ CMakeLists（共享库、无安装规则）；配方采用直接 clang 编译静态库
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (OHOS aarch64 工具链)
- 状态: built（conan-verify 八道门禁通过，尚未经 CI upload）

## 编译步骤
1. `init-build b64.c 0.1.0 --url=https://github.com/jwerle/b64.c`（tarball 经 codeload 官方 CDN 获取，SHA-256 d35c5db8…）
2. 上游库编译：`clang -std=c99 -Wall -fPIC -O2 -c encode.c decode.c buffer.c` + `ar rcs libb64c.a`
3. 上游测试：`make test`（依赖 deps/ok = jwerle/libok 0.5.0 开发依赖，vender 到 worktree 后运行）→ 8/8 通过（TAP 1..8）
4. `make test USE_CUSTOM_MALLOC=true` 变体 → 修复守卫后 8/8 通过
5. conan-init → 重写 conanfile.py（静态库、R26/R33 合规）→ conan-verify 八道门禁全部 PASS
6. 鸿蒙专项测试（64K/128K 缓冲边界、decode_ex 长度、往返一致性）9 项断言 PASS
7. 消费者用例（业务上层模拟，仅用公开 API）编译链接运行 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 平台到 github.com 主域不可达 | 官方源经 codeload.github.com（GitHub 官方 CDN）下载，SHA-256 一致；conandata 保留官方 URL，CI 自动镜像 fallback |
| 2 | 上游测试编译失败 | tarball 不含 deps/ok（gitignored dev 依赖）；libok master 的 ok() 宏要求字面量 format，test.c 传变量 | fetch jwerle/libok 0.5.0（format 作为 printf 参数版本）作为上游测试依赖；该依赖不进入配方 |
| 3 | USE_CUSTOM_MALLOC 变体编译失败 | Makefile 用 -Db64_malloc=custom_malloc 替换标识符，但 buffer.c extern 守卫 #ifdef b64_USE_CUSTOM_MALLOC 永不触发 → clang 隐式声明 error | 最小补丁：守卫改为 `defined(b64_USE_CUSTOM_MALLOC) || defined(b64_malloc)`，默认构建不受影响 |
| 4 | test_package/conanfile.py 类名非法 | conan-init 模板按包名生成 `class B64.CTestConan`（含点号，Python 语法错误） | 改为 `class B64CTestConan` |

## 源码修改
- `buffer.c`：extern 守卫增加 `defined(b64_malloc)` / `defined(b64_realloc)` 条件（补丁 0001，仅影响自定义分配器变体）

## 依赖版本
- libok 0.5.0（仅上游测试构建期开发依赖，不进配方）
- 运行时依赖：无（纯 libc）

## 验证结果
```bash
# 上游测试 8/8
make test && ./test           # → 1..8 全部 ok
make test USE_CUSTOM_MALLOC=true && ./test  # → 1..8 全部 ok（补丁后）
# Conan 八道门禁
ohc-run.py conan-verify b64.c 0.1.0   # G0-G4 + L2/L4/L5 全部 PASS
# 鸿蒙专项测试
./reports/logs/ohos-test      # → OHOS_TEST_RESULT: PASS
# 消费者用例
./reports/logs/consumer-test  # → CONSUMER_TEST_RESULT: PASS
```

## 注意事項
- 库名/静态库文件名 `libb64c.a`（上游 CMake 工程名 b64c）；系统无同名库，默认静态交付（R26）
- 非 CLI 库，无 commands.json
---

**编译结束**: 2026-09-20 21:37
**最终状态**: built
