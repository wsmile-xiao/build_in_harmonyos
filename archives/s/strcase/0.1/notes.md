# strcase 0.1 adaptation notes (GLM-42, 2026-09-17)

- 任务: 13621; 平台: strcase/0.1 (开源鸿蒙PC专项积分赛-依赖); 分支 feat/strcase-0.1
- 上游: https://github.com/rd235/strcase archive/refs/tags/0.1.tar.gz
  sha256=f881a2a29abc38841b84f0f6d1386bcd00cde9035c485366265faade9f142956
- 定位: randmac 0.2（任务 9987，GLM-46 名下）的硬依赖——randmac.c `#include <strcase.h>` 且
  CMake configure 阶段 check_include_file(strcase.h) 缺失即 FATAL_ERROR。本包先行适配供其 requires。
- 构建体系: 上游 CMakeLists 仅 install strcase.h + man 页，无编译 target、无测试。
- 补丁: 无（零补丁）。
- 依赖: 无（仅 libc 的 stdint/ctype）。
- 测试账本（四维）:
  - 上游静态注册: 0（单头文件库无任何测试目标）
  - 实际执行/通过/失败: 0/0/0/0（上游无测试，依规以消费者测试补位）
  - 消费者测试: test_package/test.c 1 个程序，5 项断言：
    ①dispatch("DUMP")→dump（strcase_tolower 运行时折叠 + STRCASE 编译期 case 常量）
    ②dispatch("Load")→load ③dispatch("bogus")→unknown（default 分支）
    ④strcase("abc")==STRCASE(a,b,c)（运行时函数与编译期宏常量一致）
    ⑤strcase_tolower("aBc")==strcase_tolower("abc")（大小写折叠）
- packaging: include/strcase.h + licenses/COPYING；header-library，package_id 清空。
- 已知限制: 仅前 8 字节有效（上游设计如此）；C 模式 STRCASE 仅支持字母/数字/下划线裸单词，
  其他符号需用名字（如 STRCASE(slash,e,t,c)）。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 12:11
**最终状态**: built
