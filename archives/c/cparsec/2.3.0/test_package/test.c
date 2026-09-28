// cparsec 2.3.0 test_package 消费者测试 (R34: 必须实质调用被测包 API)
//
// 仅通过 cparsec 安装/导出的公开头文件 cparsec.h 与公开 API 使用该库，
// 模拟业务上层组件：定义解析器、调用 cpc_arena_init / CPC_PARSE /
// cpc_slice_from_cstr / cpc_val_list_at 等公开接口，并验证可观察结果。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cparsec.h"

// 文件作用域声明解析器（clang 不支持函数体内嵌套函数定义）
CPC_STRING(p_start, "BEGIN")

int main(void) {
  // 公开 API: 初始化 arena（无 libc 假设）
  CpcArena arena;
  CpcValue arena_storage[64];
  cpc_arena_init(&arena, arena_storage, sizeof(arena_storage) / sizeof(arena_storage[0]), NULL);

  // 公开 API: cpc_slice_from_cstr + CPC_PARSE 运行解析器
  const char input[] = "BEGIN leftovers";
  CpcSlice  slice = cpc_slice_from_cstr(input);
  CpcResult result = CPC_PARSE(p_start, slice, &arena);

  if (!result.ok) {
    fprintf(stderr, "FAIL: parse did not succeed\n");
    return EXIT_FAILURE;
  }

  // 验证公开结果字段: 输出切片内容与剩余输入
  if (result.out.as.slice.len != 5 || strncmp(result.out.as.slice.ptr, "BEGIN", 5) != 0) {
    fprintf(stderr, "FAIL: unexpected parsed output\n");
    return EXIT_FAILURE;
  }

  if (result.rest.len != 10 || strncmp(result.rest.ptr, " leftovers", 10) != 0) {
    fprintf(stderr, "FAIL: unexpected rest\n");
    return EXIT_FAILURE;
  }

  printf("test cparsec 2.3.0: OK (parsed %.*s, rest %.*s)\n",
         (int)result.out.as.slice.len, result.out.as.slice.ptr,
         (int)result.rest.len, result.rest.ptr);
  return EXIT_SUCCESS;
}