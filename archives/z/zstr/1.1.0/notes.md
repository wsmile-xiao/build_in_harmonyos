# zstr 1.1.0 — 适配笔记

## 来源核验（官方资料确认）

- 官方仓库：https://github.com/mateidavid/zstr
- 正式标签：`v1.1.0`，Release 发布时间 2025-10-20
- 许可证：MIT（LICENSE，1118 字节）
- 源码归档：`https://github.com/mateidavid/zstr/archive/refs/tags/v1.1.0.tar.gz`
- SHA-256：`b77ef8b961233a100a34da588962a95a2f3b00c9b2dc0ea67100b36ec72128af`
  （下载官方归档实测，归档 13130 字节；conandata.yml 沿用该值）
- 参考配方：conan-center `zstr`（header-only + `zlib/[>=1.2.11 <2]`，
  `package_id` clear，`check_min_cppstd 11`），本仓按 Conan 2.x + 仓内
  zlib 精确引用改写。

## 结构

- 头文件：`src/zstr.hpp`（约 22KB）+ `src/strict_fstream.hpp`（约 7.8KB），C++11。
- `CMakeLists.txt` 只声明 `INTERFACE` 目标 `zstr::zstr`，
  无 `install()` 规则，不走 cmake 安装，直接复制头文件。
- `examples/`：`zc.cpp` / `zpipe.cpp` / `ztxtpipe.cpp`（压缩工具示例）
  + `test-strict_fstream.cpp`（手动诊断程序）+ `Makefile`（含 `test` 目标）。
- 无 `tests/` / `test/` 目录，无 `enable_testing` / `add_test` / gtest / pytest。

## 上游测试审计（R51 三步法之清点）

- 测试面 = `examples/Makefile` 的 `test` 目标，CI 入口为 `.travis.yml`
  的 `make -C examples test`。逐行清点 `diff -q` 断言：
  - `ztxtpipe` 5 个（明文直通、gzip、gzip-9、拼接 gzip、拼接压缩流解压）；
  - `zpipe` 6 个（同上 5 项语义 + 单层剥离 `gzip(gzip(f))==gzip(f)`）；
  - `zc` 18 个（stdin / `-` / 文件参数 / `-c` 压缩组合往返）。
  - 合计 29 个断言（conanfile.py 中 `UPSTREAM_CHECK_TOTAL = 29` 硬门禁，
    harness 实际执行数漂移即报错，防静默跳过）。
- `test-strict_fstream.cpp` 不是测试套件：需手动传文件参数，
  只打印各类 open 组合行为，无断言、无通过/失败判定，故不纳入计数，
  在此说明（不是“暂未接入”，而是审计后排除）。
- 运行方式：配方 `build()` 先以工具链编译器 + Conan zlib 编译出三个
  真实工具，再用可移植 Python harness 执行全部 29 检查（相同二进制、
  相同输入、相同 diff 语义）。可移植原因如实记录：
  - 上游 Makefile 硬编码 `g++ -lz`（系统 zlib），OHOS 无系统 zlib 头；
  - `test` 目标依赖 bash 进程替换 `<(...)` 与 `gzip`/`zcat` 命令行，
    OHOS 真机不保证具备；harness 用字节比较替代进程替换，
    用 Python gzip 承担 `gzip`/`zcat` 角色（gzip 格式标准，等价）。
  - 唯一行为差：单层剥离检查把两侧 gzip mtime 固定为 0；
    上游写法依赖两次 `gzip` 落在同一秒，属竞态写法，固定后断言更稳，
    测的仍是 zstr 的单层解压行为。
- 证伪设计：harness 逐项比较字节 + 返回码，桩二进制（空输出/
  错误输出/非零退出）必 FAIL；`UPSTREAM_CHECK_TOTAL` 防 harness
  被改小后“全过”。（待真机用实际日志复核，见下节。）

## 依赖

- `zlib/1.3.1`（仓内 zziplib/ixwebsocket 等同款精确引用）。
  `package_info()` 以 `cpp_info.requires = ["zlib::zlib"]` 透传，
  `cmake_file_name`/`cmake_target_name` 为 `zstr`/`zstr::zstr`。
- 无补丁（`patches: {}`）。无平台宏。纯库，无 `commands.json`。

## 本轮状态

- 首轮工作树：配方 + test_package（含 4 断言消费者测试 `test_zstr.cpp`）
  + 双 manifest + PR 正文草稿已就绪，均未提交。
- 待 HMBS 真机预检：`conan create` 全量日志（含 29 上游检查明细、
  `HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT` 两行标记）
  回来后，如实回填 PR 正文通过率；若 harness 在真机水土不服
  （编译器键名、zlib 路径形态等），按预检日志修复。
