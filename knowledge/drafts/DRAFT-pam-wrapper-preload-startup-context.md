# LD_PRELOAD 启动上下文必须在 exec 前准备

> 来源：pam-wrapper 1.1.8，PR 4234
> 状态：DRAFT

## 现象

测试进程设置了 `PAM_WRAPPER_SERVICE_DIR`，也会在 `main()` 中创建 PAM service
和 passdb，但 `run_pamtest()` 仍然报告服务不存在、PAM 初始化失败或读取了错误
路径。把相同文件提前放好后测试能够通过。

## 根因

`LD_PRELOAD` 不是在消费者第一次调用 wrapper API 时才生效。动态加载器会在
进入 `main()` 前加载 preload 库并运行其 constructor/初始化逻辑。pam-wrapper
会在这个阶段复制 `PAM_WRAPPER_SERVICE_DIR`，因此存在明确的时序边界：

```text
父进程准备夹具和环境
  -> exec 消费者
  -> 动态加载器装载 LD_PRELOAD 库
  -> preload 初始化捕获环境/路径
  -> main() 开始
  -> 功能测试
```

如果把“准备夹具和环境”放进 `main()`，它就落在捕获动作之后。失败表面上像
PAM、模块或文件权限问题，实际是启动上下文不完整。

## 推荐方案

由测试编排层完成准备工作。本适配在 Conan `test_package.test()` 中：

1. 创建私有 runtime 和 service 目录；
2. 写入 `pam_matrix` service 文件和 passdb；
3. 使用绝对路径设置 `PAM_WRAPPER_SERVICE_DIR`、
   `PAM_WRAPPER_RUNTIME_DIR`、`LD_LIBRARY_PATH` 和 `LD_PRELOAD`；
4. 启动消费者，消费者只调用 `run_pamtest()` 并断言认证结果。

若架构上只能由消费者生成夹具，可以使用两阶段自重启：第一阶段不加载
preload 库，只准备数据；随后设置环境并 `exec` 自身进入第二阶段。

## 与现有知识的边界

E200 证明 OHOS/musl 支持 LD_PRELOAD，并要求做功能验证。本条目补充的是
preload 库具有启动时状态时，验证必须遵守“父进程准备、子进程 exec”的顺序。
它不处理 hmmac 标签或 ELF 签名失败；出现 `Permission denied` 时仍应分别检查
E212 和构建树签名闭包草稿。

## 验证证据

- 运行目录：`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-pam-wrapper-pam-wrapper-1.1.8-r3-conan5-20260806-132958-13395`
- 结果：consumer 输出 `pam-wrapper libpamtest authentication check passed`，
  L0/L1/L4/L5 通过。

## 禁止做法

- 在消费者 `main()` 中才设置 preload 初始化所需环境。
- 在 `main()` 中才创建 preload 初始化会读取的配置或状态文件。
- 依赖 CTest/Conan 的当前工作目录解析相对路径。
- 将时序失败误判为 PAM API 不兼容并跳过真实认证测试。
