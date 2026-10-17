# 测试包辅助代码的运行时导入闭包

## 问题现象

平台 CI 的主配方已经完成编译、安装和打包，但在进入 `test_package` 的
构建分支后报 `NameError: name 'glob' is not defined`。这类错误只在测试包
真正执行辅助发现逻辑时出现，不能由主包构建成功推断测试包完整。

## 根因

Python 辅助函数使用了标准库模块，却没有在文件顶部导入。静态语法检查和
主配方构建不会执行该函数；CI 运行测试包时才进入分支并失败。

## 修复步骤

1. 以 CI 使用的同一 `conan create`、host/build profile 和环境执行
   `test_package`，定位到实际抛错的 helper，而不是把失败归类为目标编译器
   或被测库问题。
2. 为 helper 显式添加缺失的标准库导入，并运行 `python -m py_compile`。
3. 重跑完整测试包构建和消费者执行；只有消费者入口实际完成，才能声明
   Conan 验证通过。

## 验证方式

Squirrel 3.2 的 CI #39707 已完成主库编译，但在
`_configure_ohos_linker_runtime()` 调用 `glob.glob` 时失败。补充
`import glob` 后，必须重新执行本地双 profile `conan create`、目标设备
消费者和当前 HEAD 的平台 CI；旧失败不能与新候选拼接。

## 适用范围与安全边界

适用于 Conan Python 配方中按平台扫描编译器、链接器、文件或产物的测试包
辅助逻辑。它不替代目标设备、签名或平台 CI；不能通过捕获 `NameError`、跳过
测试包或只验证主库来伪造测试通过。若 helper 分支没有执行证据，状态必须
保持未验证。
