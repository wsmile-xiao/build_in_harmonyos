# SLICOT：`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 让能力探测失真

> 配套结构化条目：`DRAFT-slicot-cmake-try-compile-static-breaks-capability-probes.kv`

## 现象

SLICOT 5.9.1 在 OHOS 上编译库本体成功，但构建 examples（242 个 CTest 驱动）时
链接失败：

```
ld.lld: error: undefined symbol: dgegv_
ld.lld: error: undefined symbol: dlatzm_
ld.lld: error: undefined symbol: zgegv_
ld.lld: error: undefined symbol: zlatzm_
```

## 背景：为什么 OHOS 要设 `STATIC_LIBRARY`

Fortran 交叉编译在 OHOS 必须设置（flang-ohos 精简运行集无法完成链接探针）：

```cmake
CMAKE_SYSTEM_NAME            = Linux
CMAKE_TRY_COMPILE_TARGET_TYPE = STATIC_LIBRARY
CMAKE_C_COMPILER_FORCED      = TRUE
```

## 根因：探测退化为"只编译"，任何符号都被判"存在"

上游 `src/CMakeLists.txt` 用**函数存在性探测**决定是否编译自带的老 LAPACK 例程：

```cmake
INCLUDE(CheckFortranFunctionExists)

MACRO(ADD_ROUTINE_IF_REQUIRED ROUTINE VAR SOURCE_FILE)
    SET(CMAKE_REQUIRED_LIBRARIES PRIVATE BLAS::BLAS LAPACK::LAPACK)
    Check_Fortran_Function_Exists(${ROUTINE} ${VAR})
    IF (NOT ${VAR})
        SET(SOURCES ${SOURCES} ${SOURCE_FILE})   # 用自带实现
    ENDIF()
ENDMACRO()

ADD_ROUTINE_IF_REQUIRED(dgegv HAVE_DGEGV lapack_aux/dgegv.f)
# ... zgegv / dlatzm / zlatzm / dgegs / zgegs 同
```

`Check_Fortran_Function_Exists` 的实现是**编译并链接**一个引用该符号的小程序。
但 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 让它**只编译**（不链接），
于是**任何符号都会被判定为存在** → 6 个副本都不编译 → 最终链接 undefined。

## 修法：显式钉住探测结果

LAPACK 3.12 确实已移除这 6 个例程，所以把探测结果直接钉为 FALSE，
强制上游编译自带的 `lapack_aux/*.f`：

```python
for var in ("HAVE_DGEGS", "HAVE_ZGEGS", "HAVE_DLAZTM", "HAVE_ZLAZTM",
            "HAVE_DGEGV", "HAVE_ZGEGV"):
    tc.cache_variables[var] = False
```

并直接给出 BLAS/LAPACK 的包内静态库路径（避开环境探测）：

```python
tc.variables["BLAS_LIBRARIES"]   = "<blas>/lib/libblas.a"
tc.variables["LAPACK_LIBRARIES"] = "<lapack>/lib/liblapack.a"
```

## 通用教训

**凡是设置了 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 的平台，
所有"链接型"CMake 能力探测 (`Check_*_Function_Exists`、`check_symbol_exists`
的链接分支、`try_run` 等) 都不可信。** 遇到上游用它们做功能分支的工程，
必须按实际依赖情况**显式钉值**，不能依赖探测结果。

## 其它要点

- `SLICOT_TESTING` 只在**顶层工程**生效（`IF(CMAKE_CURRENT_SOURCE_DIR
  STREQUAL CMAKE_SOURCE_DIR)`），conan create 正是顶层，故 242 个 CTest 会构建。
- OHOS 上 make jobserver FIFO 创建失败 → `CMAKE_BUILD_PARALLEL_LEVEL=1`。
- 上游测试结果：`100% tests passed, 0 tests failed out of 242`。
- 消费者验证：用 flang 把真实 Fortran 程序链接到**已打包**的 `libslicot.a`
  （断言 `MA02AD` 转置结果），输出 `SLICOT-CONSUMER-OK`。
