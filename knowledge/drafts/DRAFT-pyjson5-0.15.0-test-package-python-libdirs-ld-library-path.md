# DRAFT-pyjson5-0.15.0-test-package-python-libdirs-ld-library-path

## test_package 调用 conan python 解释器二进制时必须显式注入 libdirs 到 LD_LIBRARY_PATH

### 问题

纯 Python 包的 test_package 若在 `test()` 中显式调用 conan 依赖的 python 解释器二进制
（`os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")`）直接运行
测试脚本，且只注入 PYTHONPATH（模块导入路径），则该解释器二进制自身的动态库
`libpython3.12.so.1.0` 依赖加载器解析。设备端加载器默认路径恰能解析该库 → 本地
conan create PASS；CI worker（conan-pr-check）加载器路径不能解析 → 远端 CI
`Error loading shared library libpython3.12.so.1.0` + `Py_BytesMain: symbol not found`
+ `ConanException: Error 127`，test_package 第 2 条 RUN 失败（L1_RESULT=fail）。

### 根因

conan python 依赖包 `bin/python3.12` 动态链接 `libpython3.12.so.1.0`（NEEDED）。
PYTHONPATH 只解决"模块从哪里导入"，不解决"解释器二进制自身的共享库由加载器解析"。
设备端与 CI worker 的隐式加载器路径集合不一致，造成同配方本地绿、远端红的真实缺口；
本地普通环境复测（未清空 LD_LIBRARY_PATH）无法暴露该缺口。

### 处理方法

1. test() 中按依赖包声明的 libdirs 构造绝对路径并注入 LD_LIBRARY_PATH：
   `ld_libdirs = [os.path.join(py_pkg, d) for d in self.dependencies["python"].cpp_info.libdirs]`
   （本库 python/3.12.9 的 cpp_info.libdirs=["lib"]，即 package_folder/lib，
   内含 libpython3.12.so.1.0）。不得硬编码绝对缓存路径，不得依赖设备隐式路径。
2. 注入形式用 shell 级 `env LD_LIBRARY_PATH=... PYTHONPATH=... PATH=... cmd`，
   同时保留 PYTHONPATH（site-packages）与 PATH 前置 bin（Conan2 run(env=...)
   在本机部分环境未生效；env 命令形式为真实 shell 命令、可静态解析）。
3. 复验硬要求（加载器环境自检）：在**清空外层 LD_LIBRARY_PATH** 的受限环境下重跑
   conan create，确认 (a) bin/pyjson5 CLI 仍成功；(b) 经 conan python 二进制的
   test_json5_ohos.py 8 断言全部 PASS。自检失败说明修复仍依赖隐式路径，必须回到
   修复步骤；不得跳过自检只跑普通环境。

### 落地

pyjson5 0.15.0 R03（CI build #54716 返工）：test_package/conanfile.py 按上述注入后，
`env -u LD_LIBRARY_PATH conan create ... --build=pyjson5/*` 受限环境重跑 exit 0：
CLI 输出 `{a: 1, b: [2, null]}`，test_json5_ohos.py 输出
`HARMONYOS-SPECIFIC-TEST PASS ... json5 version: 0.15.0`（8 断言），
证明修复不依赖设备端隐式加载器路径。

### 适用范围

所有 OHOS PC（arm64）上、test_package 显式调用 conan python/3.x 解释器二进制的
纯 Python 包（python_class_task）。同样适用于其他显式调用解释器二进制跑测试的
脚本类依赖。反例：通过包内 CLI 包装（自身前置 sys.path）或 Conan VirtualRunEnv
运行环境机制间接调用时，注入由 Conan 承载，本模式仍作为兜底复验方法。
