# gengen 1.4.2 上游测试运行证据（原字节数/sha256 见文首）

- 原始日志：设备 `~/tmp/uc2/gengen-1.4.2/check2.log`
- 原始字节数：21497
- sha256：`4060f39a049194588a559b35ce6e7df6119d82ee915cce4cd35fc8abc9e07808`
- 命令：`make check -j1`（顶层，SUBDIRS=lib src tests）
- 结果：exit 0；本文件为逐字摘录（greppable 标记），原始日志不入库

## 单元测试（src/tests，automake TESTS）

```
PASS: test_replace
PASS: test_exp_checker
PASS: test_exp_generator
PASS: test_type_env
```

## 金标 diff（tests/ + otherdir）

`grep -c "^diff "` = 48，构成：

- 35 条生成文件金标 diff（check-diff 对 BUILT_SOURCES 逐个 `diff $$source $(srcdir)/$$back_output`）
- 8 条错误输出 diff（`diff alreadydef.err alreadydef.err_test` 等 8 个 ERRFILES，全部出现于日志）
- 1 条 verbose diff（`diff verbose.output verbose.out`，日志 253 行）
- 4 条 otherdir diff（`expect no output from diff` 后的 4 条 `diff`，日志 79 行附近）

check-diff 内任一 diff 失败都会置 errors=1 使 make check 失败；exit 0 即 48 条全部通过。
`grep -cE "^(FAIL|ERROR)"` = 0。

## 首轮运行说明

首轮 `make check`（check.log）在 tests/ 的 test_if 链接步骤中断（exit 2）：
4 条规则把已生成头文件放进编译命令行，clang-15 报
`clang-15: error: cannot specify -o when generating multiple output files`。
修正 4 条规则（删去命令行上的 .h，测试语义不变）后重跑得上述全过结果。

## C++17 修复必要性证据（构建级复现）

pristine 1.4.2 tarball + 同参数 configure + `make -j1 CXXFLAGS=-std=c++17`：

```
scanner.cc:836:2: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]
        register yy_state_type yy_current_state;
scanner.cc:837:2: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]
        register char *yy_cp, *yy_bp;
```

（src/scanner.cc 共 15 处 register；配方 build() 中 sed 删除行首 register 后，
探索构建与后续 conan create 在 cppstd=17 下正常编译。）

## 消费者探针先行验证（与 test_package/test.py 同构）

```
COMPILE_OK
RUN_EXIT=0
consumer.out（cat -A）:
demo begin$
  value=42$
  flag=yes$
demo end$
```
