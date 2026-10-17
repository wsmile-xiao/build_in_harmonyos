# libsee for OpenHarmony

## 软件信息

| 项目 | 值 |
|---|---|
| 名称 | libsee |
| 版本 | 1.1.0 |
| 上游 | https://github.com/ashvardanian/LibSee |
| 构建系统 | CMake |
| 语言 | C |
| 许可证 | Apache-2.0 |
| 依赖 | 无 |

## 适配说明

上游是单文件 LD_PRELOAD 库，CMake 不提供 `install()`、测试或头文件。Conan recipe 使用 CMake 构建并手工复制真实产物 `libsee.so`，不伪造头文件；强制 `-fPIC -fno-builtin -nostdlib -nostartfiles -shared`。

## 验证

```sh
python3 -m py_compile archives/l/libsee/1.1.0/conanfile.py
python3 -m py_compile archives/l/libsee/1.1.0/test_package/conanfile.py
```

`test_package` 是真实 C 消费者：通过 `dlopen`/`dlsym` 加载 `libsee.so` 并调用 `libsee_print_size` 检查输出。Conan OHOS 包构建和该消费者测试通过，版本状态为 `built`；独立的本机 `LD_PRELOAD=.../libsee.so true` 探索退出 139（SIGSEGV），未验证发布。

原始探索命令与输出见 [`1.1.0/reports/exploration.txt`](1.1.0/reports/exploration.txt)。
