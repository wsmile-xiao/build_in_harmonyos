/*
 * cde-static-bundler - offline static environment-bundling CLI (auxiliary tool).
 *
 * Boundary (read this carefully):
 *   This tool is an OFFLINE PACKAGING AID bundled with CDE 0.1 for the
 *   feat/cde-1.0.0 branch.  It performs STATIC ELF metadata analysis and
 *   explicit resource-root copying ONLY.  It is NOT CDE 0.1's dynamic
 *   tracing mechanism, it does not use ptrace, LD_PRELOAD, runtime
 *   interception, process tracing, or a debugger, and it CANNOT bypass the
 *   OHOS ptrace policy established in R05/R06.  It must never execute the
 *   ELF under inspection.
 *
 * Usage:
 *   cde-static-bundler scan --entry <ELF> --resource-root <dir> \
 *       [--libdir <dir> ...] [--output <bundle-dir>]
 *
 * Behavior summary:
 *   1. Parse ELF metadata statically (class, byte order, machine,
 *      interpreter, DT_NEEDED, DT_RPATH, DT_RUNPATH).  Reject
 *      malformed/non-ELF input and unsupported mixed architecture.
 *   2. Resolve non-system DT_NEEDED dependencies recursively using only
 *      safe declared lookup locations.  Record all graph edges.  System
 *      libraries are listed as exclusions and never copied.  Required
 *      unresolved non-system dependencies are a hard failure with a clear
 *      manifest/report entry.
 *   3. Copy only the entry, resolved non-system dependency files, and
 *      files physically inside explicitly supplied --resource-root
 *      directories.  Reject path traversal, absolute destination escape,
 *      unsafe relative paths, and symlink escapes.  Prefer materializing
 *      regular files in the bundle instead of making output symlinks.
 *   4. Emit <bundle-dir>/manifest.json containing the input entry,
 *      architecture, interpreter, dependency graph, copied files with
 *      origin and SHA-256, system exclusions, unresolved dependencies,
 *      supplied resource roots, and tool/version metadata.  The manifest
 *      never declares a successful complete bundle when a required
 *      dependency is unresolved.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#include <elf.h>

#define TOOL_NAME    "cde-static-bundler"
#define TOOL_VERSION "1.0.0"

/* ------------------------------------------------------------------ */
/* SHA-256 (FIPS 180-4), self-contained.                              */
/* ------------------------------------------------------------------ */

typedef struct {
    uint32_t state[8];
    uint64_t bitlen;
    uint8_t  data[64];
    size_t   datalen;
} sha256_ctx;

static const uint32_t sha256_k[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

static uint32_t sha256_rotr(uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }

static void sha256_transform(sha256_ctx *c, const uint8_t block[64]) {
    uint32_t w[64], a, b, cc, d, e, f, g, h, t1, t2;
    unsigned i;
    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)block[i*4] << 24) | ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] << 8)  | (uint32_t)block[i*4+3];
    for (i = 16; i < 64; i++) {
        uint32_t s0 = sha256_rotr(w[i-15],7) ^ sha256_rotr(w[i-15],18) ^ (w[i-15] >> 3);
        uint32_t s1 = sha256_rotr(w[i-2],17) ^ sha256_rotr(w[i-2],19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    a = c->state[0]; b = c->state[1]; cc = c->state[2]; d = c->state[3];
    e = c->state[4]; f = c->state[5]; g = c->state[6]; h = c->state[7];
    for (i = 0; i < 64; i++) {
        uint32_t S1 = sha256_rotr(e,6) ^ sha256_rotr(e,11) ^ sha256_rotr(e,25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t S0 = sha256_rotr(a,2) ^ sha256_rotr(a,13) ^ sha256_rotr(a,22);
        uint32_t maj = (a & b) ^ (a & cc) ^ (b & cc);
        t1 = h + S1 + ch + sha256_k[i] + w[i];
        t2 = S0 + maj;
        h = g; g = f; f = e; e = d + t1; d = cc; cc = b; b = a; a = t1 + t2;
    }
    c->state[0] += a; c->state[1] += b; c->state[2] += cc; c->state[3] += d;
    c->state[4] += e; c->state[5] += f; c->state[6] += g; c->state[7] += h;
}

static void sha256_init(sha256_ctx *c) {
    c->state[0] = 0x6a09e667; c->state[1] = 0xbb67ae85;
    c->state[2] = 0x3c6ef372; c->state[3] = 0xa54ff53a;
    c->state[4] = 0x510e527f; c->state[5] = 0x9b05688c;
    c->state[6] = 0x1f83d9ab; c->state[7] = 0x5be0cd19;
    c->bitlen = 0; c->datalen = 0;
}

static void sha256_update(sha256_ctx *c, const uint8_t *data, size_t len) {
    size_t i;
    for (i = 0; i < len; i++) {
        c->data[c->datalen++] = data[i];
        if (c->datalen == 64) {
            sha256_transform(c, c->data);
            c->bitlen += 512;
            c->datalen = 0;
        }
    }
}

static void sha256_final(sha256_ctx *c, uint8_t out[32]) {
    uint64_t bitlen = c->bitlen + (uint64_t)c->datalen * 8;
    uint8_t pad = 0x80;
    uint8_t zero = 0x00;
    uint8_t lenbuf[8];
    unsigned i;
    sha256_update(c, &pad, 1);
    while (c->datalen != 56)
        sha256_update(c, &zero, 1);
    for (i = 0; i < 8; i++)
        lenbuf[i] = (uint8_t)(bitlen >> (56 - i*8));
    sha256_update(c, lenbuf, 8);
    for (i = 0; i < 8; i++) {
        out[i*4]   = (uint8_t)(c->state[i] >> 24);
        out[i*4+1] = (uint8_t)(c->state[i] >> 16);
        out[i*4+2] = (uint8_t)(c->state[i] >> 8);
        out[i*4+3] = (uint8_t)(c->state[i]);
    }
}

/* Compute hex SHA-256 of a file; returns 0 on success. */
static int sha256_file(const char *path, char hex[65]) {
    int fd = open(path, O_RDONLY);
    uint8_t buf[8192], digest[32];
    sha256_ctx c;
    ssize_t n;
    unsigned i;
    if (fd < 0) return -1;
    sha256_init(&c);
    while ((n = read(fd, buf, sizeof(buf))) > 0)
        sha256_update(&c, buf, (size_t)n);
    close(fd);
    if (n < 0) return -1;
    sha256_final(&c, digest);
    for (i = 0; i < 32; i++)
        sprintf(hex + i*2, "%02x", digest[i]);
    hex[64] = '\0';
    return 0;
}

/* ------------------------------------------------------------------ */
/* ELF metadata model (static parse only; never executes the ELF).    */
/* ------------------------------------------------------------------ */

#define MAX_DEPS CDE_BUNDLER_MAX_DEPS
#ifndef CDE_BUNDLER_MAX_DEPS
#define CDE_BUNDLER_MAX_DEPS 512
#endif
#ifndef CDE_BUNDLER_MAX_LIBDIRS
#define CDE_BUNDLER_MAX_LIBDIRS 64
#endif
#ifndef CDE_BUNDLER_MAX_RESROOTS
#define CDE_BUNDLER_MAX_RESROOTS 64
#endif
#ifndef CDE_BUNDLER_MAX_QUEUE
#define CDE_BUNDLER_MAX_QUEUE 1024
#endif
#ifndef CDE_BUNDLER_MAX_GRAPH_CHARS
#define CDE_BUNDLER_MAX_GRAPH_CHARS 16384
#endif
#ifndef CDE_BUNDLER_MAX_COPIED_CHARS
#define CDE_BUNDLER_MAX_COPIED_CHARS 65536
#endif
#ifndef CDE_BUNDLER_MAX_EXCLUDED_CHARS
#define CDE_BUNDLER_MAX_EXCLUDED_CHARS 8192
#endif
#ifndef CDE_BUNDLER_MAX_UNRESOLVED_CHARS
#define CDE_BUNDLER_MAX_UNRESOLVED_CHARS 8192
#endif
#ifndef CDE_BUNDLER_MAX_RESROOTS_CHARS
#define CDE_BUNDLER_MAX_RESROOTS_CHARS 8192
#define MAX_OWNED_DEST 128
#endif
/* Short aliases for existing code referencing the old names. */
#define MAX_LIBDIRS CDE_BUNDLER_MAX_LIBDIRS
#define MAX_RESROOTS CDE_BUNDLER_MAX_RESROOTS

typedef struct {
    char name[256];            /* DT_NEEDED soname */
    char resolved[PATH_MAX];   /* resolved absolute path, "" if unresolved */
    int  system_lib;           /* 1 = excluded system library, never copied */
    int  unresolved_required;  /* 1 = required but unresolved */
} dep_t;

typedef struct {
    char entry_path[PATH_MAX];
    char entry_abspath[PATH_MAX];
    unsigned char elf_class;       /* ELFCLASS32/64 */
    unsigned char elf_data;        /* ELFDATA2LSB/MSB */
    uint16_t      e_machine;
    char arch_name[64];
    char interpreter[PATH_MAX];
    dep_t deps[MAX_DEPS];
    int   ndeps;
    int   deps_truncated;          /* 1 = DT_NEEDED count exceeded MAX_DEPS */
    char  rpath[PATH_MAX];
    char  runpath[PATH_MAX];
    int   has_rpath;
    int   has_runpath;
    char  entry_sha256[65];
} elf_info_t;

/* Read whole file into heap buffer. */
static uint8_t *read_file_buf(const char *path, size_t *len_out) {
    FILE *f = fopen(path, "rb");
    uint8_t *buf;
    long sz;
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return NULL; }
    buf = malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        free(buf); fclose(f); return NULL;
    }
    fclose(f);
    *len_out = (size_t)sz;
    return buf;
}

