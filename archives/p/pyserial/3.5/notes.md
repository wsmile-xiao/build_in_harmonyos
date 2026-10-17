# pyserial 3.5 适配笔记

## 编译环境
- 语言：Python
- 构建系统：setuptools（上游 setup.py）
- 编译日期：2026-09-08
- Conan：2.29.1
- Python：3.12.8
- 状态：built（等待 Conan/W3 验证）

## 源码与校验
- 官方源码：`https://github.com/pyserial/pyserial/releases/download/v3.5/pyserial-3.5.tar.gz`
- SHA256：`3c77e014170dfffbd816e6ffc205e9842efb10be9f58ec16d3e8675b4925cddb`
- 语言预检：`--lang python` 通过，检测为 python，setuptools manifest，59 个 Python 源文件。

## 配方策略
- 使用 Conan `package_type = "python-require"`，并清除 package_id，实现 noarch 纯 Python 包。
- 复制 `serial` 包到 `lib/python/site-packages`。
- 提供 `pyserial-miniterm` 与 `pyserial-ports` 两个真实命令行入口。
- 无 Conan 运行时依赖。

## 上游测试
命令：
```bash
python3 test/run_all_tests.py
```

实测结果：`Ran 61 tests in 27.382s`，53 通过，5 跳过，3 失败（53 + 5 + 3 = 61）。
失败均来自 `test_pty.py`：当前设备对 PTY 从设备执行 TIOCMBIS 调制解调器 ioctl 返回 `PermissionError: [Errno 13] Permission denied`；不是 Python 导入、构建或核心 loopback API 失败。其余上游模块均已执行。
完整日志：`reports/upstream-test.log`。

## 消费者测试
- 文件：`test_package/test_pyserial_consumer.py`
- 实测：1/1 通过。
- 覆盖：`serial.VERSION`、`serial.serial_for_url("loop://")`、真实写入/读取回环、URL 对象属性。

## 源码修改
无。适配仅新增 Conan 配方、消费者测试和归档元数据。
---

**编译结束**: 2026-09-08 13:20
**最终状态**: built
