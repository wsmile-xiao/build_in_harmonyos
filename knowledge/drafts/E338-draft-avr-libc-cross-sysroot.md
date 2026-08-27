# E338 - 在 OHOS 主机上封装 AVR 目标 sysroot

## 适用问题

`avr-libc` 在 HarmonyOS/aarch64 主机上构建，但产物属于 AVR 目标端。若把包按
OHOS 原生 C 库暴露，Conan 会把 AVR 头文件和静态库注入宿主编译图；若只把
`avr-as`、`avr-ld` 放入 `PATH`，`avr-gcc -B` 又会因为找不到无前缀工具或 linker
scripts 而在委派阶段失败。

典型日志包括：

```text
avr-gcc: error trying to exec 'as'
cannot find ld
cannot open linker script file
```

这不是 OHOS 原生库兼容性问题，而是宿主平台、编译器驱动和 AVR 目标资源三个
边界没有被分别建模。

## 解决方案

1. 把 Conan 包声明为交叉目标资源，避免将其建模为 OHOS 原生 library。
2. `cpp_info.includedirs`、`libdirs`、`libs` 保持为空，仅通过 `resdirs` 和明确的
   `AVR_LIBC_ROOT` 暴露 sysroot。
3. 在构建目录创建临时的 `avr-gcc -B` 派发根，其中同时包含：

   ```text
   .avr-binutils-dispatch/
     bin/as
     bin/ld
     bin/nm
     avr/lib/ldscripts/
   ```

   无前缀工具指向独立 `avr-binutils` 包内的 `avr-as`、`avr-ld`、`avr-nm`；派发根
   只服务本次构建，不进入最终包。
4. `test_package` 必须使用 AVR 工具链生成真实 ELF，并验证：
   - `avr-objdump -f` 报告 `architecture: avr`；
   - GCC 返回的 multilib 路径没有逃逸包根；
   - CRT、`libc.a`、`libm.a` 和 device archive 被实际链接；
   - `avr-nm` 中 `memcpy=T`、`strlen=T`、`sin=W`，其中 `sin` 的弱绑定是预期结果。

## 测试覆盖边界

上游 `tests/simulate` 有 462 个源码：406 C、53 C++、3 汇编。stage-1
`avr-gcc-bootstrap` 只有 C 前端，没有 `avr-g++` 和 `cc1plus`；设备上也没有已打包的
`avrtest` 或 `simulavr`。因此应分别报告：

| 指标 | 结果 |
|---|---:|
| 可执行 C/汇编 compile/link | 409/409（100%） |
| 全部上游源码覆盖 | 409/462（88.53%） |
| Conan consumer | 1/1（100%） |
| C++ 未执行 | 53 |
| AVR 机器码模拟未执行 | 462 |

未执行项必须列出原因，不能计为通过。当前 stage-1 工具链下，AT90S8515 使用已有
基础 multilib，并满足 4 个 malloc/realloc 用例的上游 MCU 条件；相比之下，
ATmega128 需要缺失的 avr51 multilib，ATmega328P 不满足上述 4 个用例条件。

## 与现有知识的关系

HMDFS 的 `umask 077`、`config.status` 临时目录问题已有 E011、E129、E206、E223
覆盖。本草稿不重复这些条目的通用权限结论，只补充交叉目标 sysroot 的 Conan
包边界、`avr-gcc -B` 目标工具派发和可审计测试覆盖口径。

## 验证证据

- 真机 Shadow CI：上游 C/汇编 409/409、consumer 1/1，Build Summary 1/1。
- 正式 PR CI：PR #6700，CI #31650 / build 35540，Conan test_package、L0、L1
  和全部流水线步骤通过。
- 复现命令：

  ```sh
  CI_PACKAGES="archives/a/avr-libc/2.2.1" zsh ci/conan/build_and_test.sh
  ```
