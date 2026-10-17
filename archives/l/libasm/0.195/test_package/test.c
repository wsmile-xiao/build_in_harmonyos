#include <elfutils/libasm.h>
#include <gelf.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* libasm 0.195 —— 真实 API 调用验证（非 dlopen/打印空壳）。
 *
 * 被测对象是 libasm 的汇编器上下文 API。binary 输出模式需要 Ebl 描述符
 * （ebl_openbackend_machine），而 libebl 是 elfutils 内部的便利库、不随
 * 发行包安装；libasm 的 textp=true 文本汇编输出模式无需 Ebl，可直接使用，
 * 故本测试用它来真实驱动：
 *   ① elf_version 初始化
 *   ② asm_begin 创建汇编上下文（text 模式）
 *   ③ asm_newscn 新建 .text 节
 *   ④ asm_adduint8/asm_adduint16/asm_addsleb128/asm_align 写数据
 *   ⑤ asm_end 收尾并落盘
 *   ⑥ 回读输出文件，断言非空且含期望的汇编指令文本
 *   ⑦ 错误路径：asm_begin(NULL, NULL, false) 必须失败（fname 缺失）
 */
static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__);      \
      ++failures;                                                            \
    } else {                                                                 \
      printf("[ok] %s\n", msg);                                              \
    }                                                                        \
  } while (0)

int main(void) {
  const char *outfile = "asm-probe.s";
  unlink(outfile);

  /* ① */
  CHECK(elf_version(EV_CURRENT) != EV_NONE, "elf_version(EV_CURRENT) 初始化成功");

  /* ⑦ 错误路径：fname==NULL 且非 text 模式 -> asm_begin 返回 NULL */
  CHECK(asm_begin(NULL, NULL, false) == NULL, "asm_begin(NULL,NULL,false) 按预期失败");

  /* ② text 模式创建汇编上下文 */
  AsmCtx_t *ctx = asm_begin(outfile, NULL, true);
  CHECK(ctx != NULL, "asm_begin(textp=true) 创建上下文");
  if (ctx == NULL)
    return 1;

  /* ③ */
  AsmScn_t *scn = asm_newscn(ctx, ".text", SHT_PROGBITS, 0);
  CHECK(scn != NULL, "asm_newscn(.text) 新建节");
  if (scn == NULL) {
    asm_end(ctx);
    return 1;
  }

  /* ④ */
  CHECK(asm_adduint8(scn, 0x2a) == 0, "asm_adduint8(0x2a)");
  CHECK(asm_adduint16(scn, 0x1234) == 0, "asm_adduint16(0x1234)");
  CHECK(asm_addsleb128(scn, -5) == 0, "asm_addsleb128(-5)");
  CHECK(asm_adduleb128(scn, 0x1f) == 0, "asm_adduleb128(0x1f)");
  CHECK(asm_align(scn, 8) == 0, "asm_align(8)");

  /* ⑤ */
  int rc = asm_end(ctx);
  CHECK(rc == 0, "asm_end 收尾成功");

  /* ⑥ 回读输出 */
  FILE *f = fopen(outfile, "r");
  CHECK(f != NULL, "asm_end 已生成输出文件");
  if (f != NULL) {
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fclose(f);
    CHECK(sz > 0, "输出文件非空");

    char buf[4096];
    size_t n = 0;
    f = fopen(outfile, "r");
    if (f != NULL) {
      n = fread(buf, 1, sizeof(buf) - 1, f);
      fclose(f);
    }
    buf[n] = '\0';
    CHECK(strstr(buf, ".text") != NULL, "输出含 .text 节指令");
    CHECK(strstr(buf, "2a") != NULL || strstr(buf, "42") != NULL,
          "输出含 adduint8 数据（0x2a）");
  }

  unlink(outfile);
  if (failures != 0) {
    fprintf(stderr, "\n%d assertion(s) failed\n", failures);
    return 1;
  }
  printf("\nall libasm API assertions passed\n");
  return 0;
}
