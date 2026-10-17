# spawn

`spawn` 是比赛任务名称，对应上游 `spawn-fcgi 1.6.6`。该工具用于拉起
FastCGI 应用进程，支持 TCP 与 Unix 域套接字，无外部运行时依赖。

## 鸿蒙适配

- 使用上游 Meson 构建系统，通过 OHOS clang 生成 aarch64 可执行文件。
- 安装产物为 `bin/spawn-fcgi`。
- 消费者测试在 OpenDesk 真机启动真实监听 socket，并完成 FastCGI
  请求/响应往返验证。

## 版本

| 版本 | 状态 | 验证 |
|------|------|------|
| 1.6.6 | built | OpenDesk `CREATE_EXIT=0`，消费者测试 7/7 |
