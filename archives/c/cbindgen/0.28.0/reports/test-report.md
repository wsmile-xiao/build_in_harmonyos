# cbindgen 0.28.0 测试报告

Conan/W3 真机验证通过，等待远端评审与发布。任务6784；正式Rust版本1.97.1。

| 范围 | 执行 | 通过 | 失败 | 说明 |
|---|---:|---:|---:|---|
| 单元实例 | 4 | 4 | 0 | lib/bin各2 |
| 集成实例 | 157 | 157 | 0 | 147生成器+7profile+3depfile |
| 消费者断言 | 18 | 18 | 0 | 安装包CLI→Rust静态库→C/C++链接运行 |
| 上游ignore示例 | 0 | 0 | 0 | 1个rust,ignore文档块；工具链未含rustdoc |

构建：`cargo build --locked --release --bin cbindgen`；上游：`cargo test --locked --release --lib --bins --tests -- --test-threads=1`。
stderr/stdout及退出码保存在交付目录publish-20260910和cbindgen-local-verification-reports。
W3结果：pass；环境为OHOS/6.0 armv8 Release profile、实际系统6.1.0.115。

W3完整日志SHA256：5186c47a4ae6931390187636f8942896e5769907a1bc79671a04233b2a5679fa。
本轮实际Conan配方revision：b04343680b93ade1a6a41f5d8c11b194；与主机重新export结果一致。
W3通过L0/L1/L2/L4/L5，并执行移除产物后的负向消费者验证。
finish其余告警是主线E219/E253/E305字段缺失及旧打包/材料检查，不作为本包CI成功证据。
本包没有修改这些知识条目；独立graph validate退出0。

## CI #43268 修复复验

原始发布Rust包缺少OHOS执行签名：Cargo仅chmod后仍返回Permission denied；
仅签Cargo/rustc后，rustc_driver装载失败。现在由包内入口在私有缓存中签名这三个文件，
使用文件锁及目录原子发布，并只在工具子进程设置加载路径。

最终配方revision：`b04343680b93ade1a6a41f5d8c11b194`；主机export与鸿蒙W3日志一致。
最终W3完整日志SHA256：`5186c47a4ae6931390187636f8942896e5769907a1bc79671a04233b2a5679fa`。
原始证据目录：`output/cbindgen-0.28.0/publish-20260910/repair-final/`；
同目录外的`p017.log`、`p018.log`分别记录W3与安装包附加回归。
上游161/161、消费者18/18通过；1个上游ignore文档示例仍单列。
依赖中Cargo/rustc/driver三份文件构建前后SHA256相同。
附加验证覆盖并发首次调用、默认sysroot、两种显式sysroot参数和启动器父目录名称。
附加回归不加入18个原有消费者断言的统计。

真实安装包清单校验13项；验证包SHA256：
`2a46f5c55b2a8537b243a0fe9f30b166cb195cbc0dc6f910ca2700f5c3e8e3d1`。
旧p016用于完整finish初轮，最终代码以p017的完整W3、p018产物和源码哈希为准。
远端CI、检视、提审、合入及发布状态继续按PR !9264的最新结果记录。
