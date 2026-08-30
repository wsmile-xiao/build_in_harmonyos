# E2167 — 用嵌入式 Python 启动器把上游 dlopen/ctypes 测试接进 worker 唯一放行的 exec 加载路径

## 错误特征

前置：命中 E2166（worker 对 dlopen/LD_PRELOAD 双拒）。典型失败日志（#33895/#33918，isl 套件）：

```
isl ctypes: LoadLibrary('.../isl-python-shared/.libs/libisl.so.23.5.0') failed:
  Error loading shared library ...: Permission denied; fallback find_library=None
AttributeError: do_dlsym failed: Symbol not found: isl_ctx_alloc  so=/data/service/hnp/bin/python3
FAIL: isl_test_python.py
```

`so=` 显示的是**解释器主程序**——`CDLL(None)` 只能看启动时已进入全局符号域的对象；上游 ctypes 绑定的终态回退恰好在 `CDLL(None)` 上取符号。让它成功的方法只有一个：**在进程启动前把目标库挂上 NEEDED**。

## 触发条件

- 构建系统：Autotools（automake serial test，`PY_LOG_COMPILER = $(PYTHON)`）或任何允许换测试解释器的 harness
- 阶段：`make check` / test_package
- 环境：CI worker（见 E2166 边界）；本地设备可用 `MODE-B` 式模拟验证

## 根因分析

嵌入式启动器自身 `NEEDED libisl.so.23`（由链接时传自签库**完整路径**获得，运行时经 `LD_LIBRARY_PATH` 解析到 `.libs` 里构建期新自签副本——这条 exec 路径在 worker 被放行），`Py_Initialize` 后 python 的 `CDLL(None)` 搜索主程序全局域即可命中 `isl_ctx_alloc`。上游 0008 类补丁把真实 dlopen 异常打到 stderr 后回退的路径**原样复用**，测试计算逻辑零改动——这是"绕过平台禁用路径"而非"绕过测试"。

## 解决方案

### 推荐方案（embedded-python-launcher）

launcher.c（关键三处：`Py_DecodeLocale` 转 argv、脚本目录入 `sys.path`、SimpleFileEx 退出码透传）：

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
int main(int argc, char *argv[]) {
    if (argc < 2) { fprintf(stderr, "usage: %s SCRIPT [ARGS...]\n", argv[0]); return 2; }
    Py_Initialize();
    wchar_t **wargv = PyMem_RawMalloc(sizeof(wchar_t *) * (size_t)argc);
    for (int i = 1; i < argc; ++i) wargv[i - 1] = Py_DecodeLocale(argv[i], NULL);
    PySys_SetArgvEx(argc - 1, wargv, 0);
    for (int i = 1; i < argc; ++i) PyMem_RawFree(wargv[i - 1]);
    PyMem_RawFree(wargv);
    PyRun_SimpleString("import sys, os\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))\n");
    FILE *fp = fopen(argv[1], "r");
    if (!fp) { perror(argv[1]); Py_Finalize(); return 2; }
    int rc = PyRun_SimpleFileEx(fp, argv[1], 1);
    Py_Finalize();
    return rc == 0 ? 0 : 1;
}
```

编译与路由（配方内，`llvm-readelf -d` 断言 `libisl` NEEDED 在位；HNP 路径全硬编码，仅 `settings_build.os == OHOS` 分支执行）：

```bash
clang -Wno-deprecated-declarations launcher.c -I "$PYINC" \
      "$PYROOT/lib/libpython3.12.so" "$BUILD/.libs/libisl.so.23.5.0" \
      -Wl,-rpath,"$PYROOT/lib" -o isl_py_launcher
make -j1 check PYTHON="$PWD/isl_py_launcher"     # ← 必须 make 命令行参数形式
```

`$PYINC/$PYROOT` 用 `sysconfig` 从被测解释器现场探测（`get_paths()['include']` + realpath(sys.executable) 上两级 + `LDLIBRARY`/`Py_ENABLE_SHARED`）；automake 的 `AM_TESTS_ENVIRONMENT` 会自带 `export PYTHONPATH=interface`，嵌入式解释器直接继承，`import isl` 无需额外注入。

> 防御性加固（并行实测线索，libxft 2.3.8 @ 本机，2026-08-28）：部分环境加载器**无法**经符号链接的 SONAME 别名解析共享库，且实体化用 `copyfile` 会丢 owner 执行位（缺 `x` 时 `PROT_EXEC` 映射同样报 Permission denied）。worker 上 #33932 经 libtool 的 `libisl.so.23` 符号链接成功解析，但跨环境移植时建议把别名也实体化为保 `0755` 的签名副本，或直接把 NEEDED 目标指向实体文件所在目录最前。

### 禁止做法

- ❌ `PYTHON=x make check` 的 **shell env 前缀**写法：Makefile 里 `PYTHON = @PYTHON@` 赋值优先于环境变量，launcher 静默失效（#33918 实测，traceback 仍 so=python3）。决定性对照：`make check PYTHON=/definitely/not/python3` → FAIL(rc=2) 证明参数形式生效。
- ❌ 用 `LD_PRELOAD` 当 worker 上的回退（E2166：被忽略且无告警）。
- ❌ 把 `char** argv` 直接喂 `PySys_SetArgvEx`（wchar_t 重解释 → `no mem for sys.argv` / 越界码点崩溃，先于测试本体，极易误判为平台拒载）。

### 回退方案

被测解释器所在 HNP 无共享 `libpython.so` 时（`Py_ENABLE_SHARED=0`），改用 `python3-config --includes` + `--ldflags --embed` 静态嵌入 python（目标库 NEEDED 不变）；再不通则回到 E2166 的上报路径。

## 验证

```bash
# 1) 启动器编译后断言 NEEDED 在位
llvm-readelf -d isl_py_launcher | grep "libisl.so"
# 2) 符号域冒烟（无 LD_PRELOAD、无任何成功的 isl dlopen）
echo 'import ctypes; ctypes.CDLL(None).isl_ctx_alloc; print("SCOPE OK")' > scope.py
./isl_py_launcher scope.py                 # 期望 SCOPE OK
# 3) 决定性终裁在 CI worker：FAIL: isl_test_python.py → PASS，其余 24 项保持 PASS
```

## 关联条目

- 前置: E2166（先证明边界存在，再用本模式）, E2164（所有会被映射的副本必须构建期当场自签 + 禁写缓存红线）
- 相关: E135, E077
- 落地参考: `archives/b/barvinok/0.41.9/conanfile.py`（`_OHOS_ISL_PYTHON_LAUNCHER_SRC` / `_build_ohos_isl_python_launcher`）、PR #6848 #33932 全绿构建
