/*
 * bcc 0.37.0 OHOS 消费者用例 (consumer use case)
 *
 * 模拟业务上层组件/应用：仅通过 bcc 库已安装/导出的公开头文件与公开 C API
 * 使用该三方库，验证第三方使用者能否编译、链接、调用并正常运行。
 *
 * 调用的公开 API（均为用户态、不依赖内核 BPF syscall，本设备实测可用）：
 *   - bpf_module_rw_engine_enabled()        (bcc_common.h) 查询 rw-engine 能力
 *   - bcc_elf_foreach_load_section()        (bcc_elf.h) 遍历 ELF 可执行加载段
 *   - bcc_elf_foreach_usdt()                (bcc_elf.h) 扫描二进制中的 USDT 探针
 *   - bcc_elf_foreach_sym()                 (bcc_elf.h) 遍历 ELF 符号表
 *
 * 验证结果：各 API 返回码与可观察计数输出（RESULT: PASS/FAIL）。
 * 说明：OHOS 无内核 BPF syscall 与内核头，BPF 程序加载类 API 无法在本设备
 * 运行（见 notes.md 上游测试台账）；本用例聚焦库的用户态 ELF/能力查询公开
 * API，覆盖有业务意义的公开调用及其可观察结果。
 */
#include <stdio.h>
#include <string.h>
#include <elf.h>
#include <bcc/bcc_common.h>
#include <bcc/bcc_elf.h>
#include <bcc/bcc_syms.h>

static int load_sec_count_cb(uint64_t vma, uint64_t memsz, uint64_t offset,
                             void *payload) {
  int *count = (int *)payload;
  (void)vma; (void)memsz; (void)offset;
  (*count)++;
  return 0;
}

static void usdt_count_cb(const char *path, const struct bcc_elf_usdt *u,
                          void *payload) {
  int *count = (int *)payload;
  (void)path; (void)u;
  (*count)++;
}

static int sym_count_cb(const char *name, uint64_t start, uint64_t size,
                        void *payload) {
  int *count = (int *)payload;
  (void)start; (void)size;
  if (name && name[0])
    (*count)++;
  return 0;
}

int main(int argc, char **argv) {
  int failures = 0;
  /* 未指定目标文件时，用本程序自身作为 ELF 解析对象 */
  const char *target = argc > 1 ? argv[1] : argv[0];

  /* 1. 公开 API：rw-engine 是否启用（用户态能力查询，可观察） */
  {
    int rw = bpf_module_rw_engine_enabled();
    printf("[consumer] bpf_module_rw_engine_enabled() = %d\n", rw);
    if (rw != 1)
      failures++;
  }

  /* 2. 公开 API：遍历 ELF 可执行加载段（有业务意义的 ELF 解析能力） */
  {
    int count = 0;
    int rc = bcc_elf_foreach_load_section(target, load_sec_count_cb, &count);
    printf("[consumer] bcc_elf_foreach_load_section(%s) rc=%d sections=%d\n",
           target ? target : "(self)", rc, count);
    if (rc != 0 || count <= 0)
      failures++;
  }

  /* 3. 公开 API：扫描 USDT 探针（trace 工具链核心能力的用户态部分） */
  {
    int count = 0;
    int rc = bcc_elf_foreach_usdt(target, usdt_count_cb, &count);
    printf("[consumer] bcc_elf_foreach_usdt(%s) rc=%d usdt=%d\n",
           target ? target : "(self)", rc, count);
    if (rc != 0)
      failures++;
  }

  /* 4. 公开 API：遍历 ELF 符号表（对自身二进制，用户态 ELF 解析）
        参数槽位：第 3 参 option 传显式 bcc_symbol_option（bcc_elf_foreach_sym
        会无条件写 option->lazy_symbolize，不能传 NULL），第 4 参 payload 传
        计数指针（回调第 4 参即 payload），并校验 count>0 防止假通过。 */
  {
    int count = 0;
    struct bcc_symbol_option opt;
    memset(&opt, 0, sizeof(opt));
    opt.use_symbol_type = (1 << STT_FUNC) | (1 << STT_OBJECT) | (1 << STT_NOTYPE);
    int rc = bcc_elf_foreach_sym(target, sym_count_cb, &opt, &count);
    printf("[consumer] bcc_elf_foreach_sym(%s) rc=%d symbols=%d\n",
           target ? target : "(self)", rc, count);
    if (rc != 0 || count <= 0)
      failures++;
  }

  printf("[consumer] RESULT: %s (%d failures)\n",
         failures == 0 ? "PASS" : "FAIL", failures);
  return failures == 0 ? 0 : 1;
}
