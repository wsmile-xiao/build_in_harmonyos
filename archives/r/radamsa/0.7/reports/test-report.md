# test-report — radamsa 0.7

- 构建引用：`radamsa/0.7@ohpcd/stable`（ohos-aarch64 profile，clang 15 / armv8）
- 采信轮 HEAD：`3c3e3538faa529abbaa71548f8f367ef743fb0fd`（分支 `feat/radamsa-0.7`；
  此后仅 reports/** 文档级更新）
- 验证形态：干净轮 conan create（清缓存后 DB 两表为空，构建标志
  `RUN: make`/`Calling build()` 计数 > 0），上游测试在验证构建树内执行；
  两轮独立干净轮安装产物 sha256 一致（bin/radamsa `ee70f744…8645b`）

## 上游测试统计（同一统计单位：runner 逐用例结果）

来源：上游 `tests/run`（Makefile `test:` 目标）遍历 `tests/*.sh`，每项最多
重试 40 次（模糊断言是概率性的）。取数命令见 `reports/upstream-tests.md`。

| 项 | 数 | 说明 |
|---|---|---|
| TOTAL | 28 | `tests/*.sh` glob 注册数（框架注册数口径） |
| PASS | 28 | |
| FAIL | 0 | |
| SKIP / NOT_RUN | 0 | 未注册分母逐项归因：`*.sh_` 停用 3（blank 模板、tcp-client/tcp-serve 网络守护形态）、`tests/pcapng/` 2 项未接入 runner、`tests/benchmark` 性能基准 1 项非断言 |

通过率：**28/28（100%）**。

## test_package / 鸿蒙特有测试（不计入上游分母，单列）

来源：conan create 的 test_package 段（`reports/conan-create.log:154-162`），
执行 `test_package/test.sh` 8 项断言，`assertions_run=8`，全部 `ok`。

| 项 | 数 | 说明 |
|---|---|---|
| 断言总数 | 8 | 4 项上游功能复验 + 4 项鸿蒙特有 |
| PASS | 8 | |
| FAIL | 0 | |

鸿蒙特有断言（rule12）：
1. `stdout>/dev/null` 完成不挂起（OHOS 字符设备 poll/select 永不报告 POLLOUT
   的直接回归路径，验证 patches/0001）；
2. `stdout>/dev/zero` 完成不挂起（字符设备族覆盖）；
3. `-o` 输出到 HMFS 可写目录且 `%n` 序号展开生成 3 个文件；
4. stdin 管道输入 + stdout 管道输出（`cat | radamsa | 下游` 形态）。

## 非 PASS 项技术原因

无（上游与适配后均无非 PASS 项）。

## 平台缺陷与补丁对照（摘要）

上游原版二进制在本平台 `> /dev/null` 即永久挂起（对照证据：
`reports/conan-verify-supplement.md` 附录）；patches/0001 在 Owl VM `do_poll`
写集加 `fstat` 预检（S_ISCHR 直接判可写），修复后上游 28/28 与
test_package 8/8 全通过。
