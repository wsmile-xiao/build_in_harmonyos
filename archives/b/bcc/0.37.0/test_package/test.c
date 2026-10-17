/*
 * test_package consumer test — bcc 0.37.0
 *
 * R34: test_package must actually use the packaged library. Calls the public
 * C API from installed headers (bcc_common.h / bcc_elf.h) and checks the
 * observable result: rw-engine capability query and ELF load-section walk.
 */
#include <stdio.h>
#include <bcc/bcc_common.h>
#include <bcc/bcc_elf.h>

static int ls_cb(uint64_t vma, uint64_t memsz, uint64_t offset, void *p) {
  int *n = (int *)p;
  (void)vma; (void)memsz; (void)offset;
  (*n)++;
  return 0;
}

int main(void) {
  int fail = 0;

  int rw = bpf_module_rw_engine_enabled();
  printf("bpf_module_rw_engine_enabled() = %d\n", rw);
  if (rw != 1) {
    fprintf(stderr, "FAIL: rw engine query\n");
    fail++;
  }

  int n = 0;
  int rc = bcc_elf_foreach_load_section("/proc/self/exe", ls_cb, &n);
  printf("bcc_elf_foreach_load_section(/proc/self/exe) rc=%d sections=%d\n",
         rc, n);
  if (rc != 0 || n <= 0) {
    fprintf(stderr, "FAIL: ELF load-section walk\n");
    fail++;
  }

  if (fail == 0) {
    printf("test bcc 0.37.0: OK\n");
    return 0;
  }
  printf("test bcc 0.37.0: FAIL\n");
  return 1;
}
