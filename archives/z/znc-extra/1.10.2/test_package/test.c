/* znc-extra 包校验：逐个检查 11 个模块 .so 的 ELF 元数据与导出符号。
 *
 * 为什么不直接 dlopen：这些模块引用的 ZNC 核心符号由 znc 宿主可执行文件导出
 * （上游 src/CMakeLists.txt 的 ENABLE_EXPORTS，宿主需以 --export-dynamic 链接），
 * 脱离宿主进程单独 dlopen 必然在符号解析阶段失败（实测报
 * "Error relocating ... CModInfo::t_s ..."）。因此在测试进程内改为校验模块自身
 * 的装载元数据：ELF 类型/架构、模块入口符号 ZNCModuleEntry 已定义、且存在未定义
 * 符号（证明核心符号留给宿主解析，而非被静态打包进模块）。
 */
#include <dirent.h>
#include <elf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

/* 与配方 EXTRA_MODULES 一致（Alpine community/znc 的 znc-extra 子包内容） */
static const char *MODULES[] = {
    "autovoice",       "block_motd", "clearbufferonmsg", "ctcpflood",
    "flooddetach",     "imapauth",   "listsockets",      "log",
    "notify_connect",  "send_raw",   "shell",
};
#define NMODULES ((int)(sizeof(MODULES) / sizeof(MODULES[0])))

#define MODULE_ENTRY "ZNCModuleEntry"
#define EM_AARCH64_ELF 183

static int read_at(FILE *fp, long off, void *buf, size_t size) {
    if (fseek(fp, off, SEEK_SET) != 0) {
        return 0;
    }
    return fread(buf, 1, size, fp) == size;
}

/* 返回 0 表示通过 */
static int check_module(const char *dir, const char *name) {
    char path[4096];
    snprintf(path, sizeof(path), "%s/%s.so", dir, name);

    struct stat st;
    if (stat(path, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        printf("FAIL %-18s 模块文件缺失或为空: %s\n", name, path);
        return 1;
    }

    FILE *fp = fopen(path, "rb");
    if (!fp) {
        printf("FAIL %-18s 无法打开\n", name);
        return 1;
    }

    Elf64_Ehdr eh;
    if (!read_at(fp, 0, &eh, sizeof(eh)) ||
        memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0 ||
        eh.e_ident[EI_CLASS] != ELFCLASS64 ||
        eh.e_ident[EI_DATA] != ELFDATA2LSB ||
        eh.e_type != ET_DYN || (int)eh.e_machine != EM_AARCH64_ELF) {
        printf("FAIL %-18s 非 AArch64 ELF 共享对象 (e_type=%d e_machine=%d)\n",
               name, (int)eh.e_type, (int)eh.e_machine);
        fclose(fp);
        return 1;
    }

    if (eh.e_shnum == 0 || eh.e_shentsize != sizeof(Elf64_Shdr)) {
        printf("FAIL %-18s 段表异常\n", name);
        fclose(fp);
        return 1;
    }

    Elf64_Shdr *shdrs = calloc(eh.e_shnum, sizeof(Elf64_Shdr));
    if (!shdrs || !read_at(fp, (long)eh.e_shoff, shdrs,
                           (size_t)eh.e_shnum * sizeof(Elf64_Shdr))) {
        printf("FAIL %-18s 段表读取失败\n", name);
        free(shdrs);
        fclose(fp);
        return 1;
    }

    const Elf64_Shdr *dynsym = NULL;
    int i;
    for (i = 0; i < (int)eh.e_shnum; i++) {
        if (shdrs[i].sh_type == SHT_DYNSYM) {
            dynsym = &shdrs[i];
            break;
        }
    }
    if (!dynsym || dynsym->sh_link >= eh.e_shnum) {
        printf("FAIL %-18s 无 .dynsym\n", name);
        free(shdrs);
        fclose(fp);
        return 1;
    }
    const Elf64_Shdr *strtab = &shdrs[dynsym->sh_link];

    char *strs = calloc(1, (size_t)strtab->sh_size + 1);
    Elf64_Sym *syms = calloc(1, (size_t)dynsym->sh_size);
    size_t nsyms = (size_t)dynsym->sh_size / sizeof(Elf64_Sym);
    if (!strs || !syms || !read_at(fp, (long)strtab->sh_offset, strs, (size_t)strtab->sh_size) ||
        !read_at(fp, (long)dynsym->sh_offset, syms, (size_t)dynsym->sh_size)) {
        printf("FAIL %-18s 动态符号表读取失败\n", name);
        free(strs);
        free(syms);
        free(shdrs);
        fclose(fp);
        return 1;
    }

    int entry_defined = 0;
    size_t undefined = 0, j;
    for (j = 0; j < nsyms; j++) {
        if (syms[j].st_shndx == SHN_UNDEF) {
            undefined++;
            continue;
        }
        if (syms[j].st_name < strtab->sh_size &&
            strcmp(strs + syms[j].st_name, MODULE_ENTRY) == 0) {
            entry_defined = 1;
        }
    }

    int rc = 0;
    if (!entry_defined) {
        printf("FAIL %-18s 未导出 %s\n", name, MODULE_ENTRY);
        rc = 1;
    } else if (undefined == 0) {
        printf("FAIL %-18s 无未定义符号（核心符号未留给宿主解析）\n", name);
        rc = 1;
    } else {
        printf("PASS %-18s ET_DYN/aarch64, %s 已导出, 未定义符号 %zu 个\n",
               name, MODULE_ENTRY, undefined);
    }

    free(strs);
    free(syms);
    free(shdrs);
    fclose(fp);
    return rc;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <module-dir>\n", argv[0]);
        return 2;
    }
    const char *dir = argv[1];
    int failures = 0, i;

    for (i = 0; i < NMODULES; i++) {
        failures += check_module(dir, MODULES[i]);
    }

    /* 目录里不应出现本子包之外的 .so（znc 主包才交付基础模块） */
    DIR *d = opendir(dir);
    if (!d) {
        printf("FAIL 无法打开模块目录 %s\n", dir);
        failures++;
    } else {
        int so_count = 0;
        struct dirent *ent;
        while ((ent = readdir(d)) != NULL) {
            size_t len = strlen(ent->d_name);
            if (len > 3 && strcmp(ent->d_name + len - 3, ".so") == 0) {
                so_count++;
            }
        }
        closedir(d);
        if (so_count != NMODULES) {
            printf("FAIL 模块目录 .so 数量 %d，期望 %d\n", so_count, NMODULES);
            failures++;
        } else {
            printf("PASS 模块目录 .so 数量 %d\n", so_count);
        }
    }

    printf("== znc-extra 模块校验：%d/%d 通过，失败 %d 项 ==\n",
           NMODULES - failures, NMODULES, failures);
    return failures == 0 ? 0 : 1;
}