static const char *arch_name_of(uint16_t m) {
    switch (m) {
    case EM_386:   return "i386";
    case EM_X86_64:return "x86_64";
    case EM_AARCH64:return "aarch64";
    case EM_ARM:   return "arm";
    case EM_RISCV: return "riscv";
    default:       return "unknown";
    }
}

/* Parse ELF header + program headers + dynamic section.  Returns 0 on
 * success, non-zero with errmsg set on any malformed/non-ELF input. */
static int parse_elf(const char *path, elf_info_t *ei, char errmsg[512]) {
    uint8_t *buf;
    size_t   len;
    int      rc = -1;
    unsigned phcount = 0, phsize = 0;
    size_t   phoff = 0, shoff = 0;
    memset(ei, 0, sizeof(*ei));
    snprintf(ei->entry_path, sizeof(ei->entry_path), "%s", path);

    buf = read_file_buf(path, &len);
    if (!buf) {
        snprintf(errmsg, 512, "cannot read %s: %s", path, strerror(errno));
        return -1;
    }
    if (len < EI_NIDENT + 2 || memcmp(buf, ELFMAG, 4) != 0) {
        snprintf(errmsg, 512, "%s is not an ELF file (bad magic)", path);
        free(buf);
        return -1;
    }
    ei->elf_class = buf[EI_CLASS];
    ei->elf_data  = buf[EI_DATA];
    if (ei->elf_class != ELFCLASS32 && ei->elf_class != ELFCLASS64) {
        snprintf(errmsg, 512, "%s: unsupported ELF class %u", path, ei->elf_class);
        free(buf);
        return -1;
    }
    if (ei->elf_data != ELFDATA2LSB) {
        snprintf(errmsg, 512, "%s: unsupported byte order %u (only little-endian ELFDATA2LSB is supported; this target is AArch64-LE)", path, ei->elf_data);
        free(buf);
        return -1;
    }
    if (ei->elf_class == ELFCLASS64) {
        Elf64_Ehdr *h = (Elf64_Ehdr *)buf;
        if (len < sizeof(Elf64_Ehdr)) { snprintf(errmsg,512,"%s: truncated ELF64 header",path); free(buf); return -1; }
        ei->e_machine = h->e_machine;
        phoff = h->e_phoff; phsize = h->e_phentsize; phcount = h->e_phnum; shoff = h->e_shoff;
    } else {
        Elf32_Ehdr *h = (Elf32_Ehdr *)buf;
        if (len < sizeof(Elf32_Ehdr)) { snprintf(errmsg,512,"%s: truncated ELF32 header",path); free(buf); return -1; }
        ei->e_machine = h->e_machine;
        phoff = h->e_phoff; phsize = h->e_phentsize; phcount = h->e_phnum; shoff = h->e_shoff;
    }
    snprintf(ei->arch_name, sizeof(ei->arch_name), "%s", arch_name_of(ei->e_machine));

         /* R47: validate program-header table bounds before pointer arithmetic.
          * Reject phoff wraparound, oversized table count, invalid entry size
          * and table-extends-beyond-file for both ELF64 and ELF32. */
         {
             size_t phdr_size = (ei->elf_class == ELFCLASS64) ? sizeof(Elf64_Phdr) : sizeof(Elf32_Phdr);
             if (phsize == 0 || phsize < phdr_size) {
                 fprintf(stderr, "%s: %s: invalid program header entry size %u (expected >= %zu)\n",
                         TOOL_NAME, path, phsize, phdr_size);
                 free(buf); return -1;
             }
             if (phoff >= len) {
                 fprintf(stderr, "%s: %s: program header offset %zu out of file (%zu bytes)\n",
                         TOOL_NAME, path, (size_t)phoff, len);
                 free(buf); return -1;
             }
             if (phcount > 65535 || (size_t)phcount > (len - phoff) / phsize) {
                 fprintf(stderr, "%s: %s: program header count %u exceeds file range\n",
                         TOOL_NAME, path, phcount);
                 free(buf); return -1;
             }
         }

         /* Program headers: PT_INTERP and PT_DYNAMIC */
    {
        unsigned i;
        size_t dyn_off = 0, dyn_size = 0;
        size_t interp_off = 0, interp_size = 0;
        if (ei->elf_class == ELFCLASS64) {
            for (i = 0; i < phcount; i++) {
                Elf64_Phdr *p;
                if (phoff + (size_t)(i+1)*phsize > len) break;
                p = (Elf64_Phdr *)(buf + phoff + (size_t)i*phsize);
                /* R44: reject program segment whose p_offset+p_filesz would
                 * overflow or exceed the file length */
                if (p->p_filesz > (Elf64_Xword)len - (p->p_offset < (Elf64_Off)len ? p->p_offset : (Elf64_Off)len)) {
                    fprintf(stderr, "%s: %s: program header segment offset/size out of file range\n",
                            TOOL_NAME, path);
                    free(buf); return -1;
                }
                if (p->p_type == PT_INTERP)  { interp_off = p->p_offset; interp_size = p->p_filesz; }
                if (p->p_type == PT_DYNAMIC) { dyn_off = p->p_offset; dyn_size = p->p_filesz; }
            }
        } else {
            for (i = 0; i < phcount; i++) {
                Elf32_Phdr *p;
                if (phoff + (size_t)(i+1)*phsize > len) break;
                p = (Elf32_Phdr *)(buf + phoff + (size_t)i*phsize);
                /* R44: same bounds check for ELF32 program headers */
                if (p->p_filesz > (Elf32_Word)len - (p->p_offset < (Elf32_Off)len ? p->p_offset : (Elf32_Off)len)) {
                    fprintf(stderr, "%s: %s: program header segment offset/size out of file range\n",
                            TOOL_NAME, path);
                    free(buf); return -1;
                }
                if (p->p_type == PT_INTERP)  { interp_off = p->p_offset; interp_size = p->p_filesz; }
                if (p->p_type == PT_DYNAMIC) { dyn_off = p->p_offset; dyn_size = p->p_filesz; }
            }
        }
        if (interp_off && interp_off < len && interp_size > 0 &&
                interp_size <= len - interp_off) {
            size_t n = interp_size;
            if (n >= sizeof(ei->interpreter)) n = sizeof(ei->interpreter) - 1;
            memcpy(ei->interpreter, buf + interp_off, n);
            ei->interpreter[n] = '\0';
        }
        if (dyn_off && dyn_off < len) {
            /* find DT_STRTAB */
            size_t strtab_off = 0, strtab_size = 0;
            unsigned j, ndyn;
            size_t dt_off;
            if (ei->elf_class == ELFCLASS64) {
                ndyn = (unsigned)(dyn_size / sizeof(Elf64_Dyn));
                for (j = 0; j < ndyn; j++) {
                    Elf64_Dyn *d;
                    if (dyn_off + (size_t)(j+1)*sizeof(Elf64_Dyn) > len) break;
                    d = (Elf64_Dyn *)(buf + dyn_off + (size_t)j*sizeof(Elf64_Dyn));
                    if (d->d_tag == DT_STRTAB) { strtab_off = (size_t)d->d_un.d_ptr; break; }
                }
            } else {
                ndyn = (unsigned)(dyn_size / sizeof(Elf32_Dyn));
                for (j = 0; j < ndyn; j++) {
                    Elf32_Dyn *d;
                    if (dyn_off + (size_t)(j+1)*sizeof(Elf32_Dyn) > len) break;
                    d = (Elf32_Dyn *)(buf + dyn_off + (size_t)j*sizeof(Elf32_Dyn));
                    if (d->d_tag == DT_STRTAB) { strtab_off = (size_t)d->d_un.d_ptr; break; }
                }
            }
            /* DT_STRTAB d_ptr is a virtual address; we must map it to a file
             * offset via PT_LOAD.  For typical small tools the vaddr equals
             * file offset when p_vaddr == p_offset (common for ET_EXEC/ET_DYN
             * linked with no gap), but to be safe find the containing PT_LOAD. */
            {
                unsigned k;
                size_t load_vaddr = 0, load_offset = 0;
                if (ei->elf_class == ELFCLASS64) {
                    for (k = 0; k < phcount; k++) {
                        Elf64_Phdr *p;
                        if (phoff + (size_t)(k+1)*phsize > len) break;
                        p = (Elf64_Phdr *)(buf + phoff + (size_t)k*phsize);
                        if (p->p_type == PT_LOAD && strtab_off >= (size_t)p->p_vaddr &&
                            strtab_off < (size_t)p->p_vaddr + p->p_filesz) {
                            load_vaddr = (size_t)p->p_vaddr;
                            load_offset = (size_t)p->p_offset;
                            break;
                        }
                    }
                } else {
                    for (k = 0; k < phcount; k++) {
                        Elf32_Phdr *p;
                        if (phoff + (size_t)(k+1)*phsize > len) break;
                        p = (Elf32_Phdr *)(buf + phoff + (size_t)k*phsize);
                        if (p->p_type == PT_LOAD && strtab_off >= (size_t)p->p_vaddr &&
                            strtab_off < (size_t)p->p_vaddr + p->p_filesz) {
                            load_vaddr = (size_t)p->p_vaddr;
                            load_offset = (size_t)p->p_offset;
                            break;
                        }
                    }
                }
                dt_off = strtab_off ? strtab_off - load_vaddr + load_offset : 0;
                strtab_size = (dt_off < len) ? len - dt_off : 0;
                (void)shoff; (void)dt_off;
                if (dt_off && dt_off < len) {
                    unsigned j2;
                    if (ei->elf_class == ELFCLASS64) {
                        for (j2 = 0; j2 < ndyn; j2++) {
                            Elf64_Dyn *d;
                            if (dyn_off + (size_t)(j2+1)*sizeof(Elf64_Dyn) > len) break;
                            d = (Elf64_Dyn *)(buf + dyn_off + (size_t)j2*sizeof(Elf64_Dyn));
                            if (d->d_tag == DT_NEEDED) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    if (ei->ndeps < MAX_DEPS) {
                                        const char *s = (const char *)(buf + dt_off + stroff);
                                        size_t n2 = strnlen(s, strtab_size - stroff);
                                        if (n2 < sizeof(ei->deps[ei->ndeps].name)) {
                                            memcpy(ei->deps[ei->ndeps].name, s, n2);
                                            ei->deps[ei->ndeps].name[n2] = '\0';
                                            ei->ndeps++;
                                        }
                                    } else {
                                        ei->deps_truncated = 1;
                                    }
                                }
                            } else if (d->d_tag == DT_RPATH) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    size_t n2 = strnlen((const char*)(buf+dt_off+stroff), strtab_size-stroff);
                                    if (n2 < sizeof(ei->rpath)) { memcpy(ei->rpath, buf+dt_off+stroff, n2); ei->rpath[n2]='\0'; ei->has_rpath=1; }
                                }
                            } else if (d->d_tag == DT_RUNPATH) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    size_t n2 = strnlen((const char*)(buf+dt_off+stroff), strtab_size-stroff);
                                    if (n2 < sizeof(ei->runpath)) { memcpy(ei->runpath, buf+dt_off+stroff, n2); ei->runpath[n2]='\0'; ei->has_runpath=1; }
                                }
                            }
                        }
                    } else {
                        for (j2 = 0; j2 < ndyn; j2++) {
                            Elf32_Dyn *d;
                            if (dyn_off + (size_t)(j2+1)*sizeof(Elf32_Dyn) > len) break;
                            d = (Elf32_Dyn *)(buf + dyn_off + (size_t)j2*sizeof(Elf32_Dyn));
                            if (d->d_tag == DT_NEEDED) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    if (ei->ndeps < MAX_DEPS) {
                                        const char *s = (const char *)(buf + dt_off + stroff);
                                        size_t n2 = strnlen(s, strtab_size - stroff);
                                        if (n2 < sizeof(ei->deps[ei->ndeps].name)) {
                                            memcpy(ei->deps[ei->ndeps].name, s, n2);
                                            ei->deps[ei->ndeps].name[n2] = '\0';
                                            ei->ndeps++;
                                        }
                                    } else {
                                        ei->deps_truncated = 1;
                                    }
                                }
                            } else if (d->d_tag == DT_RPATH) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    size_t n2 = strnlen((const char*)(buf+dt_off+stroff), strtab_size-stroff);
                                    if (n2 < sizeof(ei->rpath)) { memcpy(ei->rpath, buf+dt_off+stroff, n2); ei->rpath[n2]='\0'; ei->has_rpath=1; }
                                }
                            } else if (d->d_tag == DT_RUNPATH) {
                                size_t stroff = (size_t)d->d_un.d_val;
                                if (stroff < strtab_size) {
                                    size_t n2 = strnlen((const char*)(buf+dt_off+stroff), strtab_size-stroff);
                                    if (n2 < sizeof(ei->runpath)) { memcpy(ei->runpath, buf+dt_off+stroff, n2); ei->runpath[n2]='\0'; ei->has_runpath=1; }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    free(buf);
    (void)rc;
    return 0;
}

/* ------------------------------------------------------------------ */
/* System-library exclusion policy                                    */
/* ------------------------------------------------------------------ */

static int is_system_soname(const char *soname) {
    static const char *sys[] = {
        "libc.so", "libc.so.6", "libm.so", "libm.so.6", "libdl.so", "libdl.so.2",
        "libpthread.so", "libpthread.so.0", "librt.so", "librt.so.1",
        "libstdc++.so", "libstdc++.so.6", "libgcc_s.so", "libgcc_s.so.1",
        "libc++.so", "libc++.so.1", "libc++abi.so", "libc++abi.so.1",
        "libz.so", "libz.so.1", "ld-linux.so.2", "ld-linux-x86-64.so.2",
        "ld-musl-x86_64.so.1", "ld-musl-aarch64.so.1", "ld-linux-aarch64.so.1",
        "liblog.so", "libc_sec.so", "libsec_shared.so", "libhilog.so",
        NULL
    };
    int i;
    for (i = 0; sys[i]; i++)
        if (strcmp(soname, sys[i]) == 0) return 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* Safe path helpers                                                  */
/* ------------------------------------------------------------------ */

/* Join dir + "/" + name into out (PATH_MAX). */
static void path_join(const char *dir, const char *name, char out[PATH_MAX]) {
    if (dir[0] && dir[strlen(dir)-1] == '/')
        snprintf(out, PATH_MAX, "%s%s", dir, name);
    else
        snprintf(out, PATH_MAX, "%s/%s", dir, name);
}

/* Reject components "." ".." and embedded '/' in a single name. */
static int is_unsafe_component(const char *name) {
    return strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
           strchr(name, '/') != NULL || strchr(name, '\\') != NULL;
}

/* True if child path is physically inside root (realpath-based). */
static int path_within(const char *root_real, const char *candidate_real) {
    size_t n = strlen(root_real);
    if (strncmp(root_real, candidate_real, n) != 0) return 0;
    if (candidate_real[n] == '\0' || candidate_real[n] == '/') return 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* Bundle copy + manifest state                                       */
/* ------------------------------------------------------------------ */

typedef struct {
    char entry[PATH_MAX];
    char arch[64];
    char interpreter[PATH_MAX];
    char dep_graph[CDE_BUNDLER_MAX_GRAPH_CHARS];   /* JSON array of edges */
    char copied[CDE_BUNDLER_MAX_COPIED_CHARS];     /* JSON array of copied files */
    char excluded[CDE_BUNDLER_MAX_EXCLUDED_CHARS]; /* JSON array of system exclusions */
    char unresolved[CDE_BUNDLER_MAX_UNRESOLVED_CHARS]; /* JSON array of unresolved */
    char resroots[CDE_BUNDLER_MAX_RESROOTS_CHARS]; /* JSON array of resource roots */
    int  has_unresolved_required;
    int  capacity_fatal;       /* set when any traversal bookkeeping capacity is hit */
    char capacity_reason[256]; /* stable reason, e.g. dependency-closure-capacity-exceeded */
    int  entry_arch;           /* e_machine */
    int  n_owned_dest;         /* R52: per-run destination ownership set for resource-root collision */
    char owned_dest[128][PATH_MAX];
} manifest_t;

/* R52: forward declaration for JSON string escaping used by manifest
 * serialization helpers and fatal-capacity records. */
static int json_escape_buf(const char *s, char *buf, size_t buf_size);

/* Mark the traversal as fatally capacity-limited.  The manifest keeps any
 * graph/copy information already known, adds a manifest-visible record,
 * forces complete=false, and the process will exit non-zero. */
static void manifest_capacity_fatal(manifest_t *m, const char *what) {
    if (m->capacity_fatal) return;
    m->capacity_fatal = 1;
    m->has_unresolved_required = 1;
    snprintf(m->capacity_reason, sizeof(m->capacity_reason), "%s", what);
    {
        size_t n = strlen(m->unresolved);
        if (n + 400 < sizeof(m->unresolved)) {
            if (n > 0) { strncat(m->unresolved, ",\n", sizeof(m->unresolved) - n - 1); n = strlen(m->unresolved); }
            char esc_what[512];
            if (json_escape_buf(what, esc_what, sizeof(esc_what)) != 0) { /* fallback: use raw */ }
            snprintf(m->unresolved + n, sizeof(m->unresolved) - n,
                     "{\"reason\":\"dependency-closure-capacity-exceeded\",\"detail\":\"%s\"}", esc_what);
        }
    }
}

/* ------------------------------------------------------------------ */
/* Dependency resolution                                              */
/* ------------------------------------------------------------------ */

/* R47: forward declaration for JSON-escape buffer function used by
 * dep_graph_add, copy_resource_root, and write_manifest. */
static int json_escape_buf(const char *s, char *buf, size_t buf_size);

/* Record a graph edge "parent -> soname" (as JSON text). */
static void dep_graph_add(manifest_t *m, const char *parent, const char *soname) {
    size_t n = strlen(m->dep_graph);
    if (n + 512 < sizeof(m->dep_graph)) {
        if (n > 0) {
            strncat(m->dep_graph, ",\n", sizeof(m->dep_graph) - n - 1);
            n = strlen(m->dep_graph);
        }
        {
            char esc_parent[1024], esc_soname[1024];
            if (json_escape_buf(parent, esc_parent, sizeof(esc_parent)) != 0 ||
                json_escape_buf(soname, esc_soname, sizeof(esc_soname)) != 0) {
                manifest_capacity_fatal(m, "dependency-graph path too long for JSON");
                return;
            }
            snprintf(m->dep_graph + n, sizeof(m->dep_graph) - n,
                     "{\"parent\":\"%s\",\"need\":\"%s\"}", esc_parent, esc_soname);
        }
    } else {
        /* Graph buffer full: never silently drop an edge.  Fatal state. */
        manifest_capacity_fatal(m, "dependency graph buffer capacity exceeded");
    }
}

/* Attempt to locate `soname` in the declared lookup locations:
 *   1. directory of the entry ELF
 *   2. DT_RPATH / DT_RUNPATH entries (resolving $ORIGIN)
 *   3. --libdir directories supplied by the operator
 * Returns 0 with resolved path set, or -1 if not found. */
static int resolve_dep(const char *soname, const char *entry_dir,
                       const elf_info_t *ei, const char *libdirs[],
                       int nlibdirs, char out[PATH_MAX]) {
    char candidate[PATH_MAX];
    struct stat st;
    int i;

    path_join(entry_dir, soname, candidate);
    if (realpath(candidate, out) && stat(out, &st) == 0 && S_ISREG(st.st_mode))
        return 0;

    if (ei->has_runpath && ei->runpath[0]) {
        char *copy = strdup(ei->runpath);
        char *tok = strtok(copy, ":");
        while (tok) {
            char buf[PATH_MAX];
            if (strcmp(tok, "$ORIGIN") == 0) {
                snprintf(buf, sizeof(buf), "%s", entry_dir);
            } else if (strncmp(tok, "$ORIGIN/", 8) == 0) {
                snprintf(buf, sizeof(buf), "%s/%s", entry_dir, tok + 8);
            } else {
                snprintf(buf, sizeof(buf), "%s", tok);
            }
            path_join(buf, soname, candidate);
            if (realpath(candidate, out) && stat(out, &st) == 0 && S_ISREG(st.st_mode)) {
                free(copy);
                return 0;
            }
            tok = strtok(NULL, ":");
        }
        free(copy);
    }
    if (ei->has_rpath && ei->rpath[0]) {
        char *copy = strdup(ei->rpath);
        char *tok = strtok(copy, ":");
        while (tok) {
            char buf[PATH_MAX];
            if (strcmp(tok, "$ORIGIN") == 0) {
                snprintf(buf, sizeof(buf), "%s", entry_dir);
            } else if (strncmp(tok, "$ORIGIN/", 8) == 0) {
                snprintf(buf, sizeof(buf), "%s/%s", entry_dir, tok + 8);
            } else {
                snprintf(buf, sizeof(buf), "%s", tok);
            }
            path_join(buf, soname, candidate);
            if (realpath(candidate, out) && stat(out, &st) == 0 && S_ISREG(st.st_mode)) {
                free(copy);
                return 0;
            }
            tok = strtok(NULL, ":");
        }
        free(copy);
    }
    for (i = 0; i < nlibdirs; i++) {
        path_join(libdirs[i], soname, candidate);
        if (realpath(candidate, out) && stat(out, &st) == 0 && S_ISREG(st.st_mode))
            return 0;
    }
    return -1;
}

/* ------------------------------------------------------------------ */
/* Copy + safety policies                                             */
/* ------------------------------------------------------------------ */

static int mkdir_p(const char *dir) {
    char tmp[PATH_MAX];
    char *p;
    snprintf(tmp, sizeof(tmp), "%s", dir);
    for (p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(tmp, 0755) != 0 && errno != EEXIST) return -1;
            *p = '/';
        }
    }
    if (mkdir(tmp, 0755) != 0 && errno != EEXIST) return -1;
    return 0;
}

/* Copy a regular file into bundle at bundle_rel_path.  Rejects symlinks. */
static int copy_file_into_bundle(const char *src, const char *bundle_dir,
                                 const char *bundle_rel, char out_abs[PATH_MAX],
                                 char out_sha[65], int *copied_flag) {
    char dst[PATH_MAX];
    struct stat st;
    int in = -1, out = -1;
    uint8_t buf[8192];
    ssize_t n;
    sha256_ctx c;
    uint8_t digest[32];
    unsigned i;

    if (lstat(src, &st) != 0) return -1;
    if (!S_ISREG(st.st_mode)) return -1;          /* no symlinks, no dirs */
    if (sha256_file(src, out_sha) != 0) return -1;

    path_join(bundle_dir, bundle_rel, dst);
    if (mkdir_p(bundle_dir) != 0) return -1;
    {
        char *slash = strrchr(dst, '/');
        if (slash) {
            char dir[PATH_MAX];
            snprintf(dir, sizeof(dir), "%.*s", (int)(slash - dst), dst);
            if (mkdir_p(dir) != 0) return -1;
        }
    }
    in = open(src, O_RDONLY);
    if (in < 0) return -1;
    /* R47: reject pre-existing symlink destination (no-follow safety) */
    if (lstat(dst, &st) == 0 && S_ISLNK(st.st_mode)) {
        close(in); return -1;
    }
    out = open(dst, O_WRONLY | O_CREAT | O_TRUNC, 0755);
    if (out < 0) { close(in); return -1; }
    sha256_init(&c);
    while ((n = read(in, buf, sizeof(buf))) > 0) {
        sha256_update(&c, buf, (size_t)n);
        if (write(out, buf, (size_t)n) != n) { close(in); close(out); return -1; }
    }
    if (n < 0) { close(in); close(out); return -1; }
    sha256_final(&c, digest);
    for (i = 0; i < 32; i++)
        sprintf(out_sha + i*2, "%02x", digest[i]);
    out_sha[64] = '\0';
    close(in);
    close(out);
    if (realpath(dst, out_abs) == NULL)
        snprintf(out_abs, PATH_MAX, "%s", dst);
    *copied_flag = 1;
    return 0;
}

/* Recursively copy resource-root files into bundle/<resource-root basename>.
 * Only regular files physically inside the root are copied; symlinks and
 * dirent-escape candidates are rejected.  Sets *any_fail on any error. */
static int json_escape_buf(const char *s, char *buf, size_t buf_size);
static int copy_resource_root(const char *root, const char *bundle_dir,
                              manifest_t *m, int *any_fail) {
    DIR *d = opendir(root);
    struct dirent *e;
    char root_real[PATH_MAX];
    char root_abs[PATH_MAX];
    if (!d) { *any_fail = 1; return -1; }
    if (realpath(root, root_real) == NULL) { closedir(d); *any_fail = 1; return -1; }
    if (realpath(root, root_abs) == NULL) snprintf(root_abs, PATH_MAX, "%s", root);

    while ((e = readdir(d)) != NULL) {
        char src[PATH_MAX], src_real[PATH_MAX];
        struct stat st;
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) continue;
        if (is_unsafe_component(e->d_name)) { *any_fail = 1; continue; }
        path_join(root, e->d_name, src);
        if (lstat(src, &st) != 0) { *any_fail = 1; continue; }
        if (S_ISLNK(st.st_mode)) { *any_fail = 1; continue; }   /* reject symlink escapes */
        if (S_ISDIR(st.st_mode)) {
            char sub[PATH_MAX];
            path_join(root, e->d_name, sub);
            copy_resource_root(sub, bundle_dir, m, any_fail);
            continue;
        }
        if (!S_ISREG(st.st_mode)) continue;
        if (realpath(src, src_real) == NULL || !path_within(root_real, src_real)) {
            *any_fail = 1;
            continue;
        }
        {
            char rel[PATH_MAX], out_abs[PATH_MAX], sha[65];
            int copied = 0;
            snprintf(rel, sizeof(rel), "%s/%s", root_abs, e->d_name);
            /* flatten to basename-relative to avoid absolute destination escape */
            {
                char *base = strrchr(rel, '/');
                char dstrel[PATH_MAX];
                snprintf(dstrel, sizeof(dstrel), "resources/%s", e->d_name);
                /* R52: per-run destination ownership check — reject if this
                 * destination was already claimed in this run, regardless of
                 * pre-existing disk state.  A re-run to the same output dir
                 * with identical files is deterministic and succeeds. */
                {
                    int already_owned = 0;
                    int j;
                    for (j = 0; j < m->n_owned_dest; j++) {
                        if (strcmp(m->owned_dest[j], dstrel) == 0) { already_owned = 1; break; }
                    }
                    if (already_owned) {
                        fprintf(stderr, "%s: resource-root destination collision (this run): '%s'\n",
                                TOOL_NAME, e->d_name);
                        *any_fail = 1;
                        continue;
                    }
                    if (m->n_owned_dest < MAX_OWNED_DEST) {
                        strncat(m->owned_dest[m->n_owned_dest], dstrel, PATH_MAX - 1);
                        m->n_owned_dest++;
                    }
                }
                if (copy_file_into_bundle(src, bundle_dir, dstrel, out_abs, sha, &copied) == 0) {
                    size_t n = strlen(m->copied);
                    if (n + 700 < sizeof(m->copied)) {
                        char esc_origin[1024], esc_dest[1024];
                        if (json_escape_buf(src, esc_origin, sizeof(esc_origin)) != 0 ||
                            json_escape_buf(dstrel, esc_dest, sizeof(esc_dest)) != 0) {
                            manifest_capacity_fatal(m, "path too long for JSON serialization (resource root)");
                        } else {
                            if (n > 0) { strncat(m->copied, ",\n", sizeof(m->copied)-n-1); n = strlen(m->copied); }
                            snprintf(m->copied + n, sizeof(m->copied) - n,
                                     "{\"origin\":\"%s\",\"dest\":\"%s\",\"sha256\":\"%s\"}",
                                     esc_origin, esc_dest, sha);
                        }
                    } else {
                        manifest_capacity_fatal(m, "copied-file-record buffer capacity exceeded");
                    }
                } else {
                    *any_fail = 1;
                }
                (void)base;
            }
        }
    }
    closedir(d);
    return 0;
}

