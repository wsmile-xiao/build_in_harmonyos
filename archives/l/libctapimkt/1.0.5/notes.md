# libctapimkt 1.0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-23
- 编译器: clang (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 依赖发布检查（W0/R36）：无外部运行时依赖，自包含（仅 POSIX termios + dlfcn）
# 本地编译验证（W3）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# conan-verify 8 门禁全 PASS（G0-G4 + L2/L4/L5）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libctapimkt 1.0.5
```

适配修复均在 `conanfile.py build()` 内动态完成：
- `config.guess/config.sub` 补 OHOS triplet 识别（`_patch_config_guess_sub()`，E007 同类）
- `configure` 内 `umask 077` → `umask 022`（hmfs 目录不可写，E046 同类）
- `Makefile.am` 移除多余 `-lusb`（mktlin 实际不使用 libusb API）、`-lctapimkt` 改 `libctapimkt.la` 修构建顺序
- `mktlin.c` `antwort()` 补返回值（clang 15 `-Wreturn-type` error）
- `package()` 手工 copy `ctapimkt/ctapi.h` → `include/ctapimkt/`（上游 Makefile.am 无 include_HEADERS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 aarch64-unknown-linux-ohos | 上游 2013 版 config.guess 无 OHOS triplet | conanfile.py `_patch_config_guess_sub()` 动态补 OHOS 分支（E007） |
| 2 | configure 在 hmfs 上 mktemp/umask 077 目录不可写 | hmfs 目录权限/umask 限制 | `sed -i 's/umask 077/umask 022/g' configure`（E046） |
| 3 | 上游 tarball 缺可用 Makefile.in | 上游未发布 autotools 生成文件 | tool_requires automake/autoconf/libtool，build() 内重建 |
| 4 | 链接未使用的 -lusb 且 -lctapimkt 裸链接无顺序依赖 | Makefile.am 构建顺序缺陷 | build() 内 sed 移除 -lusb，`-lctapimkt` → `libctapimkt.la` |
| 5 | mktlin.c antwort() 声明 int 但无返回值 | clang 15 -Wreturn-type 视为 error | `sed -i 's/^return;[[:space:]]*$/return 0;/' mktlin.c` |
| 6 | 头文件 ctapi.h 不随 make install 安装 | 上游 Makefile.am 无 include_HEADERS | package() 手工 copy 到 include/ctapimkt/ |

## 源码修改

- `patches/` 为空，无静态补丁文件（所有修复动态内联于 conanfile.py build()）

## 依赖版本

- 运行时依赖：无（自包含）
- tool_requires：automake/1.18, autoconf/2.72, libtool/2.5.4

## 测试情况（R34 实质测试）

- **上游测试**：无（上游 2010 年代码无 tests/ 目录，`make check` 无测试目标，已清点源码目录确认，upstream N=0）
- **适配后新增测试**：1 个消费者视角单元测试（test_package/test.c，3 断言）
  - 链接 `-lctapimkt` 并实际调用 `CT_init(0,0)` / `CT_data(ctn,&dad,&sad,5,command,&lenr,response)` / `CT_close(ctn)`
  - 无读卡器硬件时校验返回已定义 CT-API 错误码且进程不崩溃（不依赖硬件，CI 可复现）
- **鸿蒙特有测试**：1（无硬件下验证 CT-API 可链接可调用）
- 通过率：上游 0/0（不适用），新增 1/1（100%），test_package Passed 1/1

## 验证结果

```bash
# W3 本地编译验证（exit_code=0）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# conan-verify 8 门禁全 PASS
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libctapimkt 1.0.5
# test_package 实质测试（R34）：Passed 1/1，3 断言通过
```

## 注意事项

- `mktlin` 需串口读卡器硬件，CI 中无法进行端到端读卡测试（已用 CT-API 符号链接+调用测试替代）
- 配置选项 `--enable-static --disable-shared`（静态库，R26 安全策略）

---

**编译结束**: 2026-09-23 18:20
**最终状态**: built
