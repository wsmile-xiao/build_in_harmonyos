# GnuCOBOL 3.2 OpenHarmony/HarmonyOS 适配笔记

## 编译环境

- 目标平台: OpenHarmony/HarmonyOS PC arm64
- Conan settings: `os=OHOS`, `os.version=6.0`, `arch=armv8`
- 构建系统: Autotools
- 编译器: clang/clang++ 15.0.4
- 源码: GnuCOBOL 3.2 官方发布包
- 源码 SHA256: `3bb48af46ced4779facf41fdc2ee60e4ccb86eaa99d010b36685315df39c2ee2`
- 最终状态: `built`

## 构建配置

```text
--with-math=gmp
--with-curses=no
--with-json=no
--with-db=no
--with-xml2=no
```

GnuCOBOL 3.2 必须使用多精度数学库。本配方依赖 `gmp/6.3.0`，其静态库使用 `--with-pic` 构建，以便链接到共享 `libcob.so`。curses、JSON、Berkeley DB、XML2 均为未发布的可选依赖，因此显式禁用。

## 平台适配

| 补丁 | 问题 | 处理 |
|---|---|---|
| `0001-build_aux-config.guess.patch` | `config.guess` 不识别 HarmonyOS | 返回 `aarch64-unknown-linux-ohos` |
| `0002-build_aux-config.sub.patch` | `config.sub` 拒绝 `linux-ohos` | 接受 OHOS triplet 和 kernel/OS 组合 |
| `0003-configure.patch` | HMDFS 上 `umask 077` 临时目录不可写 | `config.status` 使用 `$TMPDIR`，不施加不兼容的 umask |
| `0004-libcob-call.c.patch` | HarmonyOS `fmemopen` 存在但写入无效且 `fclose` 返回 `EBADF` | OHOS 使用 libcob 的临时文件回退实现 |
| `0005-libcob-common.c.patch` | `/tmp` 存在但挂载为只读 | OHOS 额外检查临时目录的 `W_OK` 权限 |

HarmonyOS ELF 经 `llvm-strip` 修改后签名失效。Conan 配方在 `os=OHOS` 时设置 `STRIP=:`，使 `cobc -O2` 不自动 strip 生成的程序。需要 strip 的制品必须按 E077 流程重新签名。

上游 `configure` 的 Clang 探测提示含两个 Latin-1 `0xFC` 坏字节（`clang \xFCrototype warning`），会使严格 UTF-8 的门禁日志采集器在构建成功后崩溃。配方在应用补丁后对 `configure` 执行精确字节修复，固定校验命中数为 2，并将其改为 ASCII `clang prototype warning`。不修改 `configure.ac`，以避免触发 Autotools 重生成并覆盖 HMDFS `config.status` 补丁。

## 验证结果

最终干净构建命令：