/* ------------------------------------------------------------------ */
/* Manifest emission                                                  */
/* ------------------------------------------------------------------ */

/* R47: JSON-escape a string into a fixed-size buffer. Returns 0 on success,
 * -1 if the escaped result would exceed buf_size. */
static int json_escape_buf(const char *s, char *buf, size_t buf_size) {
    size_t pos = 0;
    for (; *s; s++) {
        const char *esc = NULL;
        if (*s == '"') esc = "\\\"";
        else if (*s == '\\') esc = "\\\\";
        else if (*s == '\n') esc = "\\n";
        else if (*s == '\t') esc = "\\t";
        else if (*s == '\r') esc = "\\r";
        if (esc) {
            size_t elen = strlen(esc);
            if (pos + elen >= buf_size) return -1;
            memcpy(buf + pos, esc, elen);
            pos += elen;
        } else {
            if (pos + 1 >= buf_size) return -1;
            buf[pos++] = *s;
        }
    }
    buf[pos] = '\0';
    return 0;
}

static void json_escape(FILE *f, const char *s) {
    for (; *s; s++) {
        if (*s == '"' || *s == '\\') fprintf(f, "\\%c", *s);
        else if (*s == '\n') fputs("\\n", f);
        else fputc(*s, f);
    }
}

static int write_manifest(const char *bundle_dir, const manifest_t *m,
                          const char *toolver) {
    char path[PATH_MAX];
    FILE *f;
    path_join(bundle_dir, "manifest.json", path);
    f = fopen(path, "w");
    if (!f) return -1;
    fprintf(f, "{\n");
    fprintf(f, "  \"tool\": \"%s\",\n", TOOL_NAME);
    fprintf(f, "  \"tool_version\": \"%s\",\n", toolver);
    fprintf(f, "  \"entry\": \"");
    json_escape(f, m->entry);
    fprintf(f, "\",\n");
    fprintf(f, "  \"architecture\": \"%s\",\n", m->arch);
    fprintf(f, "  \"interpreter\": \"");
    json_escape(f, m->interpreter);
    fprintf(f, "\",\n");
    fprintf(f, "  \"complete\": %s,\n", m->has_unresolved_required ? "false" : "true");
    fprintf(f, "  \"dependency_graph\": [%s\n  ],\n", m->dep_graph);
    fprintf(f, "  \"copied_files\": [%s\n  ],\n", m->copied);
    fprintf(f, "  \"system_exclusions\": [%s\n  ],\n", m->excluded);
    fprintf(f, "  \"unresolved\": [%s\n  ],\n", m->unresolved);
    fprintf(f, "  \"resource_roots\": [%s\n  ]\n", m->resroots);
    fprintf(f, "}\n");
    fclose(f);
    return 0;
}

