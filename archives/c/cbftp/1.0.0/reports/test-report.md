# cbftp 1.0.0 验证报告

## 环境

- OpenHarmony/HarmonyOS PC aarch64（OHOS SDK 26.0.0.18, clang 15.0.4）
- Conan 2.29.1（OHOS 适配版）
- Profile: ci/conan/profiles/ohos-aarch64

## 编译验证

- `conan-verify cbftp 1.0.0`: exit 0（G0-G4 门禁全部 PASS）
- `finish` W3 本地 CI 模拟: **PASS**（`ci/conan/build_and_test.sh`，JC/L0 门禁通过）
- 构建系统：纯 Makefile（无 configure），产物三个可执行文件：
  - `bin/cbftp`（ncurses FTP/FXP 客户端主程序）
  - `bin/datafilecat`（AES-256 数据文件解密工具）
  - `bin/datafilewrite`（AES-256 数据文件加密工具）
- 依赖：openssl/3.5.6.1.1、ncurses/6.6（宽字符）

## 上游测试情况

- **上游测试样例数：0**
- 排查过程：源码树无 `tests/` 目录、Makefile 无 `check`/`test` 目标（`make -n check` 无输出）、示例目录 `examples/` 仅为客户端脚本（cbapi.py/mirror.py 等，非常规测试）。
- 上游本身不含测试套件，故按 SKILL 要求补全同功能测试集（`test_package/test_cbftp.py`）。

## 补全测试集（test_package，5 用例）

| # | 用例 | 断言 | 结果 |
|---|------|------|------|
| 1 | 三个可执行文件存在且可执行 | 文件存在 + X_OK | PASS |
| 2 | datafilecat 明文（ASCII）数据文件直读 | 输出与输入逐字节一致 | PASS |
| 3 | datafilewrite AES-256 加密 + datafilecat 解密往返 | 解密结果与明文逐字节一致 | PASS |
| 4 | 错误口令解密不得产生明文 | 解密输出 ≠ 明文（AES 密钥调度确定性断言） | PASS |
| 5 | cbftp 主程序 ELF 启动 | ELF 加载/链接正常（无 TTY 时 ncurses 初始化失败属预期） | PASS |

- 测试用例：5，通过：5，失败：0，跳过：0（连续 5 次本地运行全过，稳定性验证）

## 附加说明

- 上游 `Crypto::decrypt()` 不检查 `EVP_DecryptFinal_ex` 返回值，错误口令解密输出随机；测试用例 4 采用确定性断言（输出 ≠ 明文）而非依赖随机返回码。
- 运行时依赖 `libc++_shared.so`，test_package 自动定位 OHOS SDK llvm lib 目录注入 LD_LIBRARY_PATH。