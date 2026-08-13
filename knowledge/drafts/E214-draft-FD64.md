# E214 — lld --gc-sections 裁剪 __start_/__stop_ 封装符号导致链接失败

## 错误特征
```
ld.lld: error: undefined symbol: __stop___debug
>>> referenced by log.c
>>>               src/log.o:(__btd_log_init)
>>> the encapsulation symbol needs to be retained under --gc-sections properly;
>>> consider -z nostart-stop-gc (see https://lld.llvm.org/ELF/start-stop-gc)
```

## 触发条件
- 构建系统: autotools (bluez 5.79 等使用 `-ffunction-sections -fdata-sections -Wl,--gc-sections` 的项目)
- 阶段: linking (make 链接可执行文件/测试程序时)

## 根因分析
lld 15 的 `--gc-sections` 会裁剪 `__start_`/`__stop_` 段封装符号，导致引用这些符号的代码（如 bluez 的 `src/log.c` 使用 `__start___debug`/`__stop___debug` 遍历调试描述表）链接失败。这是 lld 15 引入的 start-stop-gc 行为变化。

## 解决方案

### 推荐方案
在 LDFLAGS 中增加 `-Wl,-z,nostart-stop-gc`，保留 `__start_`/`__stop_` 封装符号：
```bash
make LDFLAGS="-Wl,--gc-sections -Wl,-z,nostart-stop-gc"
```
或修改 Makefile 的 MISC_LDFLAGS 追加 `-Wl,-z,nostart-stop-gc`。

### 禁止做法
- ❌ 移除 `-ffunction-sections -fdata-sections`（破坏其它优化）
- ❌ 使用 `--build=*/--host=*` 交叉编译参数绕过（导致 configure 检测全部跳过）

## 验证
```bash
grep -rn "gc-sections" Makefile | head -1
make unit/test-sdp   # 修复后应链接成功
```

## 关联条目
- 相关: E001（链接器相关）
