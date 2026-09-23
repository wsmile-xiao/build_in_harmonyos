// test_package 入口 4 — pkg-config 消费契约
//
// 本文件**不**由 CMake 构建，而是由 test_package/conanfile.py 的 test() 用
// `pkg-config --cflags libint2` / `pkg-config --libs libint2` 的返回值直接编译。
// 因此它验证的是安装出来的 libint2.pc 本身是否可用
// （上游模板经 CMake 渲染后前缀/版本为空，本配方在 package() 里重写，此处是回归守卫）。

#include <libint2.h>

#include <stdio.h>
#include <stdlib.h>

int main(void) {
  libint2_static_init();

  const size_t need = libint2_need_memory_eri(1);
  if (need == 0) {
    fprintf(stderr, "pkg-config consumer: libint2_need_memory_eri(1) == 0\n");
    return EXIT_FAILURE;
  }
  printf("[PASS] pkg-config consumer: C API 可用 (need_memory_eri(1) = %zu)\n", need);

  libint2_static_cleanup();
  return EXIT_SUCCESS;
}
