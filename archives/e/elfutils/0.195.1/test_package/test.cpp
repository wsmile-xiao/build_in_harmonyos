#include <stdint.h>
#include <stddef.h>
#include <libelf.h>
#include <gelf.h>
#include <elfutils/libdw.h>
#include <elfutils/libdwfl.h>
#include <elfutils/debuginfod.h>

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <unistd.h>

// elfutils 0.195.1 —— 真实 ELF/DWARF 解析 + 真实 libdebuginfod 客户端库验证
// （非 dlopen 空壳）。
// libelf/libdw 部分被测对象选**自己这个可执行文件**：它一定存在、一定是
// aarch64 ELF、且带 -g 编出来时有 DWARF，比造一个假 ELF 更有说服力。
//   ① elf_version 初始化（版本不匹配 libelf 会拒绝工作）
//   ② elf_begin 打开自身，判定为 ELF_K_ELF
//   ③ EHDR：机器类型 = EM_AARCH64、class = ELFCLASS64
//   ④ 遍历 section，按名字找到 .text 并断言其为 SHT_PROGBITS 且可执行
//   ⑤ 数出 section 总数并与 EHDR 里的 e_shnum 对账
//   ⑥ libdw：dwfl 打开自身、按地址反查模块名（证明 libdw 真能用，不只是能链）
//   ⑦ 错误路径：对非 ELF 文件 elf_begin 必须判为非 ELF_K_ELF
//   ⑧ libdebuginfod：0.195.1 的核心变更 —— 本包提供的必须是**真实客户端库**。
//      判据是 debuginfod_begin() 返回可用句柄：上游 dummy 形态（0.195 用的
//      --enable-libdebuginfod=dummy）在该函数里直接
//      `errno = ENOSYS; return NULL;`（debuginfod/debuginfod-client.c:64）。
//      其余断言走离线路径：清空 DEBUGINFOD_URLS 后 find_* 在访问缓存与网络
//      **之前**就返回 -ENOSYS（debuginfod-client.c:1822-1829）。

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