/* ------------------------------------------------------------------ */
/* main                                                               */
/* ------------------------------------------------------------------ */

static void usage(FILE *f) {
    fprintf(f,
        "cde-static-bundler %s - offline static environment-bundling CLI\n"
        "\n"
        "BOUNDARY: This is an offline packaging aid bundled with CDE 0.1.  It\n"
        "performs STATIC ELF metadata analysis and explicit resource-root copying\n"
        "only.  It is NOT CDE 0.1's dynamic tracing mechanism, does not use ptrace,\n"
        "LD_PRELOAD, runtime interception, process tracing, or a debugger, and it\n"
        "CANNOT bypass the OHOS ptrace policy established in R05/R06.  It never\n"
        "executes the ELF under inspection.\n"
        "\n"
        "Usage:\n"
        "  %s scan --entry <ELF> --resource-root <dir> [--resource-root <dir> ...]\n"
        "              [--libdir <dir> ...] [--output <bundle-dir>]\n"
        "\n"
        "Options:\n"
        "  --entry <ELF>          input ELF to analyze statically (required)\n"
        "  --resource-root <dir>  directory whose files are copied into the bundle\n"
        "                         (repeatable; must be physically inside-safe)\n"
        "  --libdir <dir>         extra declared lookup dir for non-system deps\n"
        "                         (repeatable)\n"
        "  --output <dir>         bundle output directory (default: ./cde-static-bundle)\n"
        "  -h, --help             show this help\n"
        "\n"
        "Outputs <output>/manifest.json; fails hard on unresolved required\n"
        "non-system dependencies or unsafe paths.\n",
        TOOL_VERSION, TOOL_NAME);
}

