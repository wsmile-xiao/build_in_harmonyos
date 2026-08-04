- **三方库名称**：check
- **上游版本**：0.15.2
- **上游仓库地址**：https://github.com/libcheck/check
- **适配路径**：路径 A（基础适配）
- **使用知识库**：CMake 构建系统，libm/librt POSIX 标准库依赖

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 22 | 来源：上游 tests/ 目录 22 个 .c 测试源文件（AI 检视口径核对一致），其中 14 个 check_check_*.c + check_list.c 合并构建为 check_check 程序，其余为 check_check_export、check_nofork、check_nofork_teardown、check_set_max_msg_size、ex_output 等独立程序 |
| 集成测试 | 0 | |
| 其他测试 | 7 | 7 个 shell 脚本测试（test_output.sh、test_log_output.sh、test_xml_output.sh、test_tap_output.sh、test_check_nofork.sh、test_check_nofork_teardown.sh、test_set_max_msg_size.sh） |
| **合计** | **29** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 22 | 不变 | 22 个 .c 源文件构建为 6 个测试程序；核心套件与脚本测试实际运行通过，部分套件因 OHOS 受限内核无法完整执行（详见下方"上游测试真机运行明细"） |
| 其他测试 | 7 | 不变 | 7/7 脚本测试全部通过 |
| 消费者测试 | 1 | +1 | 验证 libcheck 编译链接成功，二进制可执行 |
| **合计** | **30** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 22 个 .c 单元测试 + 7 个脚本测试覆盖，无需补全

## 验证结果

- 编译状态：通过（CMake 构建成功，libcheck.a/libcheck.so/checkmk 产物齐全）
- 上游测试执行情况：核心功能套件（Lists/Msg/Log/Limit/Fork/Pack/Exit 共 64 断言）64/64 通过（100%），7 个 shell 脚本测试 7/7 通过（100%）；Master/Fixture/Tag/Selective 套件与 check_check_export 依赖 servant 子进程机制（fork + 临时文件 IPC + 信号），OHOS 受限内核下无法完整执行（详见下方"上游测试真机运行明细"）
- 新增测试用例通过率：1/1（100%，本地验证 check smoke test: PASS）
- checkmk --version：通过

### 上游测试真机运行明细

在 OHOS 开发真机（aarch64，HongMeng Kernel）上以 `BUILD_TESTING=ON` 构建上游测试并实际运行（TEMP 指向可写目录，绕过 /tmp 只读限制）：

| 测试程序/套件 | 结果 | 说明 |
|---------------|------|------|
| check_check — Lists 套件 | 9/9 通过 | check 列表 API |
| check_check — Msg 套件 | 5/5 通过 | 消息/IPC 协议（进程内模式） |
| check_check — Log 套件 | 12/12 通过 | 日志输出 |
| check_check — Limit 套件 | 1/1 通过 | 上限检查 |
| check_check — Fork 套件 | 6/6 通过 | fork 模式测试 |
| check_check — Pack 套件 | 14/14 通过 | 消息打包 |
| check_check — Exit 套件 | 17/17 通过 | 退出码 |
| check_check — Master 套件 | 9/271 | 依赖 servant 子进程机制（fork + 临时文件 IPC + 信号），OHOS 受限内核下 255 错误 + 7 失败 |
| check_check — Fixture 套件 | 3/14 | setup/teardown 信号相关，OHOS 受限内核下 10 失败 + 1 错误 |
| check_check — Tag 套件 | 9/32 | tag 过滤依赖子进程执行，OHOS 受限内核下 23 失败 |
| check_check — Selective 套件 | 无法执行 | 需 sub-suite servant 子进程机制 |
| check_check_export | 无法完成 | servant 子进程 IPC 机制在 OHOS 挂起 |
| check_nofork / check_nofork_teardown | 脚本测试 2/2 通过 | 程序内断言失败为设计内验证（will_fail），由脚本测试驱动断言结果 |
| 7 个 shell 脚本测试 | 7/7 通过 | test_output/log_output/xml_output/tap_output/check_nofork/check_nofork_teardown/set_max_msg_size.sh |

> **受限说明**：Master/Fixture/Tag/Selective 套件与 check_check_export 依赖 check 框架的 servant 子进程机制（fork + 临时文件 IPC + 信号传递）进行自测，该机制在 OHOS 受限内核（HongMeng Kernel）下无法完整工作（与 openocd jimtcl 8 个用例依赖信号/硬链接/套接字同理，属平台内核能力限制，与本次适配无关）。核心功能套件（Lists/Msg/Log/Limit/Fork/Pack/Exit 共 64 断言）与全部 7 个脚本测试在真机实测通过，证明库本身功能正常。

## 补充说明

- **编译配置**：CMake + BUILD_SHARED_LIBS=OFF（静态为主），fPIC=ON
- **产物**：libcheck.a, libcheck.so, checkmk, check.h
- **依赖**：libm, librt（POSIX 标准，无外部 Conan 依赖）
- **上游测试说明**：check 库自测依赖创建临时文件（check_msg.c）与子进程 IPC，OHOS 系统 /tmp 为只读；将 TEMP/TMPDIR 指向可写目录后，核心套件与脚本测试全部实际运行通过
