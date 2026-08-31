/* asmc_elf.c -- x86-64 ELF relocatable object writer
 * Target: aarch64-unknown-linux-ohos (ARM64 host)
 * Emits ELF64 relocatable object files for x86-64 target code.
 * Port direction: elf.asm semantics — sections, symbol table,
 * string tables, relocations and headers constructed from parsed
 * program state (asm_output_t), not copied or fixed.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "asmc_data.h"

/* from asmc_runtime.s / asmc_io.c */
extern int tprintf(const char *fmt, ...);
extern int asmerr(int value, const char *msg);

/* --- ELF64 definitions (x86-64 target) --- */

#define EI_NIDENT 16

typedef struct {
    uint8_t  e_ident[EI_NIDENT];
    uint16_t e_type;
    uint16_t e_machine;
    uint32_t e_version;
    uint64_t e_entry;
    uint64_t e_phoff;
    uint64_t e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize;
    uint16_t e_phentsize;
    uint16_t e_phnum;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
} elf64_ehdr_t;

typedef struct {
    uint32_t sh_name;
    uint32_t sh_type;
    uint64_t sh_flags;
    uint64_t sh_addr;
    uint64_t sh_offset;
    uint64_t sh_size;
    uint32_t sh_link;
    uint32_t sh_info;
    uint64_t sh_addralign;
    uint64_t sh_entsize;
} elf64_shdr_t;

typedef struct {
    uint32_t st_name;
    uint8_t  st_info;
    uint8_t  st_other;
    uint16_t st_shndx;
    uint64_t st_value;
    uint64_t st_size;
} elf64_sym_t;

typedef struct {
    uint64_t r_offset;
    uint64_t r_info;
    int64_t  r_addend;
} elf64_rela_t;

/* constants */
#define ET_REL      1
#define EM_X86_64   62
#define EV_CURRENT  1
#define ELFCLASS64  2
#define ELFDATA2LSB 1
#define ELFOSABI_SYSV 0

#define SHT_PROGBITS 1
#define SHT_SYMTAB   2
#define SHT_STRTAB   3
#define SHT_RELA     4
#define SHT_NOBITS   8
#define SHT_NULL     0

#define SHF_WRITE    0x1
#define SHF_ALLOC    0x2
#define SHF_EXECINSTR 0x4

#define STB_LOCAL  0
#define STB_GLOBAL 1
#define STT_NOTYPE 0
#define STT_FUNC   2

#define SHN_UNDEF   0
#define SHN_ABS     0xfff1

#define R_X86_64_PC32  2
#define R_X86_64_PLT32 4

/* indices of sections in the ELF file we produce */
/* (SEC_TEXT/SEC_DATA/SEC_BSS macros come from asmc_data.h) */
enum {
    ELFSEC_NULL = 0,
    ELFSEC_TEXT = 1,
    ELFSEC_DATA = 2,
    ELFSEC_BSS = 3,
    ELFSEC_SYMTAB = 4,
    ELFSEC_STRTAB = 5,
    ELFSEC_RELA_TEXT = 6,
    ELFSEC_RELA_DATA = 7,
    ELFSEC_SHSTRTAB = 8,
    ELFSEC_COUNT = 9
};

/* One big in-memory output buffer */
typedef struct {
    uint8_t buf[131072];
    size_t  len;
} eobuf_t;

static void eput8(eobuf_t *b, uint8_t v)
{ if (b->len < sizeof(b->buf)) b->buf[b->len++] = v; }
static void eput16(eobuf_t *b, uint16_t v)
{ eput8(b, (uint8_t)v); eput8(b, (uint8_t)(v >> 8)); }
static void eput32(eobuf_t *b, uint32_t v)
{ eput8(b,(uint8_t)v); eput8(b,(uint8_t)(v>>8)); eput8(b,(uint8_t)(v>>16)); eput8(b,(uint8_t)(v>>24)); }
static void eput64(eobuf_t *b, uint64_t v)
{
    for (int i = 0; i < 8; i++) eput8(b, (uint8_t)(v >> (8*i)));
}
static void eputs(eobuf_t *b, const char *s)
{ while (*s) eput8(b, (uint8_t)*s++); }

/* section content builders */
typedef struct {
    eobuf_t body;       /* .text payload */
    eobuf_t datab;      /* .data payload */
    eobuf_t shstr;      /* section-name string table */
    eobuf_t strtab;     /* symbol string table */
    eobuf_t symtab;     /* symbol table entries */
    eobuf_t rela;       /* relocation entries (.rela.text) */
    eobuf_t relad;      /* relocation entries (.rela.data) */
    uint32_t shstr_offsets[ELFSEC_COUNT];
    uint32_t str_offsets[256];
} elf_build_t;

