# rcheevos 12.2.1 知识证据报告

- 任务：rcheevos C 适配（知识库扩展，ohpcd contrib-10027）
- 真机：10.195.180.238，隔离 job `device-b/rcheevos-kb-20260920`
- 日期：2026-09-20；环境：clang 15.0.4（aarch64-unknown-linux-ohos）、Conan 2.29.1、profile sha 367f2b79…（同 psimd job）

## 证据链（三轮 conan create + 探针，全部 target-executed）

### EVID-01 构建期：musl c89 下 LFS *64 隐式声明（未打补丁）

```text
../src/rhash/hash.c:188:3: error: implicit declaration of function 'fseeko' [-Werror,-Wimplicit-function-declaration]
#define fseeko64 fseeko   ← sysroot stdio.h:213 无条件宏别名；fseeko 声明被严格 -std=c89 隐藏
../src/rhash/hash.c:199:10: error: implicit declaration of function 'ftello'
2 errors generated. → make Error 1
```

修复：patches/0001（test/Makefile CFLAGS 追加 `-D_DEFAULT_SOURCE`，一行，不动源码）。

### EVID-02 运行期：float→unsigned UB 架构分歧（仅补 0001 后）

上游测试真实运行：**2707/2712 passed**，5 项失败全部为浮点转无符号类：

```text
* test_condset/test_addhits_float_coercion — Found: 0 == 1
* test_value/test_evaluate_value("v5900_0xh0000*-1.0_0xh0001*-100.0", 4100) — Found: 5900 == 4100
* test_value/test_typed_value_convert(FLOAT, -1.0, UNSIGNED, 0xFFFFFFFF) — Found: 0 == -1
* test_value/test_typed_value_convert(FLOAT, -3.14159, UNSIGNED, 0xFFFFFFFD) — Found: 0 == -3
* test_value/test_typed_value_negate(FLOAT, -2.7 → 2.7) — Found: 0 == 1
```

根因：`src/rcheevos/value.c:495` `(unsigned)f32` 负值 UB——MSVC/x86 参考产出测试期望的补码模式，aarch64 `fcvtzu` 饱和为 0。
修复：patches/0002（`(unsigned)(int64_t)f32`，一行）。

### EVID-03 修复后全量（补 0001+0002）

```text
Done. 2712/2712 passed in 1 seconds
```

### EVID-04 消费者测试（打包后）

conan create 退出码 0；ctest `1/1 test_rcheevos Passed`；直接执行输出：
`test_rcheevos: OK (runtime activate/tick/trigger, lboard, error strings)`——8/8 断言
（激活解析 RC_OK、非法输入负例 <0、先假后真触发公开 TRIGGERED 事件、get_achievement 非
NULL、rc_error_str(RC_OK)=="OK"、排行榜激活与 VALUE 格式化 "12,345" 与上游分隔符语义一致）。

### EVID-05 触发器状态机探针（内部 API，设备侧）

```text
initial state=1(WAITING)
frame0 val=0 → state 2(ACTIVE)   frame1 val=0 → ACTIVE
frame2 val=1 → state 5(TRIGGERED)  frame3/4 → 返回 0(INACTIVE) 但 state 保持 TRIGGERED
```
与上游 test_evaluate_trigger_triggered 的注释语义一致。另发现 peek 回调以 1 字节粒度被
调用（n=1），消费者测试据此实现小端字节服务式 peek。

## 包完整性

产物：include/*.h + lib/librcheevos.a + licenses/LICENSE（静态库，对象来自上游 Makefile 编译，
含全部哈希/rapi/rc_client 支持）。上游测试无 -m64 报错（clang aarch64 接受）。

## 测试统计

| 层 | 库存 | 通过 | 失败 | 依据 |
|---|---:|---:|---:|---|
| 上游 make runtests | 2712 | 2712 | 0 | EVID-03 |
| 消费者 CHECK | 8 | 8 | 0 | EVID-04 |

## 影子 CI 门禁

【待回填：提交后 run-ohos-shadow-ci.sh 结果】
