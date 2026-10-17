# draft-clownresampler-3.24-single-header-static-macro-hides-api

## 症状

单头文件 C 库的消费者测试（test_package）在包含公开头文件时，编译出现多条
`implicit-function-declaration` 警告，但链接仍然成功、ctest 也能通过：

```
warning: call to undeclared function 'ClownResampler_Precompute'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
warning: call to undeclared function 'ClownResampler_LowLevel_Init'; ...
warning: call to undeclared function 'ClownResampler_LowLevel_Resample'; ...
3 warnings generated.
```

clang 15 默认 C99+ 只报警告不报错；链接因预编译库存在而成功，测试"碰巧通过"，
但 API 签名实际未经过校验，属于静默风险。

## 根因

单头文件库用 `STATIC` / `IMPLEMENTATION` 宏控制"声明 vs 定义"与符号可见性：

```c
#if !defined(CLOWNRESAMPLER_STATIC) || defined(CLOWNRESAMPLER_IMPLEMENTATION)
/* ... 全部公开函数声明区 ... */
#endif
```

消费者（尤其 test_package 自动生成的测试代码）容易按"静态链接"的直觉误定义
`CLOWNRESAMPLER_STATIC`。此时声明区整体被条件编译隐藏：类型与部分宏仍然可见，
但所有函数声明不可见，编译器走隐式声明路径。

## 修复

消费者只 include 公开头文件、不定义任何内部配置宏，并链接预编译库：

```c
#include "clownresampler.h"   /* 不定义 CLOWNRESAMPLER_STATIC / IMPLEMENTATION */

int main(void) {
    ClownResampler_Precompute(&precomputed);          /* 声明可见 */
    ClownResampler_LowLevel_Init(&resampler, ...);    /* 声明可见 */
    ClownResampler_LowLevel_Resample(&resampler, ...);
}
```

若确需单 TU 内联使用单头实现，则在恰好一个编译单元定义
`CLOWNRESAMPLER_IMPLEMENTATION`（获得声明+定义），此时不应再链接预编译库，避免符号重复。

## 可跨库复用的要点

- stb 风格单头文件库（`XX_IMPLEMENTATION`/`XX_STATIC` 宏族）的消费者测试均适用。
- test_package 验证的是"外部消费者视角"：只暴露公开头文件 + 链接产物，配置宏是库内部
  使用方式，消费者不应触碰。
- 出现 `implicit-function-declaration` 警告即应视为 API 可见性配置错误，不要因链接通过
  而忽略。

## 验证

clownresampler 3.24：test_package 原模板 test.c 定义 `CLOWNRESAMPLER_STATIC` 后编译出现
3 条 undeclared-function 警告（链接与 ctest 1/1 Passed，警告被静默）；去掉 STATIC 宏后
无警告重新 conan create，ctest 1/1 Passed，消费者验证通过（8000→16000Hz 上采样，输出帧
数验证）。证据日志：`archives/c/clownresampler/3.24/reports/conan-create.log`。
