// test_package 入口 2 — libint2 C API（C ABI）消费者测试
//
// 覆盖 C++ 入口覆盖不到的 C ABI 面：
//   1) libint2_build_* 内核分发表已由 libint2_static_init() 注册（链接期完整性）
//   2) libint2_need_memory_* 内存需求查询（返回值单位是 LIBINT2_REALTYPE 元素个数）
//   3) 调用方自备 buffer 的 init/cleanup 生命周期契约
//
// 数值正确性由上游单元测试（tests/unit/c-api.c、test-c-api.cc）与入口 1/3 覆盖，
// 本入口不重复断言数值。

#include <libint2.h>
#include <libint2/config.h>

#include <stdio.h>
#include <stdlib.h>

#if !defined(LIBINT2_REALTYPE)
#define LIBINT2_REALTYPE double
#endif

static int failures = 0;

static void check(int ok, const char* what) {
  printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
  if (!ok) ++failures;
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);

  libint2_static_init();

  // ---- 1) 内核分发表 ----
  // 注：上游 1 电子表自 [0][1] 起注册（l=0 的 (s|s) 不在表中），这是上游行为，不是缺失。
  check(libint2_build_overlap[0][1] != NULL, "C API: (s|p) overlap 内核已注册");
  check(libint2_build_overlap[1][1] != NULL, "C API: (p|p) overlap 内核已注册");
  check(libint2_build_overlap[2][2] != NULL, "C API: (d|d) overlap 内核已注册");
  check(libint2_build_kinetic[1][1] != NULL, "C API: (p|p) kinetic 内核已注册");
  check(libint2_build_elecpot[2][2] != NULL, "C API: (d|d) elecpot 内核已注册");
  check(libint2_build_1emultipole[1][1] != NULL, "C API: (p|p) 1 电子多极矩内核已注册");
  check(libint2_build_2emultipole[1][1] != NULL, "C API: (p|p) 2 电子多极矩内核已注册");
  check(libint2_build_eri[0][0][0][0] != NULL, "C API: (ss|ss) ERI 内核已注册");
  check(libint2_build_eri[1][1][1][1] != NULL, "C API: (pp|pp) ERI 内核已注册");
  check(libint2_build_eri[2][2][2][2] != NULL, "C API: (dd|dd) ERI 内核已注册");
  check(libint2_build_3eri[1][1][1] != NULL, "C API: (sp|s) 3 中心 ERI 内核已注册");
  check(libint2_build_2eri[1][1] != NULL, "C API: (sp) 2 中心 ERI 内核已注册");

  // ---- 2) 内存需求查询 ----
  // libint2_need_memory_eri 返回的是 LIBINT2_REALTYPE **元素个数**（不是字节数），
  // 调用方须按 need * sizeof(LIBINT2_REALTYPE) 分配。
  const size_t need = libint2_need_memory_eri(2);
  check(need > 0, "C API: libint2_need_memory_eri(2) > 0");
  check(libint2_need_memory_eri(3) > need,
        "C API: libint2_need_memory_eri 随 max_am 单调增长");

  // ---- 3) 生命周期：调用方自备 buffer ----
  // init 记录调用方指针（inteval->stack = buf），cleanup 负责 free 并置空；
  // 即 buffer 移交给库后，调用方不得再次 free。
  void* buf = malloc(need * sizeof(LIBINT2_REALTYPE));
  check(buf != NULL, "C API: 调用方 buffer 分配成功");
  if (buf != NULL) {
    Libint_t erieval;
    libint2_init_eri(&erieval, 2, buf);
    check(erieval.stack == (LIBINT2_REALTYPE*)buf,
          "C API: init_eri 采用调用方提供的 buffer");
    libint2_cleanup_eri(&erieval);
    check(erieval.stack == NULL, "C API: cleanup_eri 释放 buffer 并置空指针");
  }

  libint2_static_cleanup();

  printf("failures = %d\n", failures);
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
