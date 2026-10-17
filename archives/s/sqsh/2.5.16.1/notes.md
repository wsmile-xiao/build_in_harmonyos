# sqsh 2.5.16.1 适配笔记

## 编译环境
- 构建系统: autotools（configure 正常执行；编译/链接绕过 make，直接 clang）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（/data/service/hnp/bin，OHOS SDK Native LLVM）
- 状态: built

## 编译步骤

1. `conan create archives/s/sqsh/2.5.16.1 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing`
2. 配方内部流程（ohc-build.sh，在源码目录内执行）：
   - `bash configure --without-readline --without-x --without-motif --without-static --without-debug --with-sybase=<freetds-prefix>`
   - sed 修补 `src/config.h`：undef `HAVE_READLINE_H`/`HAVE_READLINE`/`HAVE_RL_COMPLETION_MATCHES`/`HAVE_SHADOW_H`
   - 逐文件 clang 编译 src/ 下全部 .c（cmd_* / dsp_* / var_* / sqsh_* / sqsh_main），`-O3 -std=gnu89 -Wno-deprecated-non-prototype -DSYB_LP64` + FreeTDS CS_* 常量
   - sqsh_parser 子目录编出 sqsh_parser.a
   - 链接：`clang ... -l:libct.a -ldl -lm sqsh_parser/sqsh_parser.a -o sqsh`（静态嵌入 CT-lib）
3. `package()` 拷贝 `src/sqsh` → `bin/sqsh`，附 COPYING 许可证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 运行 sqsh 报 `Error loading shared library libct.so` + 41 个 CT-lib 符号 relocation 失败（exit 127） | FreeTDS 只发布 libct.a 静态库；配方曾用 `ar x` + `clang -shared` 拼装 libct.so 动态链接，但 OHOS musl 运行时无法定位该 .so | 链接改为 `-l:libct.a` 静态嵌入，产物自包含 |
| 2 | make 驱动编译时 clang 子进程静默死亡（Error 1/2 无输出） | make jobserver 经 posix_spawn 派生子进程在 OHOS 上不可靠 | 绕过 make，bash 循环逐文件 clang 编译 + 手工链接 |
| 3 | 上游 configure 探测 readline/shadow 头误开 | OHOS sysroot 头文件布局差异 | config.h 中 undef 对应宏，禁用 readline/shadow |
| 4 | `sqsh --help` 打印 usage 后退出码 255，`self.run()` 视为失败 | sqsh 约定 usage 退出状态为 255（不连服务器） | test_package 改为 `--help 2>&1 \| grep -q 'Use: sqsh'`，校验输出内容而非退出码 |

## 源码修改

- `config/config.guess`、`config/config.sub`：替换为 OHOS-aware 版本（source() 阶段覆盖 autoconf/ 下同名文件），无 diff 补丁（conandata.yml `patches: []`）。

## 依赖版本

- freetds/1.4.23（ohpcd remote，仅静态库 libct.a / libsybdb.a）

## 验证结果

```bash
$ conan create archives/s/sqsh/2.5.16.1 -pr:h ci/conan/profiles/ohos-aarch64 \
    -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# RC=0
# sqsh/2.5.16.1 (test package): sqsh binary verified: ELF arm64
# RUN: .../p/bin/sqsh --help 2>&1 | grep -q 'Use: sqsh'   → 通过（完整 usage 输出）
```

- conan-verify：G0–G4 全 PASS（reports/conan-verify-report.md，Verdict: PASS）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/sqsh | ~1.2 MB | arm64 ELF 可执行（CT-lib 静态嵌入，无运行时 .so 依赖） |

## 注意事项

- sqsh 为交互式 SQL shell，离线消费者测试只能验证 usage 路径；连库行为需真实 Sybase/MSSQL 服务端。
- 产物自包含（静态链接 CT-lib），无需随包分发 libct.so。
- 若将来 FreeTDS 发布共享库，可评估改回动态链接以缩小体积。
---

**编译结束**: 2026-09-30 22:09
**最终状态**: built
