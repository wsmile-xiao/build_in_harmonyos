# E547 — make 变量名含 `+` 无法用命令行赋值覆盖(C++=x 被解析为变量 C+ 的追加)

> Status: DRAFT | 实例: cbflib 0.9.7(HarmonyOS PC 构建 OHOS AArch64)
> severity 🟠 2 | category: build-system, make

## 错误特征

```text
g++ -O3 ... examples/cif2c.c ... -o bin/cif2c
bash: line 1: g++: command not found
make: *** [Makefile:2038: .../bin/cif2c] Error 127
```

## 触发条件

- 上游 makefile 以 `C++ = g++` 声明 C++ 编译器(变量名含 `+`);
- 适配者在 make 命令行传 `C++=clang++` 期望覆盖。

## 根因

GNU make 解析命令行赋值时,把紧邻 `=` 的 `+` 识别为追加操作符:参数
`C++=x` 被拆成「变量名 `C+`、操作符 `+=`、值 `=x`」,makefile 内的
`C++ = g++` 照常生效。实测(make 4.4.1):

```sh
printf 'C++ = g++\nall:\n\t@echo [${C++}]\n' > mtest.mk
make -f mtest.mk 'C++=clang++'        # 输出 [g++],覆盖失败
env 'C++=clang++' make -e -f mtest.mk # 输出 [clang++]
```

## 修复(已验证)

1. 模板改为 `C++	?= g++`(`?=` 视环境变量为已定义,语义不变);
2. 用 `env 'C++=/path/clang++' make ...` 传入——`env(1)` 可设置含 `+`
   的非法 shell 变量名,无需 `-e`。

cbflib 0.9.7 补丁 0001 后,test_package 与上游 basic/extra/dectristests 全绿。

## 相关

- causes: clang++ 覆盖不生效 → 继续调 g++ → OHOS 环境无 g++ 报 Error 127
- caused_by: 变量名含 `+` + 上游硬编码 `= g++`
