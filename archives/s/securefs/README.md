# securefs

基于 FUSE 的透明认证加密文件系统：每个文件落盘前做 AES-GCM 内容加密，
密钥由 Argon2id 派生；提供 `securefs` 命令行工具（`mount` / `create` / `chpass` /
`fix` / `info` / `version`）。

* 上游仓库：https://github.com/netheril96/securefs
* 许可证：MIT

## 版本索引

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| [0.13.1](0.13.1/) | published | cmake | 首次适配鸿蒙 PC（OHOS aarch64）；7 处平台阻塞，5 条补丁 + 1 处链接期补桩 |

## 鸿蒙 PC 适配要点（0.13.1）

* 依赖 `libfuse/2.9.9`（FUSE 2.x，静态 `libfuse.a`；上游固定 `-DFUSE_USE_VERSION=28`）。
* 上游 release archive 缺三枚子模块源码（`cryptopp`/`argon2`/`utf8proc`），按固定
  commit + sha256 在 `conandata.yml` 的 `submodules:` 中补齐。
* 平台阻塞与处置（详见 [0.13.1/notes.md](0.13.1/notes.md)）：

| 阻塞 | 处置 |
|------|------|
| `cmake_minimum_required(VERSION 3.0)` 被 CMake 4.x 硬拒 | `patches/0001` |
| OHOS 下 `if(UNIX)` 为假 → 误走 Windows/WinFsp 分支 + 写死 `/usr/local` 探测 | `patches/0002` |
| 静态 `libfuse.a` 下 `dlsym` 版本探测返回 NULL（启动崩溃） | `patches/0003` |
| `cryptopp-cmake` 把带空格的 `CMAKE_CXX_FLAGS` 当单参数转发 | `patches/0004` |
| libc++ 对 Catch2 RNG 触发 `static_assert` | `patches/0005` |
| OHOS libc 无 `pthread_cancel`/`pthread_setcancelstate`（链接期 undefined symbol） | `stubs/stub-pthread.c`（no-op 补桩） |

## 知识库拓展交付物（通用部分）

`0.13.1/tools/` 是**一类共性问题**的通用处置套件（不针对单个库）：上游「源码发布包 +
自有构建脚本」在 Conan 交叉编译 + CMake 4.x + 干净 CI 环境下必然失败的三类可静态预检风险。

| 产出物 | 文件 |
|--------|------|
| 检测脚本（只读，文本 / `--json`，退出码 0/1/2） | `0.13.1/tools/prescan_risks.py` |
| 处理策略（现象 → 根因 → 识别 → 处置 → 验证） | `0.13.1/tools/STRATEGY.md` |
| 复现脚本（干净环境复现三类风险 + 处置验证） | `0.13.1/tools/reproduce.sh` |
| 样例演示库 | 本包 0.13.1（三类风险全中，处置逐一落地） |

```sh
# 适配前扫描任意源码目录
python3 0.13.1/tools/prescan_risks.py /path/to/upstream-src
python3 0.13.1/tools/prescan_risks.py /path/to/upstream-src --json

# 复现 + 处置验证（日志落文件，规避 SIGPIPE）
sh 0.13.1/tools/reproduce.sh --src /path/to/upstream-src
```

## 构建与验证

```sh
conan create archives/s/securefs/0.13.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

测试结果（上游 `ctest` 3/3、消费者用例 5/5）见
[0.13.1/reports/test-report.md](0.13.1/reports/test-report.md)。