```bash
conan create archives/g/gnucobol/3.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

结果：

- Conan 干净源码构建退出码: 0
- 上游测试: 1226 项符合预期，56 项因显式禁用的可选功能而跳过
- `libcob` 消费者 C API 测试: 通过
- `cobc --version`: 通过，报告 GnuCOBOL 3.2.0
- `cobcrun --version`: 通过，报告 GnuCOBOL 3.2.0
- 实际 COBOL 编译运行: 通过，输出 `GnuCOBOL compiler: OK`
- 先前异常测试 8、10、667、820: 修复后全部通过
- 正式 `conan-verify`: G0-G4、L2、L4、L5 全部通过
- W3 本地 CI 模拟: 通过，`.ci-result.json` 由 `FinishPipeline` 自动生成

W3 的通用 L2 扫描直接执行包内二进制且未加载 Conan `runenv`，因此对依赖同包 `libcob.so` 的 `cobc/cobcrun` 产生非阻塞警告；同一轮 test_package 在 `conanrun` 环境中运行 `cobc --version`、`cobcrun --version` 和真实 COBOL 程序均通过。L4 扫描把补丁上下文单词 `targets` 的尾部误匹配为 `gets`；检查新增补丁行确认没有引入 `gets/strcpy/sprintf/strcat`。

独立 W4 审计发现 OHOS 临时文件回退原先按完整渲染长度读取到调用者缓冲区，短缓冲区可能越界。修复后读取量限制为 `size - 1`，检查 `fseek`，按实际 `fread` 字节数写入 NUL；test_package 使用 8 字节缓冲区和尾部哨兵验证截断与边界完整性。审计同时建议恢复临时目录 mode 0700，但 HMDFS 实测 `chmod 700` 返回成功后模式仍为 2771；原 `umask 077` 会使创建者自身无法写入。因此继续使用不可预测的 `mktemp` 名称和 `$TMPDIR`，并将权限语义差异记录为平台限制。

## 交付物

| 文件 | 大小 | 说明 |
|---|---:|---|
| `bin/cobc` | 1,411,520 bytes | COBOL 编译器 |
| `bin/cobcrun` | 31,168 bytes | COBOL 模块运行器 |
| `bin/cob-config` | 4,369 bytes | libcob 编译/链接参数工具 |
| `lib/libcob.so.4.2.0` | 698,816 bytes | GnuCOBOL 运行时库 |
| `lib/gnucobol/CBL_OC_DUMP.so` | 31,104 bytes | GnuCOBOL 附加模块 |
| `include/libcob.h`、`include/libcob/*` | - | libcob 消费者头文件 |
| `share/gnucobol/*` | 45 files | 编译器配置与 copybook |

## 状态说明

本地 Conan 配方、补丁、完整测试和归档均已完成。`gmp/6.3.0` 已在本地通过完整 Conan 验证，但尚未发布到远端 `ohpcd` 制品仓。依据 R36，GnuCOBOL 当前只能标记为 `built`，不得标记为 `published`；待 GMP 合并并发布后，再执行 GnuCOBOL 发布流程。

### 对话 #1

- 目标: 将 GnuCOBOL 3.2 适配为 OpenHarmony/HarmonyOS PC arm64 命令行工具。
- 决策: 先完成硬依赖 GMP 6.3.0 的 PIC 静态配方，再构建 GnuCOBOL；其余未发布可选依赖全部显式禁用。
- 质量复核: 初版 GMP 非 PIC 制品被打回重做；GnuCOBOL 初版模板测试和元数据被打回重做；最终干净构建、1226 项上游测试及真实 COBOL 消费者测试通过。
- 阻塞: GMP 尚未发布到远端制品仓，按 R36 保持 `built` 状态。
---

## 使用知识库

### 复用的正式 E 条目（本次适配实际使用的既有知识）

| 知识条目 | 复用的适配修改 |
|---|---|
| E001 | 工具链 `cc` 缺失场景；profile 直接使用 clang（CC=clang 思路） |
| E007 | 0001/0002 补丁：`config.guess`/`config.sub` 增加 HarmonyOS/`linux-ohos` 识别 |
| E041 | mtime 对齐避免 `make` 触发 aclocal/autoconf/automake 重生成（bypass-autotools 思路） |
| E071 | 同 E041：Autotools 重生成触发与 `help2man` man page 重生成问题（只记录复用，不重复建稿） |
| E077 | `STRIP=:` 禁用自动 strip，避免破坏 HarmonyOS ELF 签名 |
| E126 | HMDFS `config.status` 临时目录限制；0003/0005 补丁的 `$TMPDIR` 与只读 `/tmp` 处理 |
| E136 | 0003 补丁：`umask 077` + SGID 导致临时目录不可写，改用 `$TMPDIR` 且不施加 umask |

### 本次新增知识草稿（路径 B 知识贡献）

| 草稿 | 说明 |
|---|---|
| `knowledge/graph/draft/E256-draft-1E7B.kv` / `.md` | HarmonyOS `fmemopen` 符号存在但运行时不可用（`fclose` EBADF），`AC_CHECK_FUNCS` 链接级检测误判，需 `AC_RUN_IFELSE` 运行时探测并回退临时文件；对应 0004/0006/0007 补丁 |

> 草稿证据：`make check` 上游 testsuite TOTAL=1282、PASS=1226、SKIP=56、FAIL=0（56 项为显式禁用可选功能的上游正常 SKIP，未计入 PASS）；0006/0007 hunk 行数修复后七补丁在全新源码树依序验证可应用。

---
**编译结束**: 2026-08-11 19:42
**最终状态**: built
