# tofrodos 2.0.0 适配笔记

## 编译环境
- 构建系统: makefile (makefile.gcc)
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 源码使用自定义 Makefile (`makefile.gcc`)，无 configure 脚本，不支持标准 autotools/cmake
2. 构建命令:
   ```bash
   cd ~/tmp/builds/tofrodos-2.0.0.work
   make -f makefile.gcc CC=clang LD=clang CDEBUG="-fPIC -O2" LDEBUG="" FROMDOS=fromdos all
   ```
3. DESTDIR 安装 (R20): 手动 install 到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1
   install -m 755 fromdos $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   cd $TEST_PREFIX/$DEFAULT_PREFIX/bin && rm -f todos && ln -s fromdos todos
   install -m 644 fromdos.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/
   cd $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1 && rm -f todos.1 && ln -s fromdos.1 todos.1
   ```
4. 软链接创建遵循 R5 铁律: `rm -f && ln -s` 避免 HMDFS 的 `ln -sf` 问题
5. 打包: `ohc-run.py package tofrodos 2.0.0` (R19，禁止手动打包)
6. 本地安装: `make install` (不带 DESTDIR，模拟用户部署到 `$DEFAULT_PREFIX`)
7. 收尾: `ohc-run.py finish tofrodos 2.0.0 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 自动编译无法检测构建系统 (unknown_build_system HANDOFF) | tofrodos 使用 makefile.gcc 而非标准 autotools/cmake | 手动编译: `make -f makefile.gcc CC=clang LD=clang` |
| 2 | `/tmp` 不可写 (E002) | 鸿蒙平台限制，/tmp 为只读文件系统 | 使用 `$TMPDIR` 替代所有 `/tmp` 路径 |
| 3 | runtests.sh 无法完整运行 | 需要 sudo 和 getent，平台不支持 | 手动逐项功能验证，22项测试全部通过 |
| 4 | G0 clean-verify 失败 | 脚本构造 make 命令格式错误 (`make -j1 make -f makefile.gcc`) | 手动构建验证通过，非实际编译缺陷 |
| 5 | tests/crlf/ 参考数据 CRLF 行尾被去除 | init-build 步骤自动去除所有文件 CRLF 行尾 | 使用 `.orig` 目录原始参考数据进行测试比对 |
| 6 | manifest.yaml 缺少 build_system 字段 | init-build 默认设为 autotools | 修正为 `system: makefile`, 添加 `build_system: makefile` |

## 对话记录

### 对话1: 构建系统检测失败
- 触发: `ohc-run.py build` 输出 HANDOFF (EXIT_REASON: unknown_build_system)
- 分析: 源码无 configure/CMakeLists.txt，使用 makefile.gcc
- 决策: 切换到模式B手动编译，使用 `make -f makefile.gcc CC=clang LD=clang`
- 结果: 编译成功，所有 .c 文件编译为 .o，链接为 fromdos

### 对话2: DESTDIR 安装
- 触发: tofrodos Makefile 不支持标准 DESTDIR 模式
- 分析: Makefile 的 install 目标使用硬编码路径 (BINDIR=/usr/bin)
- 决策: 手动 install + 使用 `$TEST_PREFIX/$DEFAULT_PREFIX` 组合路径 (R20)
- 结果: 安装到 staging 目录正确

### 对话 #3: 测试参考数据失真
- 触发: 批量转换测试中 diff 比对失败
- 分析: hexdump 发现 `.work/tests/crlf/` 的文件行尾为 0a(LF)，应为 0d 0a(CRLF)
- 决策: 使用 `.orig` 目录的原始参考文件重新测试
- 结果: 全部12项批量转换测试通过

## 源码修改

无补丁（0 个）。使用 make 变量覆盖 (CC=clang, LD=clang, CDEBUG) 完成编译，未修改任何源文件。

## 依赖版本

- 无外部依赖
- 仅动态链接 musl libc: `/lib/ld-musl-aarch64.so.1`

## 验证结果

22项测试全部通过:
- fromdos 批量转换: 6/6 PASSED
- todos 批量转换: 6/6 PASSED
- dos2unix/unix2dos 别名: 2/2 PASSED
- -b 备份功能: 2/2 PASSED
- 双重转换: 1/1 PASSED
- 管道模式: 2/2 PASSED
- 软链接转换: 1/1 PASSED
- 错误处理: 2/2 PASSED
- --version/--help: 2/2 PASSED

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tofrodos-2.0.0-ohos-aarch64.tar.gz | 174KB | 预编译包 (ELF签名+strip+RPATH) |
| tofrodos-2.0.0-ohos-aarch64-debug.tar.gz | 52KB | 调试符号包 |

## 注意事项

1. 构建系统为自定义 Makefile，不支持 configure，需使用 `make -f makefile.gcc` 并覆盖 CC/LD 变量
2. 软链接创建需使用 `rm -f && ln -s` 而非 `ln -sf`（HMDFS 限制，R5）
3. 测试参考数据 (tests/crlf/) 在解压时 CRLF 行尾被去除，需使用 `.orig` 目录进行比对
4. G0 clean-verify 脚本对 makefile 项目生成 make 命令格式有误，需手动验证构建

---

**编译结束**: 2026-06-10
**最终状态**: published