# DRAFT-ohos-peripheral-lib-failed-open-footgun: 外设库 failed-open 句柄访问器 NULL-deref footgun

> **Contributor**: sea_crab | **Status**: Draft | **Updated**: 2026-08-31
> **Severity**: 2 | **Category**: harmonyos / peripheral / failed-open / null-deref / footgun / mmio / testing
> **Source**: c-periphery 1.0.0 HarmonyOS PC adaptation

## 错误特征

```text
./tests/test_mmio </dev/null
WARNING: This test suite assumes a BeagleBone Black (AM335x) host!
Assertion failed: r (tests/test_mmio.c: test_open_config_close: 41)
RC=134
```
（mmio_open 无 /dev/mem 失败后，mmio_read*/write* 访问器解引用 NULL → 段错误）

## 现象

c-periphery 1.0.0 mmio.c 实证：mmio_open() 在 open(/dev/mem) 失败时返回错误，
但返回前已 memset 句柄并写入 base/size/aligned_base/aligned_size（aligned_size
有效），ptr 保持 NULL。mmio_read32/write32/read/write 等访问器仅做
`(offset+len) > aligned_size` 边界检查，通过后直接解引用 NULL 指针 → 段错误。

同库同类风险（失败路径句柄部分初始化）：
- i2c.c / spi.c / serial.c：open 失败前 memset 句柄 → fd=0（非 -1）→
  i2c_close/spi_close/serial_close 的 `if (fd < 0) return 0` 守卫失效 →
  `close(0)` 误关 stdin；
- gpio.c：参数校验失败路径在 memset 之前 → 句柄保持调用前未初始化状态。

## 与现有知识的关系

- knowledge/graph 与 knowledge/drafts 对 NULL-deref/footgun 全库 0 命中。
- 最近似 DRAFT-avarice-ohos-no-hardware-peripheral-stub：其讲"构建期 stub 绕过
  外设库依赖"；本条目讲"运行期失败句柄错误路径测试设计 + 披露"，两者正交。

## 根因

外设/寄存器映射类库 open() 失败路径只初始化句柄的部分字段（错误码 + 元数据），
未保证指针/文件描述符字段处于安全值。访问器边界检查不校验 ptr（mmio），或
close() 的负值守卫不覆盖 fd=0（i2c/spi/serial）——"failed-open 句柄访问器
footgun"。无硬件环境（无 /dev/mem、/dev/i2c-*、/dev/spidev*）下消费者必然触发。

## 解决方法

1. 消费者测试设计（无硬件 CI 环境）：只测 open/close 错误路径——断言错误码
   （*_ERROR_OPEN）、errno（ENOENT）、errmsg（含失败路径），close failed-open
   句柄确认安全；绝不调用 failed-open 句柄的访问器。
2. 审计上游句柄初始化完整性：open 失败路径逐字段检查 ptr/fd 状态。
3. notes 披露义务：footgun 必须如实披露，防下游消费者崩溃。

实证（c-periphery test_package/test_periphery.c 17 断言）：
```c
int r = mmio_open(&mmio, 0x44e10000u, 4096u);   /* 无 /dev/mem → 失败 */
CHECK(r != 0, "mmio: open without /dev/mem fails");
CHECK(mmio_errno(&mmio) == ENOENT, "mmio: missing /dev/mem errno == ENOENT");
CHECK(mmio_close(&mmio) == 0, "mmio: close on failed-open handle returns 0");
```
test_periphery.c 注释明确说明只测 open/close 错误路径，不调用 failed-open 句柄
的 read/write 访问器。consumer 17/17 断言全部通过（CI round-1）。

## 验证

- 复现：./test_mmio（无 /dev/mem）→ mmio_open 返回 ENOENT → 断言失败 RC=134；
  Builder 用 marker 法隔离复现 Signal 11。
- 规避：consumer test_package 只测错误路径 → 17/17 断言通过、exit 0。
- 同类泛化：i2c/spi/serial failed-open 后 fd=0 → close(0) 误关 stdin；
  gpio 未初始化句柄。

## 适用场景

无硬件环境（OHOS 沙箱/CI）下消费外设/寄存器映射类库（mmap、/dev 节点访问）的
测试与程序；同类库模式：mmap/GPIO/I2C/SPI/串口设备访问库的失败路径测试设计。

## 禁止做法

- 不要在无硬件环境对 failed-open 句柄调用访问器（mmio_read*/write* → NULL 解引用
  段错误）。
- 不要伪造通过统计：consumer 只测错误路径必须在 notes/测试注释如实披露（R9/R34）。
- 不要整体跳过上游测试；5 个上游测试逐项编译、逐项记录不可运行原因（硬件 + 交互
  stdin），由用户决定接受缺口。
