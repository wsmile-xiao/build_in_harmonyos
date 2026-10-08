# randomio 1.4 适配笔记

## 软件简介

randomio（Dean Gaudet，MIT）是一个多线程随机磁盘 I/O 微基准：N 个线程对
指定文件/设备做随机偏移的 pread/pwrite（可调写比例与 fsync 比例），周期性
输出 iops 与 min/avg/max/sdev 延迟（毫秒）表。

- 上游：`http://www.arctic.org/~dean/randomio/`（作者站点直接分发
  `randomio-1.4.tar.bz2`，无版本控制 tag；FreeBSD ports
  benchmarks/randomio 同版本，distinfo SHA256 一致）
- 语言：C（单文件 randomio.c，9.7KB）
- 许可证：MIT（只存在于源码头注释第 7–25 行，无独立 LICENSE 文件）
- 产物：单个命令行可执行文件 `randomio`
- issue：待补（按当前轮次指示跳过）

## 依赖（W0）

- 运行时/构建依赖：仅 C 标准库（musl）+ pthread + libm（musl 并入 libc），
  无第三方 Conan 依赖。
- 运行时强依赖：文件系统需支持 O_DIRECT（ext4/f2fs 支持）。
- **W0 结论**：依赖数 0，全部满足，无需拆分依赖适配。

## 构建系统分析（W1）

- **类型**：纯 C + 手写 GNU makefile（111 字节），无 configure/autotools。
- **无 install 目标、无 check/test 目标**，源码树仅 5 个文件
  （randomio.c / Makefile / README / Changelog / .cvsignore），无任何测试。
- makefile：`CFLAGS=-O2 -g -Wall -pthread -std=gnu99`，
  `LDFLAGS=-pthread -lm`，默认规则 `randomio: randomio.o` 走 make 隐式
  编译/链接规则（用 `$(CC)` 与 `$(LDFLAGS)`）。
- **musl/OHOS 兼容性**：
  - musl `<fcntl.h>` 定义 O_DIRECT，`#error "Needs O_DIRECT"` 守卫可通过；
  - `<termios.h>`/`<sys/ioctl.h>`/pthread/drand48/pread/pwrite/fsync 均为
    musl 提供，无需补丁；
  - `_FILE_OFFSET_BITS 64` 保证 64 位 off_t；TIOCGWINSZ 行数探测有
    `#ifdef` 守卫，非 tty 输出时固定 24 行表头周期。
- **上游已知缺陷（不打补丁，保持源码忠实）**：EINTR 重试判断写错
  （`while (rc < 0 && rc == EINTR)`，应为 `errno == EINTR`），仅影响罕见
  信号中断路径，不影响编译与基准结果。

## 适配点

1. **CC 覆盖**：`make CC=<ohos-clang> -j1`；编译器来自
   `tools.build:compiler_executables`（R33）；CFLAGS/LDFLAGS 保留上游默认。
2. **无 conandata.yml**：源码 URL/SHA256 直接写进 conanfile.py 的
   `source()`（`get(..., strip_root=True)`），规避 CI 预下载脚本对
   conandata.yml 处理路径引用未初始化 BUILD_DIR 的基础设施缺陷（同
   xmodem/0.4.7.1 策略）。本包无补丁，不依赖 `self.conan_data`。
3. **许可证提取**：package() 从 randomio.c 确定性截取第 7–25 行（版权声明
   + MIT 授权文本）生成 `licenses/LICENSE`。
4. **ELF 签名**：OHOS 要求可执行文件签名，package() 内（仅 os==OHOS）执行
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign
   -selfSign 1`；工具不存在时跳过并告警（与 tinymembench/0.4、simh/3.8.1
   相同策略，由 CI/消费端补签）。
5. **无上游测试**：验证 = 完整构建 + test_package 消费端断言：
   - usage 探测（无参数 → usage 行、含 512 字节对齐说明、退出码非 0，
     确定性、不依赖存储）；
   - 端到端基准（预分配 8MiB 普通文件，`randomio <file> 2 1.0 0 4096 1 1`：
     2 线程、100% 写、0 fsync、4KiB I/O、1s 采样 1 次，~2 秒自动退出），
     断言表头两行、至少一条数值数据行、stderr 无 open/thrasher 运行错误、
     退出码 0。
6. **运行时长**：test_package 约 2–5 秒，非重任务。

## 风险点

- **O_DIRECT 运行时依赖**：若真机文件系统不支持 O_DIRECT，`open()` 报
  `Invalid argument`，端到端基准失败。此时正确处置是记录失败并评估是否
  补丁降级（如加非 O_DIRECT 回退），不得静默跳过。
- 上游 URL 为 http（非 https），Conan `get()` 带 SHA256 强校验，完整性
  由摘要保证；CI 镜像改写逻辑若重写该 URL 需关注日志。

## 验证结果

### 本机前置验证（W4，2026-10-03，本机 = Windows + DevEco OHOS SDK clang 15.0.4 + Conan 2.29.1 + Python 3.12）

- **SHA256 复核**：下载
  `http://www.arctic.org/~dean/randomio/randomio-1.4.tar.bz2`
  → `384da98a…386f`，与 FreeBSD ports distinfo 一致；tarball 单一根目录
  `randomio-1.4/`（strip_root=True）。
