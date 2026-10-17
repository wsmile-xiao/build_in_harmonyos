# Conan 交叉构建 test_package 的可运行性边界

## 现象或适配场景
`conan create` 能编译出 OHOS/arm64 消费者，但 `cmake.test()` 在 Windows 上混用 build/run 环境，或直接尝试执行目标二进制而失败。

## 根因
交叉编译时构建机和运行机不是同一环境。`conanbuild` 与 `conanrun` 包含不同的环境包装器，目标 ELF 也不能由 Windows 主机执行；把两者强行合并会产生驱动器错误或格式错误。

## 修复步骤
保留 CMake 构建步骤，test 阶段先用 `can_run(self)` 判断主机能力；不可运行时记录明确警告并返回，仍保留显式 `self.run(executable, env="conanrun")` 作为可运行配置下的 L0 消费者入口。随后在授权真机以独立 W3 事务执行同一消费者。

## 验证方式
OHOS profile 下 test_package 构建完成并安全跳过主机执行；Windows host profile 下同一消费者实际运行并输出 `tinyxml consumer PASS`；目标设备结果另以签名、RC、进程清零和释放回执证明。

## 适用范围和安全边界
适用于 Conan 的跨编译 test_package。`can_run` 只解决主机不可执行问题，不产生目标 PASS；不能用主机消费者结果替代真机验证，也不能改变上游测试分母。