int main(int argc, char **argv) {
  // ①
  CHECK(elf_version(EV_CURRENT) != EV_NONE, "elf_version(EV_CURRENT) 初始化成功");

  const char *self = argv[0];
  int fd = open(self, O_RDONLY);
  CHECK(fd >= 0, "打开自身可执行文件");
  if (fd < 0) return 1;

  // ② ③ ④ ⑤
  Elf *e = elf_begin(fd, ELF_C_READ, nullptr);
  CHECK(e != nullptr, "elf_begin 成功");
  if (e) {
    CHECK(elf_kind(e) == ELF_K_ELF, "elf_kind == ELF_K_ELF");

    GElf_Ehdr ehdr;
    CHECK(gelf_getehdr(e, &ehdr) != nullptr, "gelf_getehdr 取到 EHDR");
    CHECK(ehdr.e_machine == 183 /* EM_AARCH64 */, "e_machine == EM_AARCH64(183)");
    if (ehdr.e_machine != 183)
      std::fprintf(stderr, "       实得 %u\n", ehdr.e_machine);
    CHECK(gelf_getclass(e) == ELFCLASS64, "ELF class 为 64 位");

    size_t shstrndx = 0;
    CHECK(elf_getshdrstrndx(e, &shstrndx) == 0, "取到 section 名字符串表下标");

    // 遍历 section
    size_t n_sec = 0;
    bool text_ok = false;
    Elf_Scn *scn = nullptr;
    while ((scn = elf_nextscn(e, scn)) != nullptr) {
      ++n_sec;
      GElf_Shdr shdr;
      if (gelf_getshdr(scn, &shdr) == nullptr) continue;
      const char *nm = elf_strptr(e, shstrndx, shdr.sh_name);
      if (nm && std::strcmp(nm, ".text") == 0) {
        text_ok = (shdr.sh_type == SHT_PROGBITS) && (shdr.sh_flags & SHF_EXECINSTR);
        if (!text_ok)
          std::fprintf(stderr, "       .text type=%u flags=0x%llx\n",
                       shdr.sh_type, (unsigned long long)shdr.sh_flags);
      }
    }
    CHECK(text_ok, ".text 存在且为 SHT_PROGBITS + SHF_EXECINSTR");
    size_t shnum = 0;
    elf_getshdrnum(e, &shnum);
    CHECK(n_sec + 1 == shnum || n_sec == shnum,
          "遍历到的 section 数与 elf_getshdrnum 对账");
    if (!(n_sec + 1 == shnum || n_sec == shnum))
      std::fprintf(stderr, "       遍历=%zu getshdrnum=%zu\n", n_sec, shnum);
    std::printf("     section 数=%zu\n", n_sec);

    elf_end(e);
  }
  close(fd);

  // ⑥ libdw / libdwfl：按地址反查模块
  {
    static const Dwfl_Callbacks cb = {
        dwfl_linux_proc_find_elf,
        dwfl_standard_find_debuginfo,
        nullptr,
        nullptr,
    };
    Dwfl *dwfl = dwfl_begin(&cb);
    CHECK(dwfl != nullptr, "dwfl_begin 成功");
    if (dwfl) {
      const int rc = dwfl_linux_proc_report(dwfl, getpid());
      CHECK(rc == 0, "dwfl_linux_proc_report 读取自身进程映射成功");
      dwfl_report_end(dwfl, nullptr, nullptr);
      if (rc == 0) {
        // 用本函数的地址反查模块
        Dwarf_Addr addr = reinterpret_cast<Dwarf_Addr>(&main);
        Dwfl_Module *mod = dwfl_addrmodule(dwfl, addr);
        CHECK(mod != nullptr, "dwfl_addrmodule 按 main 的地址查到模块");
        if (mod) {
          const char *nm = dwfl_module_info(mod, nullptr, nullptr, nullptr,
                                            nullptr, nullptr, nullptr, nullptr);
          CHECK(nm != nullptr && std::strlen(nm) > 0,
                "dwfl_module_info 返回非空模块名");
          if (nm) std::printf("     模块名=%s\n", nm);
        }
      }
      dwfl_end(dwfl);
    }
  }

  // ⑦ 错误路径
  {
    const char *txt = "not_an_elf.txt";
    FILE *f = std::fopen(txt, "w");
    if (f) { std::fputs("plain text, definitely not ELF\n", f); std::fclose(f); }
    int bad = open(txt, O_RDONLY);
    if (bad >= 0) {
      Elf *be = elf_begin(bad, ELF_C_READ, nullptr);
      CHECK(be == nullptr || elf_kind(be) != ELF_K_ELF,
            "非 ELF 文件不被判为 ELF_K_ELF");
      if (be) elf_end(be);
      close(bad);
    }
    std::remove(txt);
  }

  // ⑧ libdebuginfod 真实客户端库（0.195.1 的核心变更）
  {
    CHECK(std::strcmp(DEBUGINFOD_SONAME, "libdebuginfod.so.1") == 0,
          "[debuginfod] DEBUGINFOD_SONAME == libdebuginfod.so.1");

    // 离线确定性：清空服务端列表，find_* 将在触碰缓存/网络前返回 -ENOSYS；
    // 缓存目录指向调用方给的可写目录（argv[1]），避免测试进程去写 HOME
    unsetenv(DEBUGINFOD_URLS_ENV_VAR);
    if (argc > 1 && argv[1] != nullptr && argv[1][0] != '\0') {
      setenv(DEBUGINFOD_CACHE_PATH_ENV_VAR, argv[1], 1);
    }

    errno = 0;
    debuginfod_client *client = debuginfod_begin();
    CHECK(client != nullptr,
          "[debuginfod] debuginfod_begin() 返回可用句柄（dummy 形态此处返回 NULL）");
    if (client == nullptr) {
      std::fprintf(stderr, "       errno=%d —— 疑似 dummy libdebuginfod\n", errno);
    } else {
      CHECK(debuginfod_get_url(client) == nullptr,
            "[debuginfod] get_url() 传输前为 NULL");
      CHECK(debuginfod_get_headers(client) == nullptr,
            "[debuginfod] get_headers() 传输前为 NULL");

      static void *marker = reinterpret_cast<void *>(0x5a17);
      debuginfod_set_user_data(client, marker);
      CHECK(debuginfod_get_user_data(client) == marker,
            "[debuginfod] set/get_user_data 往返一致");

      CHECK(debuginfod_add_http_header(client, "X-Elfutils-Probe: 1") == 0,
            "[debuginfod] add_http_header 接受合法头");

      debuginfod_set_progressfn(client, debuginfod_default_progressfn);
      CHECK(debuginfod_default_progressfn(client, 0, 0) == 0,
            "[debuginfod] default_progressfn 返回 0");

      const char *build_id = "0123456789abcdef0123456789abcdef01234567";
      char *path = nullptr;
      CHECK(debuginfod_find_debuginfo(
                client, reinterpret_cast<const unsigned char *>(build_id), 0,
                &path) == -ENOSYS,
            "[debuginfod] find_debuginfo 无服务端时 -ENOSYS");
      CHECK(debuginfod_find_executable(
                client, reinterpret_cast<const unsigned char *>(build_id), 0,
                &path) == -ENOSYS,
            "[debuginfod] find_executable 无服务端时 -ENOSYS");
      CHECK(debuginfod_find_source(
                client, reinterpret_cast<const unsigned char *>(build_id), 0,
                "main.c", &path) == -ENOSYS,
            "[debuginfod] find_source 无服务端时 -ENOSYS");
      CHECK(debuginfod_find_metadata(client, "buildid", build_id, &path)
                == -ENOSYS,
            "[debuginfod] find_metadata 无服务端时 -ENOSYS");

      debuginfod_end(client);
      debuginfod_end(nullptr);  // 上游对 NULL 有保护（debuginfod-client.c:2632）
      CHECK(true, "[debuginfod] debuginfod_end 释放完成且不崩溃");
    }
  }

  if (failures) {
    std::fprintf(stderr, "\nelfutils: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nelfutils 0.195.1: 全部断言通过"
              "（libelf + libdw + 真实 libdebuginfod 均已真实调用）\n");
  return 0;
}
