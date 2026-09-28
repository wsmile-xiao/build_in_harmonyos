# E430 — OHOS 上 make 无法创建 jobserver fifo，并行构建测试程序必然失败

## 错误特征

```
make: jobserver mkfifo: /tmp/GMfifo12345: Operation not permitted
make: *** [Makefile:120: test/jws_json] Error 1
```

或在 CMake 驱动下：

```
gmake[3]: *** [test/CMakeFiles/jwe_ecdh.dir/build.make:76: test/jwe_ecdh] Error 2
make: *** [Makefile:166: all] Error 2
```

关键点是错误行里出现 `jobserver`、`mkfifo` 或 `Operation not permitted`，
且**库目标本身已经编过**，失败集中在链接/生成测试程序的那一步。

## 触发条件

- 构建系统: make / CMake（Makefile 生成器）/ autotools
- 阶段: compilation（测试目标）或 testing
- 前提: `make -j N`（N > 1）、或环境里带了 `MAKEFLAGS=-jN`、或 `cmake --build . -- -jN`
- 结论: 与源码、依赖、工具链都无关——纯粹是 OHOS 不允许 make 在其所选目录创建 jobserver 命名管道

## 根因分析

GNU make 在并行模式下会创建 jobserver 命名管道用于 token 传递，路径通常落在 `$TMPDIR`
或构建目录。OHOS 设备的沙箱/文件系统策略不允许 `mkfifo`（实测 `/tmp` 亦不可写），
于是 make 在**启动任何编译之前**就退出。因为串行 `make`（`-j1`）不建 fifo，
所以「不并行就没事」这一现象具有很强的误导性：很容易被当成竞态或依赖顺序问题。

## 解决方案

### 推荐方案

对**构建测试程序**的那一步显式串行：

```bash
# CMake 工程：目标级串行
cmake --build "${CMAKE_BUILD_DIR}" --target ${TEST_TARGETS} -- -j1

# conanfile.py 中
def _build_test_programs(self):
    self.run('cmake --build "%s" --target %s -- -j1'
             % (self.build_folder, " ".join(test_targets)))
```

库本身的编译可以保持并行（只用 `cmake.build()`），只要测试目标串行即可。

### 禁止做法

- ❌ `export MAKEFLAGS=-j4`（配方或 CI 脚本里）——必定触发
- ❌ `cmake --build . -- -j2`（任何 ≥2 的并行度）
- ❌ 把该错误当成「测试源码问题」去改测试代码或关掉测试（R51 三步法要求真跑上游测试）

## 验证

```bash
cd <构建目录>
make -j2 2>&1 | grep -i 'jobserver\|mkfifo'   # 期望命中，说明诊断成立
make -j1 2>&1 | tail -3                        # 期望成功
```

## 关联条目

- 相似: E429（同批在 rhonabwy 适配期间发现，均属「与源码无关、但会浪费整轮验证」的构建环境陷阱）
