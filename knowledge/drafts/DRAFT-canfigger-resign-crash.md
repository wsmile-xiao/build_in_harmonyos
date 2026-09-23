# DRAFT-canfigger-resign-crash — hnp clang 已内嵌 codesign 签名的共享库被 binary-sign-tool selfSign 重签后 musl 加载器 SIGSEGV

## 错误特征

conan create 全流程(编译/安装)正常,`test_package` 运行消费者时:

```text
canfigger/0.3.2 (test package): RUN: ./test_canfigger
Signal 11 (core dumped)
ERROR: canfigger/0.3.2: Error in test() method, line 35
	self.run(executable, env="conanrun")
	ConanException: Error 139 while executing
```

手工以 `LD_LIBRARY_PATH=<pkg>/lib` 加载包内 `.so` 复现同样的 SIGSEGV(core dumped)。

## 触发条件

- 构建系统: meson(其他构建系统经 hnp clang 链接同样适用)
- 阶段: package()/runtime —— 对 `.so` 执行 `binary-sign-tool sign -selfSign 1` 重签后
- 平台: OpenHarmony PC(aarch64, musl 加载器)
- 关键前提: 编译器是 hnp clang(`TARGET: aarch64-unknown-linux-ohos`),其链接驱动
  **自动在输出 ELF 内嵌 ad-hoc `.codesign` 签名段**(`readelf -S` 可见)

## 根因分析

hnp clang 驱动在链接期已对输出 ELF 内嵌 ad-hoc `.codesign` 签名段——本地 meson
产物与 Conan 包产物 `readelf -S` 均能看到该段。此时再用 `binary-sign-tool selfSign`
重签,生成的重签段与本机 musl 加载器不兼容,加载该 `.so` 即 SIGSEGV。

对照实验(canfigger-0.3.2,2026-09-05):

| 产物 | `.codesign` | 消费者加载结果 |
| --- | --- | --- |
| 链接器产物(原样) | 有(链接器内嵌) | PASS,40/40 断言 |
| `binary-sign-tool selfSign` 重签产物 | 有(重签) | **SIGSEGV(exit 139)** |
| 重签产物剥离 `.codesign` | 无 | PASS,40/40 断言 |

崩溃锁定在重签段本身,而不是签名缺失。

## 解决方案

### 推荐方案

共享库**不做二次签名**:保留链接器内嵌的 `.codesign`,`package()` 只把 Meson 的
版本化别名(`.so.0`/`.so`)实体化为真实文件(实体拷贝保留链接器签名)。

```python
# conanfile.py package() 伪代码
if bool(self.options.shared):
    self._materialize_shared_aliases()   # shutil.copy2,保留签名段
    # 不调用 binary-sign-tool
```

### 禁止做法

- ❌ 对 hnp clang 链接的 `.so` 执行 `binary-sign-tool sign -selfSign 1` 重签
  ——重签段与 musl 加载器不兼容,加载即 SIGSEGV
- ❌ 先 `llvm-objcopy --remove-section .codesign` 再 selfSign 重签——同样产出
  不兼容的重签段
- ❌ 把重签崩溃误判为"链接器签名缺失"而加重签——对照实验证明签名已存在

## 验证

```bash
readelf -S <pkg>/lib/libcanfigger.so.0 | grep -c codesign   # >= 1(链接器签名保留)
LD_LIBRARY_PATH=<pkg>/lib ./test_canfigger                  # PASS assertions=40
# 复现重签崩溃(对照):
binary-sign-tool sign -inFile lib.so -outFile lib.so.signed -selfSign 1
mv lib.so.signed lib.so && LD_LIBRARY_PATH=<pkg>/lib ./test_canfigger  # exit 139
llvm-objcopy --remove-section .codesign lib.so              # 剥离后恢复 PASS
```

## 关联条目

- 相关: E077(ELF 需含有效 `.codesign` 才能被加载/移除后自签的可执行文件流程)、
  E318(go test 可执行文件 selfSign 流程,未复现本问题)、E083(BiSheng JVM 校验
  `.codesign` 与 selfSign 签名)
- 差异: 本条目限定**共享库加载**场景;E077/E318 针对测试可执行文件执行场景,
  两者不冲突

## 来源

- canfigger-0.3.2 适配(2026-09-05),设备实测对照实验
- 消费者证据: `CANFIGGER_CONSUMER_TEST PASS assertions=40`(重签剥离后)
