# DRAFT-maxflow-3.0.5-isolated-job-cmake-ctest-path — 隔离 job 里 CMake/CTest
# helper 的裸 cmake/ctest 解析不到：conf_info 不回灌自身，须在主配方与
# test_package 两处 generate() 注入 build-env PATH

> Contributor: codex | Status: Draft | Updated: 2026-09-27
> Source event: maxflow 3.0.5 HarmonyOS PC 适配，真机 shadow CI r2/r3/r5
> （archives/m/maxflow/3.0.5）

## 错误特征

```text
maxflow/3.0.5: Running CMake.configure()
maxflow/3.0.5: RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=...
/system/bin/sh: cmake: inaccessible or not found
ConanException: Error 127 while executing
```

两个独立上下文都会中招：① 包本体 build() 的 CMake helper（r2/r3）；
② **test_package 消费者配方自己的 CMake.configure()**（r5——包本体已全绿后
才暴露）。L1_RESULT=fail: conan create failed。

## 根因（三层，均为真机实测）

1. **环境层**：隔离 shadow CI job 的 runner 基础 PATH
   （`/bin:/usr/bin:/sbin:/usr/sbin:~/usr/local/bin` + ohpc-ci-shadow 前缀）
   不含 `/data/service/hnp/bin`，也不含 CMake 载荷目录
   `/data/service/hnp/cmake.org/cmake_4.1.2/bin`。CMake helper 以裸 `cmake`
   作为兜底程序名，解析失败即 Error 127。ctest 同理（上游测试要用）。
   （"隔离 job PATH 无 hnp 目录"这一环境事实与
   DRAFT-gnat-consumer-ohos-hnp-binutils-path 一致，但失败面不同：GNAT 是
   execvp("as") 汇编器，本条是 Conan CMake/CTest helper 的程序解析。）
2. **conf 陷阱**：`self.conf_info.define("tools.cmake:cmake_program", ...)` 写在
   generate() 里**对本节点自己的 helper 无效**（r3 实测复证；与 getdns
   草稿 "self.conf_info.define() 不会回灌到自身构建" 同一原则，本条是该原则
   在 `tools.cmake:cmake_program` 键上的新实例——audtty 式 conf_info 写法
   不能解决 helper 解析问题）。
3. **上下文陷阱**：主配方的 build-env 注入只覆盖包本体 build()；test_package
   是独立配方/独立图节点，有自己的 generate()，必须**各自注入**（r5 实测）。

## 解法（r6 全绿验证）

在 conanfile.py **和** test_package/conanfile.py 的 generate() 里各加一次
build-env PATH 注入（机制同 DRAFT-8960-libei 的 save_script 手法，用途从
LD_LIBRARY_PATH 换成程序查找）：

```python
from conan.tools.env import Environment

def generate(self):
    env = Environment()
    for d in ("/data/service/hnp/cmake.org/cmake_4.1.2/bin",   # cmake+ctest，稳定
              "/data/service/hnp/bin"):                         # make/ninja/as 等
        if os.path.isdir(d):
            env.prepend_path("PATH", d)
    env.vars(self, scope="build").save_script("conanbuild_hnp_path")
    ...
```

要点：

- cmake.org 载荷目录放前面（包载荷稳定，不像 hnp/bin 的符号链接会被并行
  任务增删）；cmake_4.1.2 同时说明 E103（cmake_minimum_required ≥3.5）
  在本设备是硬前提；
- make/ninja 已在 `~/usr/local/bin`（PATH 含），无需处理；
- 不要试图只改一处——两个配方上下文各自独立。

## 查重（B1 证据摘要）

- 检索词：`cmake: inaccessible or not found` / `cmake_program` / `save_script`
  / `conf_info` / `Environment`（knowledge/ 全目录）。
- DRAFT-gnat-consumer-ohos-hnp-binutils-path：同一环境事实（隔离 job PATH 无
  hnp），失败面是 GNAT/binutils execvp；本条失败面是 Conan CMake/CTest
  helper 程序解析，且新增 test_package 上下文维度；
- DRAFT-ohos-conan-make-executable-conf：配方自己 self.run 调 make 的 conf
  未注册问题；本条是 helper 内部裸程序解析，conf 未注册问题不出现；
- DRAFT-8960-libei：save_script 机制同源，但注入对象是 LD_LIBRARY_PATH
  （libc++ 加载），非程序查找；
- DRAFT-13532-getdns：conf_info 不回灌自身原则的提出者，键为
  find_package_prefer_config；本条提供 tools.cmake:cmake_program 键的实测
  实例。
- 新增价值：① 首个 CMake/CTest helper 程序解析失败条目；② conf_info 陷阱在
  cmake_program 键上的复证；③ **test_package 独立上下文需独立注入**（全新维度，
  r5 实测，此前无任何草稿提及）。

## 验证证据

- r2/r3：裸 conf_info/无注入 → Error 127；
- r4：build-env 注入后包本体 configure/build 全绿；
- r5：test_package 同签名失败 → 消费者配方加同样注入；
- r6：exit 0，L0/L1/L4/L5 pass，上游 ctest 10/10，test_package 7/7。
