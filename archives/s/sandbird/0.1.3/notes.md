# sandbird 0.1.3 适配记录

## W0/W0b/R47

- W0：配方无外部 Conan 依赖，预检通过。
- 任务语言为 C；源码主体为 C，语言预检通过。
- 官方 tarball SHA-256：`b509c5e80adf8c8e833d95ddb279a7927de9ba9ada912861c81e88b66be04687`。
- 上游没有 CMake/Make/Meson/Autotools 构建入口，按 custom recipe 处理。

## 构建与测试

- recipe 从 Conan OHOS profile 读取 C 编译器和归档器，使用 clang 以 C89 编译 `src/sandbird.c`，生成静态库 `libsandbird.a`。
- 同时编译官方 `example/hello.c` 和 `example/input.c` 作为源级 API smoke check；示例是长驻 HTTP 服务，不在配方中启动。
- test_package 真实链接 `sandbird::sandbird`，以 ephemeral port 创建 server，执行非阻塞 `sb_poll_server(..., 0)`、`sb_close_server`，并检查 `sb_error_str`。

## 路径判断

- 本任务走路径 A。此次只是无构建系统 C89 小库的本地 recipe 封装，没有形成跨库可复用的新知识条目。

## 对话记录

### 对话 #1（2026-09-03）

- 首次 G1 因验证器要求配方显式调用 `apply_conandata_patches(self)` 而失败；即使 `patches: {}` 为空也必须保留调用，补齐后 Conan verify 通过。
- finish 的通用 clean-verify 仍按 Autotools 默认探测，因无 configure 入口返回 exit 127；Conan create、test_package、W3 和 verify-build 均通过，故保留为框架通用探测限制，不伪报源码失败。
- staging 无可执行文件，记录 `verified=0 failed=0`；静态库交付物由真实 Conan package 生成。

## 验证命令

- `python3 scripts/ohc-run.py conan-verify sandbird 0.1.3`
- `python3 scripts/ohc-run.py finish sandbird 0.1.3 built`
- `python3 scripts/ohc-run.py verify-build sandbird 0.1.3`
- `python3 /storage/Users/currentUser/tmp/uc2/package_task.py sandbird 0.1.3`

## 交付物

- `packaging/sandbird-0.1.3-ohos-aarch64.tar.gz`：由实际 Conan 缓存打包，约 2 KiB。

## 结束

最终状态: built
