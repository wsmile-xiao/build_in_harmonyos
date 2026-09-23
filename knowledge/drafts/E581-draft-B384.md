# E581（草稿）— Conan/OHOS 适配上游 C/C++ 库时的三类静默陷阱

> 来源：tlsh 5.0.0 首次适配（分支 `feat/tlsh-5.0.0`，2026-09-17，HarmonyOS PC aarch64 / Conan 2.29.1）。
> 三条结论都在同一次适配中被实测触发，且**都不在编译期报错**——分别表现为 ctest 立即失败、
> 运行时段错误、消费者编译期缺常量。

## 错误特征

```
# ① 测试入口缺失（ctest 立刻退出）
TLSH_PROG=../bin/tlsh
error: (127), you must compile ../bin/tlsh
1/1 Test #1: tlsh_unittest_len_xlen ...........***Failed    0.02 sec

# ② 未初始化槽位被解引用（OHOS 必现；glibc 上常因零页侥幸通过）
$ tlsh -split 50,100,200 -f example_data/Week3.txt -o out.tlsh
Segmentation fault (core dumped)          # rc=139

# ③ 消费者拿不到库的编译宏（头文件 API 与库不一致）
error: use of undeclared identifier 'TLSH_STRING_LEN_REQ'
```

## 触发条件

- 构建系统：CMake（上游根 `CMakeLists.txt`）
- 阶段：① testing（ctest）② runtime（CLI 子命令）③ compilation（消费者 test_package）
- 依赖条件：上游把测试入口的产物放在 install 阶段；上游用 `add_definitions()` 切换公共头文件 API

## 根因分析

**(1) 未初始化槽位 + 分发循环被提前短路**

`src/input_desc.cpp::set_input_desc()` 先 `malloc` 一个指针数组 `inputd->tptr`
（容量 `max_files+1`），随后在**同一个分发循环**里逐槽 `tptr[ti] = NULL`：

```c
for (int ti = 0; ti < inputd->n_file; ti++) {
    inputd->tptr[ti] = NULL;
    if (listname || digestname) { ... }
    else if (splitlines) {
        read_file_eval_tlsh_splitline(...);   // 内部按"实际命中的分隔点"填 tptr[0..k]
        ti = inputd->n_file;                  // ← 第一轮就跳出循环，后续槽位从未被置 NULL
    } else { ... }
}
```

`-split 50,100,200` 对上游 `Testing/example_data/Week3.txt`（151 行）只命中 2 个分隔点，
于是 `tptr[2]` 由收尾语句赋值、`tptr[3]` 保持 malloc 原始内容；而输出循环按
`n_file = max_files = 4` 遍历并解引用每个非 NULL 槽 → 野指针解引用。

glibc 上新映射页通常为 0，`tptr[3]` 恰好是 NULL 而被跳过——上游 exp 夹具
（`exp/example_data.Week3.split.tlsh`，3 行）正是在这种"侥幸"下生成的；OHOS 上
malloc 复用非零内存，缺陷必然暴露。

**(2) 测试入口依赖 install 期产物**

上游把 `bin/tlsh -> tlsh_unittest` 的符号链接放在
`install(CODE "file(CREATE_LINK ... SYMBOLIC)")` 里（构建树中不存在；
上游注释：*issue #115 - CREATE_LINK does not work on CENTOS 7*），而 `Testing/test.sh`
默认调用 `../bin/tlsh`。上游自己的 `make.sh` 因此要在 `make test` 之前手工
`cd bin && ln -s tlsh_unittest tlsh`。直接 `ctest` 会以 127 退出。
另外 `Testing/test_parts.sh`、`Testing/test_pattern.sh` 未注册 `add_test`，
ctest 覆盖不到，若 recipe 只跑 `ctest` 会**少跑 247 次上游比对**。

**(3) 库编译宏未导出**

上游根 `CMakeLists.txt` 用 `add_definitions(-DBUCKETS_128)`（默认 128 桶）编译库；
该宏同时决定公共头文件里 `TLSH_STRING_LEN_REQ` 的值与 `getHash()` 的默认参数签名。
Conan 消费者不在同一 CMake 工程内，拿不到这个宏 → 头文件走另一分支。

## 解决方案

### 推荐方案

1. **最小 bugfix 补丁**（`refresh-patch --auto` 生成，`patch_type: bugfix`）：
   在 `malloc` 之后显式把整段数组置 NULL，而不是零散地补某一个槽：

   ```c
   inputd->tptr = (Tlsh **) malloc ( sizeof(Tlsh *) * (inputd->max_files+1) );
   for (int ti = 0; ti < inputd->max_files + 1; ti++) {
       inputd->tptr[ti] = NULL;
   }
   ```

   补丁后 `-split 50,100,200` 的输出与上游 exp 夹具**逐字一致**，test 9 由失败恢复为通过。

2. **在 `build()` 内把上游测试变成可运行**：`cmake.build()` 之后按上游 `make.sh` 的同一动作补
   `bin/<tool>` 符号链接（只落 conan 构建目录的生成目录，不进提交面），并显式执行未注册
   `add_test` 的上游脚本：

   ```python
   def _link_cli(self):
       link = os.path.join(self.source_folder, "bin", "tlsh")
       if not os.path.lexists(link):
           os.symlink("tlsh_unittest", link)

   def build(self):
       cmake.configure(); cmake.build(); self._link_cli()
       cmake.test()                                     # ctest：上游注册项
       self.run('sh "%s"' % os.path.join(self.source_folder, "Testing", "test_parts.sh"))
       self.run('sh "%s"' % os.path.join(self.source_folder, "Testing", "test_pattern.sh"))
   ```

3. **导出上游编译宏**：`package_info()` 里 `self.cpp_info.defines = ["BUCKETS_128"]`，
   让消费者头文件与库一致（注意与 PF5 禁止的 `__OHOS__` 注入无关）。

### 禁止做法

- ❌ 删除 `Testing/exp/*` 夹具、或在 recipe 里跳过失败的 test 编号——把上游真实缺陷
  降级成"看不见"，属外部审查的欺骗档（P0/P1）。
- ❌ 为让消费者编过而把 `__OHOS__`/平台宏混进 `cpp_info.defines`（PF5 禁止项）。

## 验证

```bash
# 复现（未打补丁）
cd <源码>/Testing
../bin/tlsh -split 50,100,200 -f example_data/Week3.txt -o /tmp/x.tlsh   # Segmentation fault (rc=139)

# 修复后（干净轮）
conan create archives/t/tlsh/5.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：Calling build() / Apply patch (bugfix) / 1/1 Test Passed /
#       test_parts.sh 与 test_pattern.sh 各打印 passed / test_package checks=16 failed=0
```

## 关联条目

- 相关：E187（CMake 4.x 拒绝 `cmake_minimum_required(VERSION < 3.5)` → 用
  `CMAKE_POLICY_VERSION_MINIMUM` 兼容；tlsh 同族，本配方用 `cache_variables` 注入）
- 相关：E103（同一 CMake 4 兼容问题）
