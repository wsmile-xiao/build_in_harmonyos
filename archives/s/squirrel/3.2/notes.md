# squirrel 3.2 适配记录

## 来源与依赖

- 官方仓库：`https://github.com/albertodemichelis/squirrel`
- 标签：`v3.2`
- 归档 SHA-256：`02805414CFADD5BBB921891D3599B83375A40650ABD6404A8AB407DC5E86A996`
- Conan 依赖：无；官方 CMake 只构建 squirrel、sqstdlib 和 sq。

## 适配边界

Conan 的 `shared` 选项映射到上游未声明但实际读取的 `DISABLE_DYNAMIC`/
`DISABLE_STATIC` 缓存变量，默认构建静态库并启用 `fPIC`。上游没有注册 CTest
用例，因此 test_package 通过 `sq_open`、根表压栈/弹栈和 `sq_close` 验证真实
公共 API 与链接闭包。

## 验证

`conan create` 与 test_package 已通过。交叉构建的消费者在
`10.62.150.125:8022` 上使用任务自有原生 `binary-sign-tool sign -selfSign 1`
签名后实际运行，`sq_open`、根表压栈/弹栈和 `sq_close` consumer 结果为 1/1，
目标 RC=0，进程退出且远端任务根独立清理通过。当前 W3 run 为
`F:\\HarmonyPC\\squirrel-3.2-20260904\\w3-r003`，绑定最终候选树；旧 r001
因瞬时进程未捕获 start token 而终止，r002 虽成功但绑定旧候选树，均未复用其
结果。

## 新增知识

- E550：将上游自定义 CMake 动静态缓存开关绑定到 Conan 选项，并用真实 API
  consumer 覆盖无 CTest 的测试边界。
- E551：Windows Conan OHOS 交叉构建必须分离 host/build profile；任务自有
  launcher 只改写 create，CMake/test_package 使用参数列表避开 POSIX 环境文件。
---

**编译结束**: 2026-09-04 07:07
**最终状态**: built