static uint32_t add_shstr(elf_build_t *e, const char *name)
{
    uint32_t off = (uint32_t)e->shstr.len;
    eputs(&e->shstr, name);
    eput8(&e->shstr, 0);
    return off;
}

static uint32_t add_str(elf_build_t *e, const char *name)
{
    uint32_t off = (uint32_t)e->strtab.len;
    eputs(&e->strtab, name);
    eput8(&e->strtab, 0);
    return off;
}

/* Build and write the ELF relocatable object. */
int WriteElfOutput(asm_output_t *out, const char *src_path)
{
    char dst[1024];
    snprintf(dst, sizeof(dst), "%s", src_path);
    char *dot = strrchr(dst, '.');
    if (dot) strcpy(dot + 1, "o");
    else strcat(dst, ".o");

    elf_build_t e;
    memset(&e, 0, sizeof(e));

    /* --- section name string table (index 0 = empty) --- */
    uint32_t s_text  = add_shstr(&e, ".text");
    uint32_t s_data  = add_shstr(&e, ".data");
    uint32_t s_bss   = add_shstr(&e, ".bss");
    uint32_t s_sym   = add_shstr(&e, ".symtab");
    uint32_t s_str   = add_shstr(&e, ".strtab");
    uint32_t s_rela  = add_shstr(&e, ".rela.text");
    uint32_t s_relad = add_shstr(&e, ".rela.data");
    uint32_t s_shstr = add_shstr(&e, ".shstrtab");
    e.shstr_offsets[SEC_TEXT] = s_text;
    e.shstr_offsets[SEC_DATA] = s_data;
    e.shstr_offsets[SEC_BSS]  = s_bss;
    e.shstr_offsets[ELFSEC_SYMTAB] = s_sym;
    e.shstr_offsets[ELFSEC_STRTAB] = s_str;
    e.shstr_offsets[ELFSEC_RELA_TEXT] = s_rela;
    e.shstr_offsets[ELFSEC_RELA_DATA] = s_relad;
    e.shstr_offsets[ELFSEC_SHSTRTAB] = s_shstr;

    /* --- .text payload: placed code bytes --- */
    for (size_t i = 0; i < out->text_len; i++)
        eput8(&e.body, out->text[i]);
    /* --- .data payload: initialized data bytes (in e.data) --- */
    for (size_t i = 0; i < out->data_len; i++)
        eput8(&e.datab, out->data[i]);

    /* --- symbol table: index 0 = NULL symbol --- */
    eput32(&e.symtab, 0); eput8(&e.symtab, 0); eput8(&e.symtab, 0);
    eput16(&e.symtab, 0); eput64(&e.symtab, 0); eput64(&e.symtab, 0);

    /* strtab: index 0 must be the empty string (NULL symbol name) */
    eput8(&e.strtab, 0);
    e.str_offsets[0] = 0;

    /* ELF .symtab layout requires all STB_LOCAL symbols to precede STB_GLOBAL
     * ones, and sh_info = index of the first non-local symbol.  Write locals
     * first then globals, record new-index mapping for relocations. */
    int new_idx[1024];
    for (int i = 0; i < out->nsyms; i++) new_idx[i] = -1;
    int nloc = 0, nglob = 0;
    for (int i = 0; i < out->nsyms; i++)
        if (!out->syms[i].global) nloc++;
    nglob = out->nsyms - nloc;
    int cur = 1;   /* index 0 reserved for NULL */
    for (int pass = 0; pass < 2; pass++) {
        for (int i = 0; i < out->nsyms; i++) {
            int is_glob = out->syms[i].global != 0;
            if (is_glob != (pass == 1)) continue;
            asmc_sym_t *s = &out->syms[i];
            uint32_t st = add_str(&e, s->name);
            e.str_offsets[i + 1] = st;
            uint8_t bind    = s->global ? STB_GLOBAL : STB_LOCAL;
            uint8_t type    = s->defined ? STT_NOTYPE : STT_NOTYPE;
            new_idx[i] = cur++;
            eput32(&e.symtab, st);
            eput8(&e.symtab, (uint8_t)((bind << 4) | type));
            eput8(&e.symtab, 0);
            eput16(&e.symtab, (uint16_t)(s->defined ? s->sec_index : SHN_UNDEF));
            eput64(&e.symtab, s->value);
            eput64(&e.symtab, 0);   /* st_size */
        }
    }

    /* --- relocations: separate .rela.text and .rela.data by fixup->sec --- */
    for (int i = 0; i < out->nfixups; i++) {
        asmc_fixup_t *f = &out->fixups[i];
        /* r_info = (symtab_index) << 32 | type ; symtab index 0 is NULL, and the
         * fixed symbols are laid out locals-first per the mapping above. */
        int sti = (f->sym_index >= 0 && f->sym_index < out->nsyms) ? new_idx[f->sym_index] : 0;
        uint64_t r_info = ((uint64_t)sti << 32) | (uint32_t)f->type;
        if (f->sec == SEC_DATA) {
            eput64(&e.relad, f->offset);
            eput64(&e.relad, r_info);
            eput64(&e.relad, f->addend);
        } else {
            eput64(&e.rela, f->offset + 1);   /* r_offset points at the imm field */
            eput64(&e.rela, r_info);
            eput64(&e.rela, f->addend);
        }
    }

    /* --- layout: compute file offsets --- */
    size_t off = 64;               /* ELF header */
    size_t shoff;
    size_t text_off, data_off, sym_off, str_off, rela_off, relad_off, shstr_off;

    text_off = off;      off += e.body.len;
    data_off = off;      off += e.datab.len;
    sym_off  = off;      off += e.symtab.len;
    str_off  = off;      off += e.strtab.len;
    rela_off = off;      off += e.rela.len;
    relad_off = off;     off += e.relad.len;
    shstr_off = off;     off += e.shstr.len;
    off = (off + 7) & ~7ULL;       /* align section headers */
    shoff = off;
    off += (size_t)ELFSEC_COUNT * 64; /* section headers */

    eobuf_t f;
    memset(&f, 0, sizeof(f));

    /* --- ELF header --- */
    eput8(&f, 0x7f); eput8(&f, 'E'); eput8(&f, 'L'); eput8(&f, 'F');
    eput8(&f, ELFCLASS64);
    eput8(&f, ELFDATA2LSB);
    eput8(&f, EV_CURRENT);
    eput8(&f, ELFOSABI_SYSV);
    for (int i = 0; i < 8; i++) eput8(&f, 0);  /* pad */
    eput16(&f, ET_REL);
    eput16(&f, EM_X86_64);
    eput32(&f, EV_CURRENT);
    eput64(&f, 0);                 /* e_entry */
    eput64(&f, 0);                 /* e_phoff */
    eput64(&f, shoff);
    eput32(&f, 0);                 /* e_flags */
    eput16(&f, 64);                /* e_ehsize */
    eput16(&f, 0);                 /* e_phentsize */
    eput16(&f, 0);                 /* e_phnum */
    eput16(&f, 64);                /* e_shentsize */
    eput16(&f, ELFSEC_COUNT);         /* e_shnum */
    eput16(&f, ELFSEC_SHSTRTAB);      /* e_shstrndx */

    /* pad to 64 */
    while (f.len < 64) eput8(&f, 0);

    /* --- section payloads at their computed offsets --- */
    while (f.len < text_off) eput8(&f, 0);
    for (size_t i = 0; i < e.body.len; i++) eput8(&f, e.body.buf[i]);
    while (f.len < data_off) eput8(&f, 0);
    for (size_t i = 0; i < e.datab.len; i++) eput8(&f, e.datab.buf[i]);
    while (f.len < sym_off) eput8(&f, 0);
    for (size_t i = 0; i < e.symtab.len; i++) eput8(&f, e.symtab.buf[i]);
    while (f.len < str_off) eput8(&f, 0);
    for (size_t i = 0; i < e.strtab.len; i++) eput8(&f, e.strtab.buf[i]);
    while (f.len < rela_off) eput8(&f, 0);
    for (size_t i = 0; i < e.rela.len; i++) eput8(&f, e.rela.buf[i]);
    while (f.len < relad_off) eput8(&f, 0);
    for (size_t i = 0; i < e.relad.len; i++) eput8(&f, e.relad.buf[i]);
    while (f.len < shstr_off) eput8(&f, 0);
    for (size_t i = 0; i < e.shstr.len; i++) eput8(&f, e.shstr.buf[i]);
    while (f.len < shoff) eput8(&f, 0);

    /* --- section headers --- */
    elf64_shdr_t sh[ELFSEC_COUNT];
    memset(sh, 0, sizeof(sh));

    /* .text */
    sh[SEC_TEXT].sh_name = e.shstr_offsets[SEC_TEXT];
    sh[SEC_TEXT].sh_type = SHT_PROGBITS;
    sh[SEC_TEXT].sh_flags = SHF_ALLOC | SHF_EXECINSTR;
    sh[SEC_TEXT].sh_addr = 0;
    sh[SEC_TEXT].sh_offset = text_off;
    sh[SEC_TEXT].sh_size = e.body.len;
    sh[SEC_TEXT].sh_addralign = 16;
    sh[SEC_TEXT].sh_entsize = 0;

    /* .data */
    sh[SEC_DATA].sh_name = e.shstr_offsets[SEC_DATA];
    sh[SEC_DATA].sh_type = SHT_PROGBITS;
    sh[SEC_DATA].sh_flags = SHF_ALLOC | SHF_WRITE;
    sh[SEC_DATA].sh_offset = data_off;
    sh[SEC_DATA].sh_size = e.datab.len;
    sh[SEC_DATA].sh_addralign = 1;

    /* .bss: NOBITS, no file bytes */
    sh[SEC_BSS].sh_name = e.shstr_offsets[SEC_BSS];
    sh[SEC_BSS].sh_type = SHT_NOBITS;
    sh[SEC_BSS].sh_flags = SHF_ALLOC | SHF_WRITE;
    sh[SEC_BSS].sh_offset = shstr_off;   /* virtual; readelf shows end-of-file */
    sh[SEC_BSS].sh_size = out->bss_len;
    sh[SEC_BSS].sh_addralign = 1;

    /* .symtab */
    sh[ELFSEC_SYMTAB].sh_name = e.shstr_offsets[ELFSEC_SYMTAB];
    sh[ELFSEC_SYMTAB].sh_type = SHT_SYMTAB;
    sh[ELFSEC_SYMTAB].sh_offset = sym_off;
    sh[ELFSEC_SYMTAB].sh_size = e.symtab.len;
    sh[ELFSEC_SYMTAB].sh_link = ELFSEC_STRTAB;
    sh[ELFSEC_SYMTAB].sh_info = (uint32_t)(1 + nloc);  /* index of first non-local symbol */
    sh[ELFSEC_SYMTAB].sh_addralign = 8;
    sh[ELFSEC_SYMTAB].sh_entsize = 24;

    /* .strtab */
    sh[ELFSEC_STRTAB].sh_name = e.shstr_offsets[ELFSEC_STRTAB];
    sh[ELFSEC_STRTAB].sh_type = SHT_STRTAB;
    sh[ELFSEC_STRTAB].sh_offset = str_off;
    sh[ELFSEC_STRTAB].sh_size = e.strtab.len;
    sh[ELFSEC_STRTAB].sh_addralign = 1;

    /* .rela.text */
    sh[ELFSEC_RELA_TEXT].sh_name = e.shstr_offsets[ELFSEC_RELA_TEXT];
    sh[ELFSEC_RELA_TEXT].sh_type = SHT_RELA;
    sh[ELFSEC_RELA_TEXT].sh_offset = rela_off;
    sh[ELFSEC_RELA_TEXT].sh_size = e.rela.len;
    sh[ELFSEC_RELA_TEXT].sh_link = ELFSEC_SYMTAB;
    sh[ELFSEC_RELA_TEXT].sh_info = SEC_TEXT;
    sh[ELFSEC_RELA_TEXT].sh_addralign = 8;
    sh[ELFSEC_RELA_TEXT].sh_entsize = 24;

    /* .rela.data */
    sh[ELFSEC_RELA_DATA].sh_name = e.shstr_offsets[ELFSEC_RELA_DATA];
    sh[ELFSEC_RELA_DATA].sh_type = SHT_RELA;
    sh[ELFSEC_RELA_DATA].sh_offset = relad_off;
    sh[ELFSEC_RELA_DATA].sh_size = e.relad.len;
    sh[ELFSEC_RELA_DATA].sh_link = ELFSEC_SYMTAB;
    sh[ELFSEC_RELA_DATA].sh_info = SEC_DATA;
    sh[ELFSEC_RELA_DATA].sh_addralign = 8;
    sh[ELFSEC_RELA_DATA].sh_entsize = 24;

    /* .shstrtab */
    sh[ELFSEC_SHSTRTAB].sh_name = e.shstr_offsets[ELFSEC_SHSTRTAB];
    sh[ELFSEC_SHSTRTAB].sh_type = SHT_STRTAB;
    sh[ELFSEC_SHSTRTAB].sh_offset = shstr_off;
    sh[ELFSEC_SHSTRTAB].sh_size = e.shstr.len;
    sh[ELFSEC_SHSTRTAB].sh_addralign = 1;

    for (int i = 0; i < ELFSEC_COUNT; i++) {
        eput32(&f, sh[i].sh_name);
        eput32(&f, sh[i].sh_type);
        eput64(&f, sh[i].sh_flags);
        eput64(&f, sh[i].sh_addr);
        eput64(&f, sh[i].sh_offset);
        eput64(&f, sh[i].sh_size);
        eput32(&f, sh[i].sh_link);
        eput32(&f, sh[i].sh_info);
        eput64(&f, sh[i].sh_addralign);
        eput64(&f, sh[i].sh_entsize);
    }

    FILE *fp = fopen(dst, "wb");
    if (!fp) { asmerr(1000, dst); return 1; }
    fwrite(f.buf, 1, f.len, fp);
    fclose(fp);

    tprintf("%s: ELF64 relocatable, %zu bytes (%d symbols, %d relocs)\n",
            dst, f.len, out->nsyms, out->nfixups);
    return 0;
}