- **语言预检（R47）**：`ohc-run.py lang-preflight` → task=cpp, detected=c，
  匹配继续。
- **预编译风险扫描**：`ohc-run.py prescan` → 危险调用 False，构建系统 make。
- **静态门禁**：G0e 根目录白名单 / JC 垃圾文件 / L0 批量检查（ast、
  MANIFEST、test() 方法、无硬编码 remote、run() 无 shell 变量）全过。
- **补丁可应用性**：0001 对原始源码树 `git apply --check` 通过；应用后
  OHOS clang 交叉编译 **0 警告**，链接 exit=0。
- **无补丁基线**：同样交叉编译 0 警告（编译本身不需要补丁，补丁只解决
  真机运行时 O_DIRECT 问题）。
- **工具口径分歧（已归因）**：本地 `ohc-run.py conan-verify` G1 要求
  conandata.yml/export_sources；真实 CI 门禁（build_and_test.sh L0f）仅在
  conandata.yml 存在时校验，无 export_sources 硬要求。本包按知识指南
  §5.2 策略不使用 conandata.yml（规避 CI 预下载 BUILD_DIR 缺陷），与
  xmodem/0.4.7.1 先例一致。本机无 make，conan create 完整流程由真机
  runner 执行（与 tinymembench/0.4 相同）。
- **真机 r2 附加实测**：HMDFS 对新文件 `open(O_CREAT|O_DIRECT)` 成功、对
  已存在文件 `open(O_DIRECT)` 返回 EINVAL（独立复现两次）→ 产生补丁 0001。

### 真机 shadow CI（W5）

见下方迭代记录表；最终结果以最后一轮为准。

## 真机 shadow CI 迭代记录（job: randomio-1.4-20261004）

| 项 | r1 | r2 | r3 | r4 | r5（最终） |
|---|---|---|---|---|---|
| 排队 wait_seconds | ~120 | ~120 | ~60 | ~60 | **0** |
| exit code | 1 | 1 | 1 | 1 | **0** |
| 门禁 | L1 fail | G0/KC/JC pass，L1 fail | 同 r2 | 同 r2 | **G0/KC/JC/L0/L1/L4/L5 全 pass，L2 skip（预期），100%** |
| 报错原文 | `AttributeError: 'RandomioConan' object has no attribute '_source_url'` | test 输出 `FAIL: exited with 1` + `open: Invalid argument` | `ImportError: cannot import name 'apply' from 'conan.tools.files'` | `TypeError: patch() got multiple values for argument 'base_path'` | — |
| 根因 | Conan 2 不把模块级全局变量映射到 self，`self._source_url` 取值失败 | HMDFS 对已存在文件的 open(O_DIRECT) 返回 EINVAL（实测新文件 O_CREAT+O_DIRECT 成功、已存在文件失败；独立复现两次） | 设备端 conan 无 `apply` 导出，正确 API 为 `patch()` | 设备 conan 签名为 `(conanfile, base_path=None, patch_file=None,…)`，位置参数撞到 base_path | — |
| 解法 | source() 直接引用模块级 `_source_url`/`_source_sha256` | 补丁 0001：EINVAL 时回退缓冲 IO（镜像上游 __APPLE__ 分支），告警写 stderr | 改用 `conan.tools.files.patch()`，路径取 `export_sources_folder` | 全关键字调用（本机 conan 2.29.1 `inspect.signature` 复核后上真机） | — |

### r5 最终结果（真机 shadow CI，排队 0s）

```
G0_RESULT=pass          KC_RESULT=pass        JC_RESULT=pass: empty
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed（usage 探测 OK + 端到端基准 OK）
L2_RESULT=skip: randomio version/help failed
                        （预期降级：main 无 --version/--help 解析，同 tinymembench）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)   exit code 0
```

真机手动复跑装好的二进制（8MiB 文件、2 线程、纯写、4KiB、1s×1）：
写 ~248,422 iops，stderr 按设计输出 `warning: O_DIRECT unsupported …
falling back to buffered I/O`（HMDFS 不支持对已存在文件的 O_DIRECT，
回退后延迟含页缓存，已记录为平台限制）。

上游测试：0（上游无测试套件，MANIFEST.yml 附清点证据）；test_package
消费断言 8/8 通过。

另观察：`build_and_test.sh:164: permission denied: git`——设备无 git 的脚本内调用，r2 未阻塞任何门禁（G0/KC/JC/L0 相关结果均 pass）。

## 下一步（真机/shadow CI 命令）

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job randomio-1.4 \
  --package archives/r/randomio/1.4 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/randomio-1.4/run-conan-heavy.sh"
```

重点记录：L0–L5 结果、test_package usage 探测与端到端基准输出（真实
iops/延迟数字）、binary-sign-tool 签名后能否 exec、真机文件系统是否支持
O_DIRECT。
