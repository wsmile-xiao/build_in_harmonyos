/* libasm 0.195 —— 端到端消费者用例（鸿蒙特有，完整流程非纯断言）：
 *
 *   libasm 生成汇编源文件
 *     → OHOS 工具链 as(1) 把汇编源汇编成目标文件
 *     → readelf(1) 解析目标文件节表
 *     → 程序内校验 .text 节存在且含预期数据字节
 *
 * 真正跑通"生成→汇编→产物验证"完整流程，覆盖 libasm 的核心消费场景
 * （作为汇编器库产出可供工具链消费的汇编代码）。
 */
#include <elfutils/libasm.h>
#include <gelf.h>

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

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

/* 运行外部命令，返回退出状态；stdout/stderr 透传（便于 CI 日志诊断） */
static int run_cmd(const char *cmd) {
  int status = system(cmd);
  if (status < 0)
    return -1;
  return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

int main(void) {
  const char *asmfile = "e2e-out.s";
  const char *objfile = "e2e-out.o";
  unlink(asmfile);
  unlink(objfile);

  CHECK(elf_version(EV_CURRENT) != EV_NONE, "elf_version 初始化");

  /* ── 阶段 1：libasm 生成汇编源文件（text 模式）── */
  AsmCtx_t *ctx = asm_begin(asmfile, NULL, true);
  CHECK(ctx != NULL, "阶段1: asm_begin(text) 创建上下文");
  if (ctx == NULL)
    return 1;

  AsmScn_t *scn = asm_newscn(ctx, ".text", SHT_PROGBITS, 0);
  CHECK(scn != NULL, "阶段1: asm_newscn(.text)");
  if (scn == NULL) {
    asm_end(ctx);
    return 1;
  }

  /* 写一段有语义的数据：'A' 'T' 标记 + 版本号，供产物校验。
   * 只用 .byte：libasm text 模式对 16 位量发 `.value` 伪指令，
   * OHOS 的 as(1) 不认（GNU as 扩展），故 0x0195 拆成两个字节。 */
  int rc = 0;
  rc |= asm_adduint8(scn, 0x41);       /* 'A' */
  rc |= asm_adduint8(scn, 0x54);       /* 'T' */
  rc |= asm_adduint8(scn, 0x01);       /* 版本 0.195 标记（高字节） */
  rc |= asm_adduint8(scn, 0x95);       /* 版本 0.195 标记（低字节） */
  rc |= asm_align(scn, 8);
  CHECK(rc == 0, "阶段1: 写入标记数据(0x41,0x54,0x0195)+对齐");

  CHECK(asm_end(ctx) == 0, "阶段1: asm_end 生成汇编源文件");

  /* ── 阶段 2：交给工具链 as(1) 汇编成目标文件 ── */
  char cmd[512];
  snprintf(cmd, sizeof(cmd), "as %s -o %s 2>&1", asmfile, objfile);
  int as_rc = run_cmd(cmd);
  CHECK(as_rc == 0, "阶段2: as(1) 汇编源文件为目标文件");

  if (as_rc != 0) {
    fprintf(stderr, "--- as 失败，汇编源内容如下 ---\n");
    run_cmd("cat e2e-out.s");
    unlink(asmfile);
    return 1;
  }

  /* ── 阶段 3：readelf 解析 + 程序内读产物校验 ── */
  snprintf(cmd, sizeof(cmd), "readelf -S %s > e2e-readelf.txt 2>&1", objfile);
  CHECK(run_cmd(cmd) == 0, "阶段3: readelf -S 解析目标文件节表");

  FILE *f = fopen("e2e-readelf.txt", "r");
  CHECK(f != NULL, "阶段3: readelf 输出可读");
  if (f != NULL) {
    char buf[8192];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    CHECK(strstr(buf, ".text") != NULL, "阶段3: 目标文件含 .text 节");
  }

  /* 程序内用 libelf 直接读目标文件，校验 .text 内容为预期字节 */
  int fd = open(objfile, O_RDONLY);
  Elf *elf = fd >= 0 ? elf_begin(fd, ELF_C_READ_MMAP, NULL) : NULL;
  CHECK(elf != NULL, "阶段3: elf_begin 读目标文件");
  if (elf != NULL) {
    size_t shstrndx = 0;
    Elf_Scn *section = NULL;
    Elf_Scn *text = NULL;
    CHECK(elf_getshdrstrndx(elf, &shstrndx) == 0, "阶段3: 获取节名字符串表索引");
    while ((section = elf_nextscn(elf, section)) != NULL) {
      GElf_Shdr shdr;
      if (gelf_getshdr(section, &shdr) == NULL)
        continue;
      char *name = elf_strptr(elf, shstrndx, shdr.sh_name);
      if (name != NULL && strcmp(name, ".text") == 0) {
        text = section;
        break;
      }
    }
    CHECK(text != NULL, "阶段3: libelf 定位 .text 节");
    if (text != NULL) {
      Elf_Data *data = elf_getdata(text, NULL);
      CHECK(data != NULL && data->d_size >= 4, "阶段3: .text 数据非空");
      if (data != NULL && data->d_size >= 4) {
        const unsigned char *bytes = data->d_buf;
        CHECK(bytes[0] == 0x41 && bytes[1] == 0x54,
              "阶段3: .text 首字节为标记 'A''T'");
      }
    }
    elf_end(elf);
  }
  if (fd >= 0)
    close(fd);

  unlink(asmfile);
  unlink(objfile);
  unlink("e2e-readelf.txt");

  if (failures != 0) {
    fprintf(stderr, "\n%d assertion(s) failed\n", failures);
    return 1;
  }
  printf("\ne2e PASS: libasm 生成汇编 → as 汇编 → readelf/elf_begin 校验全流程通过\n");
  return 0;
}