int main(int argc, char **argv) {
    const char *entry = NULL;
    const char *bundle_dir = "cde-static-bundle";
    const char *libdirs[MAX_LIBDIRS];
    const char *resroots[MAX_RESROOTS];
    int nlibdirs = 0, nresroots = 0;
    int i;
    elf_info_t *ei;
    char errmsg[512];
    char entry_dir[PATH_MAX], entry_real[PATH_MAX];
    manifest_t m;
    char toolver[128];

    memset(libdirs, 0, sizeof(libdirs));
    memset(resroots, 0, sizeof(resroots));
    memset(&m, 0, sizeof(m));

    ei = calloc(1, sizeof(elf_info_t));
    if (!ei) {
        fprintf(stderr, "%s: out of memory\n", TOOL_NAME);
        return 3;
    }

    /* Required interface: `cde-static-bundler scan --entry ...` */
    if (argc > 1 && strcmp(argv[1], "scan") == 0) {
        argv++;
        argc--;
    } else if (argc > 1 && strcmp(argv[1], "-h") != 0 && strcmp(argv[1], "--help") != 0) {
        fprintf(stderr, "%s: expected subcommand 'scan'\n", TOOL_NAME);
        usage(stderr);
        return 2;
    }

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(stdout);
            return 0;
        } else if (strcmp(argv[i], "--entry") == 0 && i + 1 < argc) {
            entry = argv[++i];
        } else if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            bundle_dir = argv[++i];
        } else if (strcmp(argv[i], "--libdir") == 0 && i + 1 < argc) {
            if (nlibdirs < MAX_LIBDIRS) { libdirs[nlibdirs++] = argv[++i]; }
            else { fprintf(stderr, "%s: too many --libdir arguments (max %d)\n", TOOL_NAME, MAX_LIBDIRS); return 2; }
        } else if (strcmp(argv[i], "--resource-root") == 0 && i + 1 < argc) {
            if (nresroots < MAX_RESROOTS) { resroots[nresroots++] = argv[++i]; }
            else { fprintf(stderr, "%s: too many --resource-root arguments (max %d)\n", TOOL_NAME, MAX_RESROOTS); return 2; }
        } else {
            fprintf(stderr, "%s: unknown argument: %s\n", TOOL_NAME, argv[i]);
            usage(stderr);
            return 2;
        }
    }
    if (!entry) {
        fprintf(stderr, "%s: --entry is required\n", TOOL_NAME);
        usage(stderr);
        return 2;
    }

    snprintf(toolver, sizeof(toolver), "%s", TOOL_VERSION);

    if (parse_elf(entry, ei, errmsg) != 0) {
        fprintf(stderr, "%s: %s\n", TOOL_NAME, errmsg);
        free(ei);
        return 1;
    }
    if (realpath(entry, entry_real) == NULL) {
        fprintf(stderr, "%s: realpath(%s): %s\n", TOOL_NAME, entry, strerror(errno));
        return 1;
    }
    snprintf(ei->entry_abspath, sizeof(ei->entry_abspath), "%s", entry_real);
    {
        char *slash = strrchr(entry_real, '/');
        if (slash) {
            snprintf(entry_dir, sizeof(entry_dir), "%.*s", (int)(slash - entry_real), entry_real);
        } else {
            snprintf(entry_dir, sizeof(entry_dir), ".");
        }
    }
    if (sha256_file(entry_real, ei->entry_sha256) != 0) {
        fprintf(stderr, "%s: sha256(%s) failed\n", TOOL_NAME, entry_real);
        return 1;
    }

    snprintf(m.entry, sizeof(m.entry), "%s", entry_real);
    snprintf(m.arch, sizeof(m.arch), "%s", ei->arch_name);
    snprintf(m.interpreter, sizeof(m.interpreter), "%s", ei->interpreter);
    m.entry_arch = ei->e_machine;

    /* Resolve deps: recursive transitive closure via a BFS work queue.
     *
     * Algorithm:
     *   - Seed the queue with the entry ELF.
     *   - While the queue is non-empty, pop an ELF, parse ITS DT_NEEDED /
     *     DT_RPATH / DT_RUNPATH using that parent ELF's own lookup context,
     *     and record every parent->needed graph edge.
     *   - System libraries: recorded in system_exclusions, never copied,
     *     never enqueued for recursion.
     *   - Non-system dependency: resolve with the parent's context; verify
     *     its ELF machine matches the entry machine (mismatch = required
     *     unresolved); skip re-copy if its canonical path is already in the
     *     visited set (cycle/duplicate protection); otherwise copy it as a
     *     regular file and enqueue it so ITS dependencies are traversed.
     *   - complete=true is emitted only after the full non-system closure
     *     has been traversed with no required unresolved items.
     */
    {
        /* Named compile-time capacity macro; see top-of-file block.  A
         * disposable test binary may override it with -D at compile time. */
        enum { MAX_QUEUE = CDE_BUNDLER_MAX_QUEUE };
        /* Large buffers live in static storage, not on the stack: OHOS
         * stack limits are small and 2 x 1024 x PATH_MAX would overflow. */
        static char queue[MAX_QUEUE][PATH_MAX];
        static char visited[MAX_QUEUE][PATH_MAX];
        static elf_info_t cur_ei;
        int qhead = 0, qtail = 0;
        int nvisited = 0;
        int vi;

        /* Seed entry: check capacity before any insert. */
        if (nvisited >= MAX_QUEUE) {
            manifest_capacity_fatal(&m, "visited set capacity exceeded at seed entry");
        } else {
            snprintf(visited[nvisited++], PATH_MAX, "%s", entry_real);
        }
        if (qtail >= MAX_QUEUE) {
            manifest_capacity_fatal(&m, "queue capacity exceeded at seed entry");
        } else {
            snprintf(queue[qtail++], PATH_MAX, "%s", entry_real);
        }

        while (qhead < qtail) {
            char cur[PATH_MAX];
            char cur_dir[PATH_MAX];
            char cur_err[512];
            int ci;
            snprintf(cur, PATH_MAX, "%s", queue[qhead++]);

            {
                char *slash = strrchr(cur, '/');
                if (slash)
                    snprintf(cur_dir, sizeof(cur_dir), "%.*s", (int)(slash - cur), cur);
                else
                    snprintf(cur_dir, sizeof(cur_dir), ".");
            }

            if (parse_elf(cur, &cur_ei, cur_err) != 0) {
                fprintf(stderr, "%s: cannot reparse %s: %s\n", TOOL_NAME, cur, cur_err);
                m.has_unresolved_required = 1;
                continue;
            }
            if (cur_ei.deps_truncated) {
                /* DT_NEEDED table overflowed its per-ELF bound: silent
                 * dependency loss is forbidden, so treat as fatal. */
                fprintf(stderr, "%s: dependency table capacity exceeded while parsing %s\n",
                        TOOL_NAME, cur);
                manifest_capacity_fatal(&m, "per-ELF dependency table capacity exceeded");
                continue;
            }
            for (ci = 0; ci < cur_ei.ndeps; ci++) {
                dep_t *d = &cur_ei.deps[ci];
                dep_graph_add(&m, cur, d->name);
                if (is_system_soname(d->name)) {
                    size_t n = strlen(m.excluded);
                    if (n + 400 < sizeof(m.excluded)) {
                        if (n > 0) { strncat(m.excluded, ",\n", sizeof(m.excluded)-n-1); n = strlen(m.excluded); }
                        char esc_name[512];
                        if (json_escape_buf(d->name, esc_name, sizeof(esc_name)) != 0) { /* fallback */ }
                        snprintf(m.excluded + n, sizeof(m.excluded) - n,
                                 "{\"soname\":\"%s\",\"reason\":\"system-library-exclusion\"}", esc_name);
                    } else {
                        manifest_capacity_fatal(&m, "exclusion-record buffer capacity exceeded");
                    }
                    continue; /* never copy, never recurse into system libs */
                }
                {
                    char resolved[PATH_MAX];
                    if (resolve_dep(d->name, cur_dir, &cur_ei, libdirs, nlibdirs, resolved) != 0) {
                        m.has_unresolved_required = 1;
                        {
                            size_t n = strlen(m.unresolved);
                            if (n + 400 < sizeof(m.unresolved)) {
                                if (n > 0) { strncat(m.unresolved, ",\n", sizeof(m.unresolved)-n-1); n = strlen(m.unresolved); }
                                char esc_soname[512], esc_parent[PATH_MAX];
                                if (json_escape_buf(d->name, esc_soname, sizeof(esc_soname)) != 0) { /* fallback */ }
                                if (json_escape_buf(cur, esc_parent, sizeof(esc_parent)) != 0) { /* fallback */ }
                                snprintf(m.unresolved + n, sizeof(m.unresolved) - n,
                                         "{\"soname\":\"%s\",\"required\":true,\"parent\":\"%s\"}", esc_soname, esc_parent);
                            } else {
                                manifest_capacity_fatal(&m, "unresolved-record buffer capacity exceeded");
                            }
                        }
                        continue;
                    }
                    /* architecture consistency vs ENTRY machine */
                    {
                        elf_info_t de;
                        char derr[512];
                        if (parse_elf(resolved, &de, derr) == 0 && de.e_machine != ei->e_machine) {
                            m.has_unresolved_required = 1;
                            {
                                size_t n = strlen(m.unresolved);
                                if (n + 500 < sizeof(m.unresolved)) {
                                    if (n > 0) { strncat(m.unresolved, ",\n", sizeof(m.unresolved)-n-1); n = strlen(m.unresolved); }
                                    char esc_soname[512], esc_parent[PATH_MAX];
                                    if (json_escape_buf(d->name, esc_soname, sizeof(esc_soname)) != 0) { /* fallback */ }
                                    if (json_escape_buf(cur, esc_parent, sizeof(esc_parent)) != 0) { /* fallback */ }
                                    snprintf(m.unresolved + n, sizeof(m.unresolved) - n,
                                             "{\"soname\":\"%s\",\"required\":true,\"reason\":\"architecture-mismatch(%s vs %s)\",\"parent\":\"%s\"}",
                                             esc_soname, de.arch_name, ei->arch_name, esc_parent);
                                } else {
                                    manifest_capacity_fatal(&m, "unresolved-record buffer capacity exceeded (arch mismatch)");
                                }
                            }
                            continue;
                        }
                    }
                    /* canonical visited check: avoid cycle and duplicate copy */
                    {
                        int dup = 0;
                        for (vi = 0; vi < nvisited; vi++) {
                            if (strcmp(visited[vi], resolved) == 0) { dup = 1; break; }
                        }
                        if (dup) continue; /* edge already recorded above */
                    }
                    if (nvisited >= MAX_QUEUE) {
                        manifest_capacity_fatal(&m, "visited set capacity exceeded during traversal");
                        continue;
                    }
                    snprintf(visited[nvisited++], PATH_MAX, "%s", resolved);
                    {
                        char rel[PATH_MAX], out_abs[PATH_MAX], sha[65];
                        int copied = 0;
                        if (is_unsafe_component(d->name)) {
                            fprintf(stderr, "%s: unsafe dependency name rejected: %s\n", TOOL_NAME, d->name);
                            m.has_unresolved_required = 1;
                            continue;
                        }
                        snprintf(rel, sizeof(rel), "lib/%s", d->name);
                        if (copy_file_into_bundle(resolved, bundle_dir, rel, out_abs, sha, &copied) != 0) {
                            fprintf(stderr, "%s: failed to copy dependency %s\n", TOOL_NAME, d->name);
                            return 1;
                        }
                        {
                            size_t n = strlen(m.copied);
                            if (n + 700 < sizeof(m.copied)) {
                                char esc_origin[1024], esc_dest[1024];
                                if (json_escape_buf(resolved, esc_origin, sizeof(esc_origin)) != 0 ||
                                    json_escape_buf(rel, esc_dest, sizeof(esc_dest)) != 0) {
                                    manifest_capacity_fatal(&m, "path too long for JSON serialization (dependency)");
                                } else {
                                    if (n > 0) { strncat(m.copied, ",\n", sizeof(m.copied)-n-1); n = strlen(m.copied); }
                                    snprintf(m.copied + n, sizeof(m.copied) - n,
                                             "{\"origin\":\"%s\",\"dest\":\"%s\",\"sha256\":\"%s\"}",
                                             esc_origin, esc_dest, sha);
                                }
                            } else {
                                manifest_capacity_fatal(&m, "copied-file-record buffer capacity exceeded");
                            }
                        }
                        if (qtail < MAX_QUEUE) {
                            snprintf(queue[qtail++], PATH_MAX, "%s", resolved);
                        } else {
                            manifest_capacity_fatal(&m, "traversal queue capacity exceeded");
                        }
                    }
                }
            }
        }
    }

    /* Copy the entry itself */
    {
        char out_abs[PATH_MAX], sha[65];
        int copied = 0;
        if (copy_file_into_bundle(entry_real, bundle_dir, "entry", out_abs, sha, &copied) != 0) {
            fprintf(stderr, "%s: failed to copy entry %s\n", TOOL_NAME, entry_real);
            return 1;
        }
        {
            size_t n = strlen(m.copied);
            if (n + 700 < sizeof(m.copied)) {
                char esc_origin[1024];
                if (json_escape_buf(entry_real, esc_origin, sizeof(esc_origin)) != 0) {
                    manifest_capacity_fatal(&m, "entry path too long for JSON serialization");
                } else {
                    if (n > 0) { strncat(m.copied, ",\n", sizeof(m.copied)-n-1); n = strlen(m.copied); }
                    snprintf(m.copied + n, sizeof(m.copied) - n,
                             "{\"origin\":\"%s\",\"dest\":\"entry\",\"sha256\":\"%s\"}",
                             esc_origin, sha);
                }
            }
        }
    }

    /* Copy resource roots */
    for (i = 0; i < nresroots; i++) {
        char root_real[PATH_MAX];
        int fail = 0;
        if (realpath(resroots[i], root_real) == NULL) {
            fprintf(stderr, "%s: resource-root %s: %s\n", TOOL_NAME, resroots[i], strerror(errno));
            return 1;
        }
        {
            size_t n = strlen(m.resroots);
            if (n + 600 < sizeof(m.resroots)) {
                char esc_root[1024];
                if (json_escape_buf(root_real, esc_root, sizeof(esc_root)) != 0) {
                    manifest_capacity_fatal(&m, "resource-root path too long for JSON");
                } else {
                    if (n > 0) { strncat(m.resroots, ",\n", sizeof(m.resroots)-n-1); n = strlen(m.resroots); }
                    snprintf(m.resroots + n, sizeof(m.resroots) - n,
                             "{\"root\":\"%s\"}", esc_root);
                }
            } else {
                manifest_capacity_fatal(&m, "resource-roots record buffer capacity exceeded");
            }
        }
        copy_resource_root(root_real, bundle_dir, &m, &fail);
        if (fail) {
            fprintf(stderr, "%s: resource-root %s: unsafe entries rejected or copy failed\n",
                    TOOL_NAME, root_real);
            return 1;
        }
    }

    if (write_manifest(bundle_dir, &m, toolver) != 0) {
        fprintf(stderr, "%s: cannot write manifest.json in %s\n", TOOL_NAME, bundle_dir);
        return 1;
    }

    if (m.capacity_fatal) {
        fprintf(stderr, "%s: capacity FATAL: %s (see manifest.json 'dependency-closure-capacity-exceeded' "
                "record); bundle INCOMPLETE, no successful bundle declared\n",
                TOOL_NAME, m.capacity_reason);
        return 1;
    }
    if (m.has_unresolved_required) {
        fprintf(stderr, "%s: bundle INCOMPLETE: required non-system dependencies unresolved "
                "(see manifest.json); not declaring a successful bundle\n", TOOL_NAME);
        return 1;
    }
    printf("%s: bundle written to %s/manifest.json (complete=true)\n", TOOL_NAME, bundle_dir);
    return 0;
}
