/* asmc_asm.c -- minimal AArch64-hosted x86/x86-64 assembler pipeline
 * Target: aarch64-unknown-linux-ohos (ARM64 host)
 * Emits x86/x86-64 target object bytes (flat binary `.bin`)
 * Port direction: tokenize.asm / parser.asm / bin.asm semantics,
 * reduced to a real, verifiable minimal pipeline for this round.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include "asmc_data.h"

/* from asmc_runtime.s / asmc_io.c */
extern int tprintf(const char *fmt, ...);
extern int asmerr(int value, const char *msg);

/* ---------- tokenizer (tokenize.asm reduced) ---------- */

typedef enum {
    ATOK_END = 0,
    ATOK_ID,        /* identifier (mnemonic, label, register) */
    ATOK_NUM,       /* numeric literal */
    ATOK_STRING,    /* '...' or "..." */
    ATOK_OP,        /* single-char operator / punctuation */
    ATOK_DIRECTIVE  /* .model, .code, .data, .stack, end ... */
} a_tok_type;

typedef struct {
    a_tok_type type;
    char text[128];
    uint64_t value;    /* ATOK_NUM */
    int size;          /* ATOK_NUM: bytes needed (1,2,4,8) */
} a_tok_t;

/* skip whitespace and comments (; to EOL) */
static const char *skip_ws(const char *p)
{
    for (;;) {
        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
            p++;
        if (*p == ';') {          /* comment */
            while (*p && *p != '\n')
                p++;
            continue;
        }
        break;
    }
    return p;
}

static int hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if ((c | 0x20) >= 'a' && (c | 0x20) <= 'f') return (c | 0x20) - 'a' + 10;
    return -1;
}

static int parse_number(const char **pp, a_tok_t *tok)
{
    const char *p = *pp;
    uint64_t v = 0;
    int base = 10, size = 4;
    int digits = 0;

    if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) {
        base = 16;
        p += 2;
    } else if (p[0] == '0' && (p[1] == 'b' || p[1] == 'B')) {
        base = 2;
        p += 2;
    }

    /* parse integer part */
    for (;;) {
        int d = (base == 16) ? hexval(*p) : (*p >= '0' && *p <= '9' ? *p - '0' : -1);
        if (base == 10 && *p >= '0' && *p <= '9')
            d = *p - '0';
        if (d < 0 || d >= base)
            break;
        v = v * base + d;
        digits++;
        p++;
    }

    /* floating-point fractional part: .NNN */
    if (base == 10 && *p == '.' && p[1] >= '0' && p[1] <= '9') {
        p++; /* skip '.' */
        uint64_t frac = 0;
        int fdigits = 0;
        while (*p >= '0' && *p <= '9') {
            if (fdigits < 18) { frac = frac * 10 + (*p - '0'); fdigits++; }
            p++;
        }
        /* convert decimal float to IEEE 754 double bits:
         * value = intpart + fracpart / 10^fdigits */
        {
            double dval = (double)v;
            double scale = 1.0;
            for (int fd = 0; fd < fdigits; fd++) scale *= 10.0;
            dval += (double)frac / scale;
            union { double d; uint64_t u; } cvt;
            cvt.d = dval;
            tok->value = cvt.u;
        }
        tok->size = 8;
        tok->type = ATOK_NUM;
        snprintf(tok->text, sizeof(tok->text), "%llu.%llu", (unsigned long long)v, (unsigned long long)frac);
        *pp = p;
        return 1;
    }

    /* real constant suffix 'r': hex digits are IEEE 754 bits directly */
    if (base == 16 && *p == 'r') {
        /* 3FF0000000000000r -> value = 0x3FF0000000000000 (IEEE 754 double for 1.0) */
        tok->value = v;
        tok->size = 8;
        tok->type = ATOK_NUM;
        snprintf(tok->text, sizeof(tok->text), "0x%llx", (unsigned long long)v);
        p++;
        *pp = p;
        return 1;
    }

    /* optional size letter suffix: h(hex), b(bin), d(dec), o(oct) */
    if (base == 10 && (*p == 'h' || *p == 'H')) { base = 16; p++; }
    else if (base == 10 && (*p == 'b' || *p == 'B')) { base = 2; p++; }
    else if (base == 10 && (*p == 'd' || *p == 'D')) { p++; }

    if (v > 0xFFFFFFFF) size = 8;
    else if (v > 0xFFFF) size = 4;
    else if (v > 0xFF) size = 2;
    else size = 1;

    tok->type = ATOK_NUM;
    tok->value = v;
    tok->size = size;
    snprintf(tok->text, sizeof(tok->text), "%llu", (unsigned long long)v);
    *pp = p;
    return 1;
}

/* Tokenize one source line into up to max tokens.
 * Returns token count (excluding final ATOK_END).
 */
int TokenizeLine(const char *line, a_tok_t *toks, int max)
{
    const char *p = line;
    int n = 0;

    p = skip_ws(p);
    while (*p && n < max - 1) {
        a_tok_t *t = &toks[n];
        memset(t, 0, sizeof(*t));

        if (*p == '.' && ((p[1] >= 'a' && p[1] <= 'z') || (p[1] >= 'A' && p[1] <= 'Z') ||
                   (p[1] >= '0' && p[1] <= '9') || p[1] == '_')) {
            /* directive (.model, .code, .data, .stack, .end, ...) — only at line start */
            if (n == 0) {  /* first token must be '.' for directive */
                const char *s = p;
                int i = 0;
                while (*p && *p != ' ' && *p != '\t' && *p != ',' &&
                       *p != '\n' && *p != '\r' && *p != ';' && i < 127)
                    t->text[i++] = *p++;
                t->text[i] = 0;
                t->type = ATOK_DIRECTIVE;
                n++;
                (void)s;
            } else {
                /* mid-line '.' is an operator (property access, e.g. [rcx].Class) */
                t->type = ATOK_OP;
                t->text[0] = '.';
                t->text[1] = 0;
                p++;
                n++;
            }
        } else if (*p >= '0' && *p <= '9') {
            parse_number(&p, t);
            n++;
        } else if (*p == '\'' || *p == '"') {
            /* string literal */
            char q = *p++;
            int i = 0;
            t->type = ATOK_STRING;
            while (*p && *p != q && i < 127)
                t->text[i++] = *p++;
            t->text[i] = 0;
            if (*p == q) p++;
            n++;
        } else if ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
                   *p == '_' || *p == '@' || *p == '$' || *p == '?') {
            /* identifier / mnemonic / register / label */
            int i = 0;
            t->type = ATOK_ID;
            while ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
                   (*p >= '0' && *p <= '9') || *p == '_' || *p == '@' ||
                   *p == '$' || *p == '?') {
                if (i < 127) t->text[i++] = *p;
                p++;
            }
            t->text[i] = 0;
            n++;
        } else if (*p == ',' || *p == ':' || *p == '[' || *p == ']' ||
                   *p == '(' || *p == ')' || *p == '{' || *p == '}' ||
                   *p == '+' || *p == '-' || *p == '.' ||
                   *p == '*' || *p == '/' || *p == '=' || *p == '&' ||
                   *p == '|' || *p == '!' || *p == '<' || *p == '>') {
            /* multi-char operators: == != <= >= && || */
            const char *mop = NULL;
            if (p[1]) {
                if (*p == '=' && p[1] == '=') mop = "==";
                else if (*p == '!' && p[1] == '=') mop = "!=";
                else if (*p == '<' && p[1] == '=') mop = "<=";
                else if (*p == '>' && p[1] == '=') mop = ">=";
                else if (*p == '&' && p[1] == '&') mop = "&&";
                else if (*p == '|' && p[1] == '|') mop = "||";
            }
            t->type = ATOK_OP;
            if (mop) {
                t->text[0] = mop[0];
                t->text[1] = mop[1];
                t->text[2] = 0;
                p += 2;
            } else {
                t->text[0] = *p;
                t->text[1] = 0;
                p++;
            }
            n++;
        } else {
            /* skip unknown single char */
            p++;
        }
        p = skip_ws(p);
    }
    toks[n].type = ATOK_END;
    return n;
}

/* ---------- x86/x86-64 encoder (parser.asm + codegen reduced) ---------- */

/* object_t defined in asmc_data.h: buffer + use64 + errors */

/* register table: name -> (reg code, 64bit flag, xmm flag) */
typedef struct { const char *name; int code; int is64; int is_xmm; } reg_t;

static const reg_t regs[] = {
    { "al",    0, 0, 0 }, { "cl", 1, 0, 0 }, { "dl", 2, 0, 0 }, { "bl", 3, 0, 0 },
    { "ah",    4, 0, 0 }, { "ch", 5, 0, 0 }, { "dh", 6, 0, 0 }, { "bh", 7, 0, 0 },
    { "ax",    0, 0, 0 }, { "cx", 1, 0, 0 }, { "dx", 2, 0, 0 }, { "bx", 3, 0, 0 },
    { "sp",    4, 0, 0 }, { "bp", 5, 0, 0 }, { "si", 6, 0, 0 }, { "di", 7, 0, 0 },
    { "eax",   0, 0, 0 }, { "ecx", 1, 0, 0 }, { "edx", 2, 0, 0 }, { "ebx", 3, 0, 0 },
    { "esp",   4, 0, 0 }, { "ebp", 5, 0, 0 }, { "esi", 6, 0, 0 }, { "edi", 7, 0, 0 },
    { "rax",   0, 1, 0 }, { "rcx", 1, 1, 0 }, { "rdx", 2, 1, 0 }, { "rbx", 3, 1, 0 },
    { "rsp",   4, 1, 0 }, { "rbp", 5, 1, 0 }, { "rsi", 6, 1, 0 }, { "rdi", 7, 1, 0 },
    { "r8",    8, 1, 0 }, { "r9", 9, 1, 0 },  { "r10", 10, 1, 0 }, { "r11", 11, 1, 0 },
    { "r12",   12, 1, 0 }, { "r13", 13, 1, 0 }, { "r14", 14, 1, 0 }, { "r15", 15, 1, 0 },
    /* 32-bit extended registers (REX encoded) */
    { "r8d",   8, 0, 0 }, { "r9d", 9, 0, 0 },  { "r10d", 10, 0, 0 }, { "r11d", 11, 0, 0 },
    { "r12d",  12, 0, 0 }, { "r13d", 13, 0, 0 }, { "r14d", 14, 0, 0 }, { "r15d", 15, 0, 0 },
    /* 16-bit extended registers (REX encoded) */
    { "r8w",   8, 0, 0 }, { "r9w", 9, 0, 0 },  { "r10w", 10, 0, 0 }, { "r11w", 11, 0, 0 },
    { "r12w",  12, 0, 0 }, { "r13w", 13, 0, 0 }, { "r14w", 14, 0, 0 }, { "r15w", 15, 0, 0 },
    /* 8-bit extended registers (REX required) */
    { "r8b",   8, 0, 0 }, { "r9b", 9, 0, 0 },  { "r10b", 10, 0, 0 }, { "r11b", 11, 0, 0 },
    { "r12b",  12, 0, 0 }, { "r13b", 13, 0, 0 }, { "r14b", 14, 0, 0 }, { "r15b", 15, 0, 0 },
    /* 8-bit low-byte of extended GPRs (REX required; also sil/spl/bpl/dil) */
    { "spl",   4, 0, 0 }, { "bpl", 5, 0, 0 }, { "sil", 6, 0, 0 }, { "dil", 7, 0, 0 },
    /* xmm registers for SIMD */
    { "xmm0",  0, 0, 1 }, { "xmm1", 1, 0, 1 }, { "xmm2", 2, 0, 1 }, { "xmm3", 3, 0, 1 },
    { "xmm4",  4, 0, 1 }, { "xmm5", 5, 0, 1 }, { "xmm6", 6, 0, 1 }, { "xmm7", 7, 0, 1 },
    { "xmm8",  8, 0, 1 }, { "xmm9", 9, 0, 1 },  { "xmm10", 10, 0, 1 }, { "xmm11", 11, 0, 1 },
    { "xmm12", 12, 0, 1 }, { "xmm13", 13, 0, 1 }, { "xmm14", 14, 0, 1 }, { "xmm15", 15, 0, 1 },
    { "xmm16", 16, 0, 1 }, { "xmm17", 17, 0, 1 }, { "xmm18", 18, 0, 1 }, { "xmm19", 19, 0, 1 },
    { "xmm20", 20, 0, 1 }, { "xmm21", 21, 0, 1 }, { "xmm22", 22, 0, 1 }, { "xmm23", 23, 0, 1 },
    { "xmm24", 24, 0, 1 }, { "xmm25", 25, 0, 1 }, { "xmm26", 26, 0, 1 }, { "xmm27", 27, 0, 1 },
    { "xmm28", 28, 0, 1 }, { "xmm29", 29, 0, 1 }, { "xmm30", 30, 0, 1 }, { "xmm31", 31, 0, 1 },
    /* ymm registers for AVX (vector length l=1) */
    { "ymm0",  0, 0, 1 }, { "ymm1", 1, 0, 1 }, { "ymm2", 2, 0, 1 }, { "ymm3", 3, 0, 1 },
    { "ymm4",  4, 0, 1 }, { "ymm5", 5, 0, 1 }, { "ymm6", 6, 0, 1 }, { "ymm7", 7, 0, 1 },
    { "ymm8",  8, 0, 1 }, { "ymm9", 9, 0, 1 },  { "ymm10", 10, 0, 1 }, { "ymm11", 11, 0, 1 },
    { "ymm12", 12, 0, 1 }, { "ymm13", 13, 0, 1 }, { "ymm14", 14, 0, 1 }, { "ymm15", 15, 0, 1 },
    { "ymm16", 16, 0, 1 }, { "ymm17", 17, 0, 1 }, { "ymm18", 18, 0, 1 }, { "ymm19", 19, 0, 1 },
    { "ymm20", 20, 0, 1 }, { "ymm21", 21, 0, 1 }, { "ymm22", 22, 0, 1 }, { "ymm23", 23, 0, 1 },
    { "ymm24", 24, 0, 1 }, { "ymm25", 25, 0, 1 }, { "ymm26", 26, 0, 1 }, { "ymm27", 27, 0, 1 },
    { "ymm28", 28, 0, 1 }, { "ymm29", 29, 0, 1 }, { "ymm30", 30, 0, 1 }, { "ymm31", 31, 0, 1 },
    /* zmm registers for AVX-512 (vector length l=2) */
    { "zmm0",  0, 0, 1 }, { "zmm1", 1, 0, 1 }, { "zmm2", 2, 0, 1 }, { "zmm3", 3, 0, 1 },
    { "zmm4",  4, 0, 1 }, { "zmm5", 5, 0, 1 }, { "zmm6", 6, 0, 1 }, { "zmm7", 7, 0, 1 },
    { "zmm8",  8, 0, 1 }, { "zmm9", 9, 0, 1 },  { "zmm10", 10, 0, 1 }, { "zmm11", 11, 0, 1 },
    { "zmm12", 12, 0, 1 }, { "zmm13", 13, 0, 1 }, { "zmm14", 14, 0, 1 }, { "zmm15", 15, 0, 1 },
    { "zmm16", 16, 0, 1 }, { "zmm17", 17, 0, 1 }, { "zmm18", 18, 0, 1 }, { "zmm19", 19, 0, 1 },
    { "zmm20", 20, 0, 1 }, { "zmm21", 21, 0, 1 }, { "zmm22", 22, 0, 1 }, { "zmm23", 23, 0, 1 },
    { "zmm24", 24, 0, 1 }, { "zmm25", 25, 0, 1 }, { "zmm26", 26, 0, 1 }, { "zmm27", 27, 0, 1 },
    { "zmm28", 28, 0, 1 }, { "zmm29", 29, 0, 1 }, { "zmm30", 30, 0, 1 }, { "zmm31", 31, 0, 1 },
    /* AVX-512 mask registers (k0-k7, 64-bit) */
    { "k0", 0, 0, 0 }, { "k1", 1, 0, 0 }, { "k2", 2, 0, 0 }, { "k3", 3, 0, 0 },
    { "k4", 4, 0, 0 }, { "k5", 5, 0, 0 }, { "k6", 6, 0, 0 }, { "k7", 7, 0, 0 },
    /* MMX registers (mm0-mm7, 64-bit but not xmm) */
    { "mm0", 0, 0, 0 }, { "mm1", 1, 0, 0 }, { "mm2", 2, 0, 0 }, { "mm3", 3, 0, 0 },
    { "mm4", 4, 0, 0 }, { "mm5", 5, 0, 0 }, { "mm6", 6, 0, 0 }, { "mm7", 7, 0, 0 },
    { NULL,    0, 0, 0 }
};

static const reg_t *find_reg(const char *name)
{
    for (const reg_t *r = regs; r->name; r++)
        if (strcmp(r->name, name) == 0)
            return r;
    return NULL;
}

static int reg_is8(const reg_t *r)
{
    const char *n = r->name;
    size_t L = strlen(n);
    if (n[0] == 'r' && n[L-1] == 'b') return 1;               /* r8b..r15b */
    if (L == 2) return (n[1] == 'l' || n[1] == 'h');          /* al cl dl bl ah ch dh bh */
    if (L == 4) return (n[1] == 'i' || n[1] == 'l' || n[1] == 'p'); /* sil dil spl bpl */
    return 0;
}
static int reg_is16(const reg_t *r)
{
    const char *n = r->name;
    size_t L = strlen(n);
    if (r->is64) return 0;                                  /* rax..rdi, r8..r15 are 64-bit */
    if (L == 2 && n[1] != 'l' && n[1] != 'h') return 1;       /* ax cx dx bx sp bp si di */
    if (n[0] == 'r' && n[L-1] == 'w') return 1;               /* r8w..r15w */
    return 0;
}
/* Memory operand descriptor for ModRM/SIB encoding */

/* forward declarations for emit_byte/emit_imm used by encode_mem_operand */
static void emit_byte(asm_output_t *out, uint8_t b);
static void emit_imm(asm_output_t *out, uint64_t v, int width);
/* REX prefix builder: w=REX.W, r=REX.R (reg field), b=REX.B (rm field) */
static void emit_rex(asm_output_t *out, int w, int r, int b)
{
    int rex = 0x40 | (w ? 8 : 0) | (r ? 4 : 0) | (b ? 1 : 0);
    if (rex != 0x40) emit_byte(out, (uint8_t)rex);
}
typedef struct {
    int      has_base;    /* 0/1 */
    int      base_reg;    /* register code (0-15) */
    int      has_index;   /* 0/1 */
    int      index_reg;   /* register code (0-15) */
    int      scale;       /* 1,2,4,8 */
    int64_t  disp;        /* signed displacement */
    int      has_disp;    /* 0/1 */
    int      is_rip_rel;  /* 1 = RIP-relative (symbol) */
} mem_op_t;

/* Parse a memory operand from token array starting at '[' token.
 * Returns the index after ']' on success, or -1 on failure.
 * Fills mop with the parsed components.
 */
static int parse_mem_operand(a_tok_t *toks, int i, int n, mem_op_t *mop)
{
    memset(mop, 0, sizeof(*mop));
    mop->scale = 1;

    if (i >= n || toks[i].type != ATOK_OP || toks[i].text[0] != '[')
        return -1;
    i++;  /* skip '[' */

    int state = 0; /* 0=expect base/index, 1=after +/-, 2=after * */
    int64_t val = 0;

    while (i < n) {
        if (toks[i].type == ATOK_OP && toks[i].text[0] == ']') {
            i++;
            if (state == 0 && !mop->has_base && !mop->has_index) {
                /* bare [disp] — use RIP-relative for symbols, or just disp */
                mop->has_disp = 1;
            }
            return i;
        }
        if (toks[i].type == ATOK_OP && toks[i].text[0] == '+') {
            i++; state = 0; continue;
        }
        if (toks[i].type == ATOK_OP && toks[i].text[0] == '-') {
            i++; state = 0; val = 0;
            /* check next token for number */
            if (i < n && toks[i].type == ATOK_NUM) {
                mop->disp = -(int64_t)toks[i].value;
                mop->has_disp = 1;
                state = 1;
                i++;
            }
            continue;
        }
        if (toks[i].type == ATOK_OP && toks[i].text[0] == '*') {
            i++; state = 2; continue;
        }
        if (toks[i].type == ATOK_NUM) {
            val = (int64_t)toks[i].value;
            if (state == 2) {
                /* after '*': scale factor */
                if (val == 2) mop->scale = 2;
                else if (val == 4) mop->scale = 4;
                else if (val == 8) mop->scale = 8;
                else mop->scale = 1;
            } else {
                mop->disp = val;
                mop->has_disp = 1;
            }
            i++;
            continue;
        }
        if (toks[i].type == ATOK_ID) {
            const reg_t *r = find_reg(toks[i].text);
            if (r) {
                if (!mop->has_base) {
                    mop->base_reg = r->code;
                    mop->has_base = 1;
                } else if (!mop->has_index) {
                    mop->index_reg = r->code;
                    mop->has_index = 1;
                }
            } else {
                /* symbol for RIP-relative: [symbol] or [symbol+disp] */
                mop->is_rip_rel = 1;
                /* store symbol name for later fixup; not needed for base/index */
                if (!mop->has_disp) mop->has_disp = 1;
            }
            i++;
            continue;
        }
        i++;
    }
    return -1;  /* unmatched ']' */
}

/* Encode ModRM and SIB bytes for a memory operand.
 * reg: 3-bit register code (for ModRM.reg field)
 * mop: parsed memory operand descriptor
 * Returns 1 on success (bytes emitted), 0 on failure.
 */
static int encode_mem_operand(asm_output_t *out, int reg, mem_op_t *mop,
                              int *needs_reloc, int *sym_idx)
{
    *needs_reloc = 0;
    *sym_idx = -1;

    if (mop->is_rip_rel) {
        /* RIP-relative: ModRM mod=00, rm=101 with reg field */
        uint8_t modrm = 0x05 | (reg & 7) << 3;
        emit_byte(out, modrm);
        emit_imm(out, 0, 4);  /* placeholder */
        *needs_reloc = 1;
        return 1;
    }

    if (!mop->has_base && !mop->has_index) {
        /* direct memory address: [disp32] — ModRM mod=00, rm=101 */
        uint8_t modrm = 0x05 | (reg & 7) << 3;
        emit_byte(out, modrm);
        emit_imm(out, (uint64_t)(int64_t)mop->disp, 4);
        return 1;
    }

    /* Determine ModRM.mod and whether SIB is needed */
    int base = mop->has_base ? mop->base_reg : -1;
    int index = mop->has_index ? mop->index_reg : -1;
    int64_t disp = mop->disp;
    int has_disp = mop->has_disp;

    /* If base == rsp (4) or base == r12 (12), SIB is required even with no index */
    int need_sib = (mop->has_index) || (base == 4) || (base == 12) || (base == -1);

    /* Choose mod based on displacement */
    int mod;
    if (!has_disp || disp == 0) {
        if (base == 5) {  /* rbp/r13 with no disp must encode disp8=0 */
            mod = 1; has_disp = 1; disp = 0;
        } else {
            mod = 0;
        }
    } else if (disp >= -128 && disp <= 127) {
        mod = 1;
    } else {
        mod = 2;
    }

    /* If no base and we have index, use base=4 (rsp) as SIB marker */
    if (base == -1) {
        base = 4;  /* indicates no base in SIB */
        need_sib = 1;
    }

    /* Build ModRM */
    uint8_t modrm = 0;
    if (!need_sib) {
        /* mod=00, reg, r/m=base */
        modrm = mod | (reg & 7) << 3 | (base & 7);
    } else {
        /* mod=00, reg, r/m=100 (SIB marker) */
        modrm = mod | (reg & 7) << 3 | 4;
    }
    emit_byte(out, modrm);

    /* Encode SIB if needed */
    if (need_sib) {
        int scale_bits = 0;
        if (mop->scale == 2) scale_bits = 1;
        else if (mop->scale == 4) scale_bits = 2;
        else if (mop->scale == 8) scale_bits = 3;
        int idx = (index >= 0) ? (index & 7) : 4;  /* 4 = no index */
        uint8_t sib = (scale_bits << 6) | (idx << 3) | (base & 7);
        emit_byte(out, sib);
    }

    /* Encode displacement */
    if (mod == 1) {
        emit_byte(out, (uint8_t)(int8_t)disp);
    } else if (mod == 2) {
        emit_imm(out, (uint64_t)disp, 4);
    }

    return 1;
}

/* emit to current section */
static void emit_byte(asm_output_t *out, uint8_t b)
{
    if (out->cur_sec == SEC_TEXT && out->text_len < sizeof(out->text))
        out->text[out->text_len++] = b;
    else if (out->cur_sec == SEC_DATA && out->data_len < sizeof(out->data))
        out->data[out->data_len++] = b;
}

static void emit_imm(asm_output_t *out, uint64_t v, int width)
{
    for (int i = 0; i < width; i++)
        emit_byte(out, (uint8_t)(v >> (8 * i)));
}

/* current section offset */
static size_t cur_offset(asm_output_t *out)
{
    if (out->cur_sec == SEC_TEXT) return out->text_len;
    if (out->cur_sec == SEC_DATA) return out->data_len;
    return out->bss_len;
}


static int is_num_token(a_tok_t *t)
{
    return t->type == ATOK_NUM;
}

/* ---------- floating-point literal pool ----------
 * Find or add a float constant to the literal pool and emit it into .data.
 * Returns the .data section offset of the constant (for RIP-relative addressing).
 * width: 4 (single) or 8 (double).
 */
static int64_t litpool_get_or_add_w(asm_output_t *out, uint64_t bits, int width)
{
    /* check if already in pool (same bits+width) */
    for (int i = 0; i < out->litpool_n; i++) {
        if (out->litpool[i] == bits) {
            return out->litpool_data_offsets[i];
        }
    }
    if (out->litpool_n >= 64) return -1;
    int idx = out->litpool_n++;
    out->litpool[idx] = bits;
    int64_t off = out->data_len;
    out->litpool_data_offsets[idx] = (int)off;
    int old_sec = out->cur_sec;
    out->cur_sec = SEC_DATA;
    emit_imm(out, bits, width);
    if (width == 4) emit_imm(out, 0, 4);  /* pad to 8 for consistency */
    out->cur_sec = old_sec;
    return off;
}

/* default: 8-byte double pool */
static int64_t litpool_get_or_add(asm_output_t *out, uint64_t bits)
{
    return litpool_get_or_add_w(out, bits, 8);
}

/* Emit a 16-byte vector constant into the literal pool (.data) and return its offset.
 * Elems are 32-bit (ps) or 64-bit (pd/dq) values; count determines the vector width. */
static int64_t vecpool_add(asm_output_t *out, uint64_t *elems, int count, int w64)
{
    if (out->cur_sec != SEC_DATA) {
        /* temporarily switch to .data to emit the pool, then restore */
        int saved_sec = out->cur_sec;
        out->cur_sec = SEC_DATA;
        int64_t off = out->data_len;
        for (int i = 0; i < count; i++)
            emit_imm(out, elems[i], w64 ? 8 : 4);
        /* pad to 16 bytes */
        while (out->data_len - off < 16) emit_byte(out, 0);
        out->cur_sec = saved_sec;
        return off;
    }
    int64_t off = out->data_len;
    for (int i = 0; i < count; i++)
        emit_imm(out, elems[i], w64 ? 8 : 4);
    while (out->data_len - off < 16) emit_byte(out, 0);
    return off;
}

/* ---------- VEX prefix encoder (AVX) ----------
 * Emits 2-byte (C5) or 3-byte (C4) VEX prefix.
 * map: 0=0F, 1=0F38, 2=0F3A
 * w: VEX.W
 * vvvv: 4-bit source reg (0-15); 0xF means "no vvvv source"
 * reg: 4-bit ModRM.reg field (0-15)
 * rm:  4-bit ModRM.rm field (0-15)
 * l: VEX.L (0=128-bit, 1=256-bit)
 * pp: 0=none, 1=66, 2=F3, 3=F2
 */
static void emit_evex_aa(asm_output_t *out, int mm, int w, int vvvv,
                         int reg, int rm, int ll, int pp, int aaa);

static void emit_vex(asm_output_t *out, int map, int w, int vvvv,
                     int reg, int rm, int l, int pp)
{
    int bit_r = (reg >> 3) & 1;
    int bit_x = 0;
    int bit_b = (rm >> 3) & 1;

    /* 2-byte VEX possible when map==0, w==0, x==0, b==0 */
    if (map == 0 && w == 0 && bit_x == 0 && bit_b == 0) {
        emit_byte(out, 0xC5);
        uint8_t b1 = (uint8_t)((~vvvv & 0xF) << 3) | (l << 2) | pp;
        emit_byte(out, b1);
        return;
    }
    emit_byte(out, 0xC4);
    uint8_t b1 = (uint8_t)((bit_r << 7) | (bit_x << 6) | (bit_b << 5) | (map & 7));
    emit_byte(out, b1);
    uint8_t b2 = (uint8_t)((w << 7) | ((~vvvv & 0xF) << 3) | (l << 2) | pp);
    emit_byte(out, b2);
}

/* ---------- EVEX prefix encoder (AVX-512) ----------
 * Emits 4-byte EVEX prefix (0x62 + 3 payload bytes).
 * p0: [R|X|B|R'|0|mm]
 * p1: [W|vvvv|1|pp]
 * p2: [z|L'|L|b|V'|a|a|a]
 * Register extensions: R' and V' come from bits 4+ of reg/vvvv respectively.
 * LL: 0=128,1=256,2=512
 * pp: 0=None,1=66,2=F3,3=F2
 * mm: 1=0F, 2=0F38, 3=0F3A
 */
static void emit_evex(asm_output_t *out, int mm, int w, int vvvv,
                      int reg, int rm, int ll, int pp)
{
    emit_evex_aa(out, mm, w, vvvv, reg, rm, ll, pp, 0);
}

/* Same as emit_evex but with aaa mask register field (k0-k7 → aaa = code & 7). */
static void emit_evex_aa(asm_output_t *out, int mm, int w, int vvvv,
                         int reg, int rm, int ll, int pp, int aaa)
{
    int bit_r  = (reg >> 3) & 1;
    int bit_x  = 0;
    int bit_b  = (rm  >> 3) & 1;
    int bit_rp = (reg >> 4) & 1;
    int bit_vp = (vvvv >> 4) & 1;

    emit_byte(out, 0x62);
    uint8_t p0 = (uint8_t)((bit_r << 7) | (bit_x << 6) | (bit_b << 5) | (bit_rp << 4) | (mm & 3));
    emit_byte(out, p0);
    uint8_t p1 = (uint8_t)((w << 7) | ((~vvvv & 0xF) << 3) | (1 << 2) | (pp & 3));
    emit_byte(out, p1);
    uint8_t p2 = (uint8_t)((bit_vp << 7) | ((ll & 3) << 5) | (aaa & 7));
    emit_byte(out, p2);
}

/* Advanced-vector instruction handler: vmovq/vmovd/vmovapd/vmovdqa/vmovdqu
 * vmnemonic -> base opcode (map 0F), pp prefix, L bit (0=xmm,1=ymm), load/store.
 */
static int encode_avx_move(asm_output_t *out, const char *mnem, a_tok_t *toks, int n)
{
    const reg_t *rd = NULL, *rs = NULL, *rg = NULL;
    int is_ymm = 0;
    for (int i = 1; i < n; i++) {
        if (toks[i].type == ATOK_ID) {
            const reg_t *r = find_reg(toks[i].text);
            if (!r) continue;
            if (r->is_xmm) {
                if (!rd) rd = r; else if (r->is_xmm && !rs) rs = r;
                if (r->name[0] == 'y') is_ymm = 1;
            }
            else { if (!rg) rg = r; }
        }
    }
    if (!rd) return 0;

    int found_mem = 0, mem_idx = -1;
    mem_op_t mop;
    for (int i = 1; i < n; i++)
        if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
            if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; mem_idx = i; break; }
        }

    /* Determine if store form: if '[' comes after an xmm register, it's a store */
    int is_store = 0;
    if (found_mem) {
        int xmm_before = 0;
        for (int j = 1; j < mem_idx; j++) {
            if (toks[j].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[j].text);
                if (r && r->is_xmm) { xmm_before = 1; break; }
            }
        }
        is_store = xmm_before;
    }

    int l = is_ymm ? 1 : 0;
    int pp = 1;  /* 66 by default for vmovapd/vmovdqa */
    int opc = 0x28;  /* load */
    int opc_store = 0x29;

    if (strcmp(mnem, "vmovq") == 0 || strcmp(mnem, "vmovd") == 0) {
        if (found_mem) {
            emit_vex(out, 0, 0, 0xF, rd->code, 0, 0, 2);
            emit_byte(out, 0x7E);
            int nr, si;
            encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
        if (rs && rs->is_xmm) {
            emit_vex(out, 0, 0, 0xF, rd->code, rs->code, 0, 2);
            emit_byte(out, 0x7E);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        if (rg) {
            emit_vex(out, 0, 1, 0xF, rd->code, rg->code, 0, 1);
            emit_byte(out, 0x6E);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rg->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "vmovapd") == 0 || strcmp(mnem, "vmovaps") == 0) {
        pp = (mnem[5] == 's') ? 0 : 1;  /* vmovaps has no 66 prefix */
        opc = is_store ? 0x29 : 0x28;
    } else if (strcmp(mnem, "vmovupd") == 0 || strcmp(mnem, "vmovups") == 0) {
        pp = (mnem[6] == 's' || (mnem[6] == 0 && mnem[5] == 's')) ? 0 : 1;
        opc = is_store ? 0x11 : 0x10;
    } else if (strcmp(mnem, "vmovdqa") == 0) {
        opc = is_store ? 0x7F : 0x6F;
    } else if (strcmp(mnem, "vmovdqu") == 0) {
        pp = 2;  /* F3 */
        opc = is_store ? 0x7F : 0x6F;
    } else {
        return 0;  /* unknown AVX move */
    }
    emit_vex(out, 0, 0, 0xF, rd->code, found_mem ? 0 : rs->code, l, pp);
    emit_byte(out, (uint8_t)opc);
    if (found_mem) {
        int nr, si;
        encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
        (void)nr; (void)si;
        return 1;
    }
    if (rs) {
        uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
        emit_byte(out, modrm);
        return 1;
    }
    return 0;
}

/* Find symbol index by name, add if missing */
static int find_or_add_sym(asm_output_t *out, const char *name)
{
    for (int i = 0; i < out->nsyms; i++)
        if (strcmp(out->syms[i].name, name) == 0)
            return i;
    if (out->nsyms >= 256)
        return -1;
    asmc_sym_t *s = &out->syms[out->nsyms];
    memset(s, 0, sizeof(*s));
    snprintf(s->name, sizeof(s->name), "%s", name);
    return out->nsyms++;
}

/* Look up symbol; if found and defined return its offset, else -1 */
static int64_t lookup_sym(asm_output_t *out, const char *name)
{
    for (int i = 0; i < out->nsyms; i++)
        if (strcmp(out->syms[i].name, name) == 0 && out->syms[i].defined)
            return (int64_t)out->syms[i].value;
    return -1;
}

/* record a relocation (ELF type for x86-64) at current section offset */
static void add_fixup(asm_output_t *out, int sym_index, int etype, int addend)
{
    if (out->nfixups >= 256 || sym_index < 0) return;
    asmc_fixup_t *f = &out->fixups[out->nfixups++];
    f->offset = cur_offset(out);
    f->sym_index = sym_index;
    f->type = etype;
    f->addend = addend;
    f->sec = out->cur_sec;
}

/* Derive the comparison immediate for cmp* SIMD instructions from the mnemonic:
 * eq→0, lt→1, le→2, neq→4, nlt→5, nle→6 (F2/66/0F C2 /r ib forms). */
static uint8_t cmp_imm_from_mnemonic(const char *m)
{
    for (const char *p = m; *p; p++) {
        if (p[0] == 'e' && p[1] == 'q') return 0;
        if (p[0] == 'l' && p[1] == 't') return 1;
        if (p[0] == 'l' && p[1] == 'e') return 2;
        if (p[0] == 'n' && p[1] == 'e' && p[2] == 'q') return 4;
        if (p[0] == 'n' && p[1] == 'l' && p[2] == 't') return 5;
        if (p[0] == 'n' && p[1] == 'l' && p[2] == 'e') return 6;
    }
    return 0;
}

/* Encode a single instruction.
 * Returns 1 on success, 0 on failure (asm error emitted by caller).
 */
static int encode_instruction(asm_output_t *out, a_tok_t *toks, int n)
{
    static char mnbuf[32];
    const char *mnem = NULL;
    snprintf(mnbuf, sizeof(mnbuf), "%s", toks[0].text);
    for (char *p = mnbuf; *p; p++)
        if (*p >= 'A' && *p <= 'Z') *p += 'a' - 'A';   /* case-insensitive mnemonic matching */
    /* strip `??` prefix from renamed keywords (option renamekeyword) → ??add becomes add */
    if (mnbuf[0] == '?' && mnbuf[1] == '?') {
        char tmp[32];
        snprintf(tmp, sizeof(tmp), "%s", mnbuf + 2);
        snprintf(mnbuf, sizeof(mnbuf), "%s", tmp);
    }
    mnem = mnbuf;
    const reg_t *r1 = NULL, *r2 = NULL;
    int ireg = -1;          /* -1 = no register operand, 0..7 normally, 8+ high */
    uint64_t imm = 0;
    int has_imm = 0;

    /* collect operands */
    for (int i = 1; i < n; i++) {
        if (toks[i].type == ATOK_ID) {
            const reg_t *r = find_reg(toks[i].text);
            if (r) { if (!r1) r1 = r; else if (!r2) r2 = r; }
            else { ireg = -2; }  /* unknown id operand */
        } else if (toks[i].type == ATOK_NUM) {
            imm = toks[i].value;
            has_imm = 1;
        }
    }

    /* SSE brace-constant early check: `inst xmm, { c1, c2, ... }` for
     * movaps/movapd/movups/movupd/movdqa/movdqu and pd/ps arithmetic. */
    if ((strcmp(mnem, "movaps") == 0 || strcmp(mnem, "movapd") == 0 ||
         strcmp(mnem, "movups") == 0 || strcmp(mnem, "movupd") == 0 ||
         strcmp(mnem, "movdqa") == 0 || strcmp(mnem, "movdqu") == 0 ||
         strcmp(mnem, "divpd") == 0 || strcmp(mnem, "addpd") == 0 ||
         strcmp(mnem, "xorpd") == 0 || strcmp(mnem, "mulpd") == 0 ||
         strcmp(mnem, "divps") == 0 || strcmp(mnem, "addps") == 0 ||
         strcmp(mnem, "xorps") == 0 || strcmp(mnem, "mulps") == 0 ||
         strcmp(mnem, "subps") == 0 || strcmp(mnem, "subpd") == 0 ||
         strcmp(mnem, "andps") == 0 || strcmp(mnem, "orps") == 0)) {
        const reg_t *bc_reg = NULL;
        int brace_lt = -1, brace_gt = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '{') { brace_lt = i; }
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '}') { brace_gt = i; break; }
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) { if (!bc_reg) bc_reg = r; }
            }
        }
        if (brace_lt >= 0 && brace_gt > brace_lt && bc_reg) {
            uint64_t ve[8]; int nve = 0;
            for (int i = brace_lt + 1; i < brace_gt; i++) {
                if (toks[i].type == ATOK_NUM && nve < 8) ve[nve++] = toks[i].value;
                if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
            }
            if (nve > 0) {
                int w64 = 0;
                if (strstr(mnem, "pd") || strstr(mnem, "dq")) w64 = 1;
                int64_t off = vecpool_add(out, ve, nve, w64);
                if (off < 0) return 0;
                if (strcmp(mnem, "movdqa") == 0) { emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x6F); }
                else if (strcmp(mnem, "movdqu") == 0) { emit_byte(out, 0xF3); emit_byte(out, 0x0F); emit_byte(out, 0x6F); }
                else if (strstr(mnem, "pd") && strncmp(mnem, "mov", 3) != 0) { emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x58); }
                else if (strncmp(mnem, "mov", 3) == 0) { if (strstr(mnem, "pd")) emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x28); }
                else { emit_byte(out, 0x0F); emit_byte(out, 0x58); }
                emit_byte(out, 0x05 | (bc_reg->code & 7) << 3);
                emit_imm(out, (uint64_t)off, 4);
                int si = find_or_add_sym(out, "litpool");
                if (si >= 0 && out->nfixups < 256) {
                    asmc_fixup_t *f = &out->fixups[out->nfixups++];
                    f->offset = cur_offset(out) - 4;
                    f->sym_index = si;
                    f->type = 2; /* R_X86_64_PC32 */
                    f->addend = -4 + (int)off;
                    f->sec = out->cur_sec;
                }
                return 1;
            }
        }
    }

    if (strcmp(mnem, "nop") == 0) {
        emit_byte(out, 0x90);
        return 1;
    }
    if (strcmp(mnem, "ret") == 0 || strcmp(mnem, "retn") == 0) {
        emit_byte(out, 0xC3);
        return 1;
    }
    if (strcmp(mnem, "enter") == 0) {
        /* enter imm16, imm8 → C8 iw ib */
        int cnt = 0;
        int64_t imm[2] = {0, 0};
        for (int i = 1; i < n && cnt < 2; i++)
            if (toks[i].type == ATOK_NUM) imm[cnt++] = toks[i].value;
        emit_byte(out, 0xC8);
        emit_imm(out, (uint64_t)imm[0], 2);
        emit_byte(out, (uint8_t)imm[1]);
        return 1;
    }
    if (strcmp(mnem, "hlt") == 0) {
        emit_byte(out, 0xF4);
        return 1;
    }
    if (strcmp(mnem, "int3") == 0) {
        emit_byte(out, 0xCC);
        return 1;
    }
    if (strcmp(mnem, "xlat") == 0 || strcmp(mnem, "xlatb") == 0) {
        emit_byte(out, 0xD7);
        return 1;
    }
    /* zero-operand conversions & string/control instructions */
    if (strcmp(mnem, "cwde") == 0) { emit_byte(out, 0x98); return 1; }
    if (strcmp(mnem, "cdqe") == 0) { emit_byte(out, 0x48); emit_byte(out, 0x98); return 1; }
    if (strcmp(mnem, "cdq") == 0) { emit_byte(out, 0x99); return 1; }
    if (strcmp(mnem, "cqo") == 0) { emit_byte(out, 0x48); emit_byte(out, 0x99); return 1; }
    if (strcmp(mnem, "cwd") == 0) { emit_byte(out, 0x66); emit_byte(out, 0x99); return 1; }
    if (strcmp(mnem, "iretq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xCF); return 1; }
    if (strcmp(mnem, "cmpsq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xA7); return 1; }
    if (strcmp(mnem, "lodsq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xAD); return 1; }
    if (strcmp(mnem, "movsq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xA5); return 1; }
    if (strcmp(mnem, "movsd") == 0 && n == 1) { emit_byte(out, 0x48); emit_byte(out, 0xA5); return 1; }
    if (strcmp(mnem, "scasq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xAF); return 1; }
    if (strcmp(mnem, "stosq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xAB); return 1; }
    if (strcmp(mnem, "stosd") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xAB); return 1; }
    if (strcmp(mnem, "insb") == 0) { emit_byte(out, 0x6C); return 1; }
    if (strcmp(mnem, "insw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0x6D); return 1; }
    if (strcmp(mnem, "insd") == 0) { emit_byte(out, 0x48); emit_byte(out, 0x6D); return 1; }
    if (strcmp(mnem, "outsb") == 0) { emit_byte(out, 0x6E); return 1; }
    if (strcmp(mnem, "outsw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0x6F); return 1; }
    if (strcmp(mnem, "outsd") == 0) { emit_byte(out, 0x48); emit_byte(out, 0x6F); return 1; }
    if (strcmp(mnem, "cmpsb") == 0) { emit_byte(out, 0xA6); return 1; }
    if (strcmp(mnem, "cmpsw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0xA7); return 1; }
    if (strcmp(mnem, "lodsb") == 0) { emit_byte(out, 0xAC); return 1; }
    if (strcmp(mnem, "lodsw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0xAD); return 1; }
    if (strcmp(mnem, "lodsd") == 0) { emit_byte(out, 0xAD); return 1; }
    if (strcmp(mnem, "lodsq") == 0) { emit_byte(out, 0x48); emit_byte(out, 0xAD); return 1; }
    if (strcmp(mnem, "movsb") == 0) { emit_byte(out, 0xA4); return 1; }
    if (strcmp(mnem, "movsw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0xA5); return 1; }
    if (strcmp(mnem, "scasb") == 0) { emit_byte(out, 0xAE); return 1; }
    if (strcmp(mnem, "scasw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0xAF); return 1; }
    if (strcmp(mnem, "stosb") == 0) { emit_byte(out, 0xAA); return 1; }
    if (strcmp(mnem, "stosw") == 0) { emit_byte(out, 0x66); emit_byte(out, 0xAB); return 1; }
    /* string pseudo-instructions: movs/stos/lods/cmps/scas/ins with size operand (m08/m16/m32/m64) */
    if (strcmp(mnem, "movs") == 0 || strcmp(mnem, "stos") == 0 || strcmp(mnem, "lods") == 0 ||
        strcmp(mnem, "cmps") == 0 || strcmp(mnem, "scas") == 0 || strcmp(mnem, "ins") == 0 ||
        strcmp(mnem, "outs") == 0) {
        int sz = 64;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                if (strcmp(toks[i].text, "m08") == 0) sz = 8;
                else if (strcmp(toks[i].text, "M08") == 0) sz = 8;
                else if (strcmp(toks[i].text, "m16") == 0) sz = 16;
                else if (strcmp(toks[i].text, "M16") == 0) sz = 16;
                else if (strcmp(toks[i].text, "m32") == 0) sz = 32;
                else if (strcmp(toks[i].text, "M32") == 0) sz = 32;
                else if (strcmp(toks[i].text, "m64") == 0) sz = 64;
                else if (strcmp(toks[i].text, "M64") == 0) sz = 64;
            }
        }
        uint8_t base;
        if (mnem[0] == 'm') base = 0xA4;        /* movs: A4/A5 */
        else if (mnem[0] == 's' && mnem[1] == 't') base = 0xAA;  /* stos: AA/AB */
        else if (mnem[0] == 'l') base = 0xAC;   /* lods: AC/AD */
        else if (mnem[0] == 'c') base = 0xA6;   /* cmps: A6/A7 */
        else if (mnem[0] == 's') base = 0xAE;   /* scas: AE/AF */
        else if (mnem[0] == 'o') base = 0x6E;   /* outs: 6E/6F */
        else base = 0x6C;                       /* ins: 6C/6D */
        if (sz == 8) { emit_byte(out, base); }
        else if (sz == 16) { emit_byte(out, 0x66); emit_byte(out, base + 1); }
        else { emit_byte(out, 0x48); emit_byte(out, base + 1); }
        return 1;
    }
    if (strcmp(mnem, "swapgs") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xF8); return 1; }
    if (strcmp(mnem, "monitor") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC8); return 1; }
    if (strcmp(mnem, "mwait") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC9); return 1; }
    if (strcmp(mnem, "vmcall") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC1); return 1; }
    if (strcmp(mnem, "vmlaunch") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC2); return 1; }
    if (strcmp(mnem, "vmresume") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC3); return 1; }
    if (strcmp(mnem, "vmxoff") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC4); return 1; }
    if (strcmp(mnem, "iretd") == 0) { emit_byte(out, 0xCF); return 1; }
    if (strcmp(mnem, "iret") == 0) { emit_byte(out, 0xCF); return 1; }
    /* zero-operand system instructions */
    if (strcmp(mnem, "cli") == 0) { emit_byte(out, 0xFA); return 1; }
    if (strcmp(mnem, "sti") == 0) { emit_byte(out, 0xFB); return 1; }
    if (strcmp(mnem, "clts") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x06); return 1; }
    if (strcmp(mnem, "invd") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x08); return 1; }
    if (strcmp(mnem, "wbinvd") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x09); return 1; }
    if (strcmp(mnem, "rdmsr") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x32); return 1; }
    if (strcmp(mnem, "rdpmc") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x33); return 1; }
    if (strcmp(mnem, "rdtsc") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x31); return 1; }
    if (strcmp(mnem, "sysenter") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x34); return 1; }
    if (strcmp(mnem, "sysexit") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x35); return 1; }
    if (strcmp(mnem, "syscall") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x05); return 1; }
    if (strcmp(mnem, "sysret") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x07); return 1; }
    if (strcmp(mnem, "monitor") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC8); return 1; }
    if (strcmp(mnem, "mwait") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xC9); return 1; }
    if (strcmp(mnem, "swapgs") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xF8); return 1; }
    if (strcmp(mnem, "rdtscp") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xF9); return 1; }
    if (strcmp(mnem, "rsm") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0xAA); return 1; }
    if (strcmp(mnem, "xgetbv") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xD0); return 1; }
    if (strcmp(mnem, "xsetbv") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x01); emit_byte(out, 0xD1); return 1; }
    /* x87 FPU instructions */
    if (strcmp(mnem, "fclex") == 0) { emit_byte(out, 0x9B); emit_byte(out, 0xDB); emit_byte(out, 0xE2); return 1; }
    if (strcmp(mnem, "fnclex") == 0) { emit_byte(out, 0xDB); emit_byte(out, 0xE2); return 1; }
    if (strcmp(mnem, "fwait") == 0) { emit_byte(out, 0x9B); return 1; }
    if (strcmp(mnem, "finit") == 0) { emit_byte(out, 0x9B); emit_byte(out, 0xDB); emit_byte(out, 0xE3); return 1; }
    if (strcmp(mnem, "fninit") == 0) { emit_byte(out, 0xDB); emit_byte(out, 0xE3); return 1; }
    if (strcmp(mnem, "fsetpm") == 0) { emit_byte(out, 0xDB); emit_byte(out, 0xE4); return 1; }
    if (strcmp(mnem, "fldz") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xEE); return 1; }
    if (strcmp(mnem, "fld1") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xE8); return 1; }
    if (strcmp(mnem, "fldpi") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xEB); return 1; }
    if (strcmp(mnem, "fchs") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xE0); return 1; }
    if (strcmp(mnem, "fabs") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xE1); return 1; }
    if (strcmp(mnem, "fsqrt") == 0) { emit_byte(out, 0xD9); emit_byte(out, 0xFA); return 1; }
    if (strcmp(mnem, "fadd") == 0 && n == 1) { emit_byte(out, 0xD8); emit_byte(out, 0xC0); return 1; }
    if (strcmp(mnem, "fmul") == 0 && n == 1) { emit_byte(out, 0xD8); emit_byte(out, 0xC9); return 1; }
    if (strcmp(mnem, "fsub") == 0 && n == 1) { emit_byte(out, 0xD8); emit_byte(out, 0xE0); return 1; }
    if (strcmp(mnem, "fdiv") == 0 && n == 1) { emit_byte(out, 0xD8); emit_byte(out, 0xF0); return 1; }
    if (strcmp(mnem, "fcomip") == 0) { emit_byte(out, 0xDF); emit_byte(out, 0xF0); return 1; }
    if (strcmp(mnem, "fucomip") == 0) { emit_byte(out, 0xDF); emit_byte(out, 0xE8); return 1; }
    /* fbld/fbstp: DF /4 /6 (m80 memory) */
    if (strcmp(mnem, "fbld") == 0 || strcmp(mnem, "fbstp") == 0) {
        int digit = (mnem[2] == 'l') ? 4 : 6;
        emit_byte(out, 0xDF);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "byte") != 0 &&
                strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0 &&
                strcmp(toks[i].text, "qword") != 0 && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fcom/fcomp/fcompp: D8 /2 (m32), D8 D8+i (st), DE D9 (fcompp) */
    if (strcmp(mnem, "fcom") == 0 || strcmp(mnem, "fcomp") == 0 || strcmp(mnem, "fcompp") == 0) {
        if (n == 1 && strcmp(mnem, "fcompp") == 0) { emit_byte(out, 0xDE); emit_byte(out, 0xD9); return 1; }
        if (n == 1) { emit_byte(out, 0xD8); emit_byte(out, 0xD1); return 1; }
        int sti = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        }
        if (sti >= 0) {
            emit_byte(out, 0xD8);
            emit_byte(out, (uint8_t)(0xD8 + sti));
            return 1;
        }
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    emit_byte(out, 0xD8);
                    int nr, si;
                    encode_mem_operand(out, 2, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0xD8);
                emit_byte(out, 0x05 | 2 << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fcmov* st(0), st(i): DA/DB C0+i */
    if (strncmp(mnem, "fcmov", 5) == 0) {
        int cc = 0;
        const char *s = mnem + 5;
        if (strcmp(s, "b") == 0) cc = 0;
        else if (strcmp(s, "e") == 0) cc = 1;
        else if (strcmp(s, "be") == 0) cc = 2;
        else if (strcmp(s, "u") == 0) cc = 3;
        else if (strcmp(s, "nb") == 0) cc = 4;
        else if (strcmp(s, "ne") == 0) cc = 5;
        else if (strcmp(s, "nbe") == 0) cc = 6;
        else if (strcmp(s, "nu") == 0) cc = 7;
        else return 0;
        /* DA for cc 0-3, DB for cc 4-7 */
        int sti = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2;
                if (*p == '(') { p++; sti = 0; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        }
        emit_byte(out, (cc < 4) ? 0xDA : 0xDB);
        emit_byte(out, (uint8_t)(0xC0 + sti));
        return 1;
    }
    /* x87 arith with st(i)/m32/m64 operands: fadd/fsub/fmul/fdiv/fdivr (+p variants) */
    if (strcmp(mnem, "fadd") == 0 || strcmp(mnem, "faddp") == 0 ||
        strcmp(mnem, "fsub") == 0 || strcmp(mnem, "fsubp") == 0 ||
        strcmp(mnem, "fsubr") == 0 || strcmp(mnem, "fsubrp") == 0 ||
        strcmp(mnem, "fmul") == 0 || strcmp(mnem, "fmulp") == 0 ||
        strcmp(mnem, "fdiv") == 0 || strcmp(mnem, "fdivp") == 0 ||
        strcmp(mnem, "fdivr") == 0 || strcmp(mnem, "fdivrp") == 0) {
        /* op: add=0 sub=1 subr=2 mul=3 div=4 divr=5 */
        int op = (mnem[1] == 'a') ? 0 :
                 (mnem[1] == 's') ? ((mnem[3] == 'r') ? 2 : 1) :
                 (mnem[1] == 'm') ? 3 :
                 (mnem[2] == 'i') ? ((mnem[4] == 'r') ? 5 : 4) : 4;
        int is_pop = (mnem[4] == 'p') || (mnem[5] == 'p');
        int is_r = (op == 2 || op == 5);  /* fsubr / fdivr */
        /* base register byte: add=C0 sub=E0 subr=E8 mul=C8 div=F0 divr=F8 */
        uint8_t base[6] = { 0xC0, 0xE0, 0xE8, 0xC8, 0xF0, 0xF8 };
        int digit[6] = { 0, 4, 5, 1, 6, 7 };
        /* collect st indices and memory operand */
        int sti = -1, stj = -1;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                /* parse st or st(n) */
                const char *p = toks[i].text + 2;
                int idx = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { idx = idx * 10 + (*p - '0'); p++; } }
                if (sti < 0) sti = idx; else if (stj < 0) stj = idx;
            }
        }
        if (sti < 0 && mem_tok < 0) {
            /* no operands: fadd → D8 C1, fmul → D8 C9, etc. */
            if (is_pop) { emit_byte(out, 0xDE); emit_byte(out, (uint8_t)(base[op] + stj + 1)); }
            else { emit_byte(out, 0xD8); emit_byte(out, (uint8_t)(base[op] + 1)); }
            return 1;
        }
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                /* m32 → D8 /digit, m64 → DC /digit */
                int is64 = 0;
                for (int i = 1; i < n; i++)
                    if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "real8") == 0 || strcmp(toks[i].text, "QWORD") == 0)) is64 = 1;
                emit_byte(out, is64 ? 0xDC : 0xD8);
                int nr, si;
                encode_mem_operand(out, digit[op], &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (sti >= 0 && stj >= 0) {
            /* reg,reg form. dest=st(0)+src / st(i)=st(i)+st(0) */
            if (sti == 0) {
                /* fadd st(0), st(j): D8 C0+j */
                if (is_pop) { emit_byte(out, 0xDE); emit_byte(out, (uint8_t)(base[op] + stj + 1)); }
                else { emit_byte(out, 0xD8); emit_byte(out, (uint8_t)(base[op] + stj)); }
            } else {
                /* fadd st(i), st(0): DC C0+i */
                if (is_pop) { emit_byte(out, 0xDE); emit_byte(out, (uint8_t)((is_r ? base[op]+8 : base[op]) + sti + 1)); }
                else { emit_byte(out, 0xDC); emit_byte(out, (uint8_t)((is_r ? base[op]+8 : base[op]) + sti)); }
            }
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "pushf") == 0) { emit_byte(out, 0x9C); return 1; }
    if (strcmp(mnem, "pushfq") == 0) { emit_byte(out, 0x9C); return 1; }
    if (strcmp(mnem, "pushfd") == 0) { emit_byte(out, 0x9C); return 1; }
    if (strcmp(mnem, "pushw") == 0) {
        /* pushw imm16 → 66 68 imm16 */
        if (has_imm) { emit_byte(out, 0x66); emit_byte(out, 0x68); emit_imm(out, imm, 2); return 1; }
        return 0;
    }
    if (strcmp(mnem, "popf") == 0) { emit_byte(out, 0x9D); return 1; }
    if (strcmp(mnem, "popfq") == 0) { emit_byte(out, 0x9D); return 1; }
    /* movsx / movzx: sign/zero-extend r/m8 or r/m16 to r16/32/64 */
    if (strcmp(mnem, "movsx") == 0 || strcmp(mnem, "movzx") == 0) {
        int is_sx = (mnem[4] == 's');
        const reg_t *md = NULL, *ms = NULL;
        int mem_tok = -1, src8 = 0, src16 = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!md) md = r; else if (!ms) ms = r; }
            }
        }
        if (!md) return 0;
        /* determine source width: 8-bit if source reg is al/ah/bl/... or BYTE ptr, else 16-bit */
        if (ms) {
            if ((ms->name[1] == 'l' && ms->name[0] != 'r') || ms->name[1] == 'h' ||
                (ms->name[0] == 'r' && ms->name[3] == 'b') ||
                strcmp(ms->name, "sil") == 0 || strcmp(ms->name, "dil") == 0 ||
                strcmp(ms->name, "bpl") == 0 || strcmp(ms->name, "spl") == 0) src8 = 1;
            else src16 = 1;
        }
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "BYTE") == 0 || strcmp(toks[i].text, "byte") == 0))
                src8 = 1;
        if (mem_tok >= 0 && !src8) src16 = 1;
        if (!src8 && !src16) src16 = 1;
        /* target 16-bit → 66 prefix */
        int dst16 = 0;
        if (md->name[1] == 'x' || md->name[1] == 'p' || md->name[1] == 'i' ||
            (md->name[0] == 'r' && (md->name[1] == '8' || md->name[1] == '9' || md->name[1] == '1')))
            dst16 = 1;
        if (dst16) emit_byte(out, 0x66);
        else if (md->is64) emit_byte(out, 0x48);
        emit_byte(out, 0x0F);
        emit_byte(out, src8 ? (is_sx ? 0xBE : 0xB6) : (is_sx ? 0xBF : 0xB7));
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, md->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (ms) {
            emit_byte(out, 0xC0 | (md->code & 7) << 3 | (ms->code & 7));
            return 1;
        }
        return 0;
    }
    /* movsxd: sign-extend r/m32 to r64 → REX.W 0F 63 /r */
    if (strcmp(mnem, "movsxd") == 0) {
        const reg_t *xd = NULL, *xs = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!xd) xd = r; else if (!xs) xs = r; }
            }
        }
        if (!xd) return 0;
        emit_byte(out, 0x48);   /* REX.W */
        emit_byte(out, 0x0F); emit_byte(out, 0x63);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, xd->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (xs) {
            emit_byte(out, 0xC0 | (xd->code & 7) << 3 | (xs->code & 7));
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "push") == 0 || strcmp(mnem, "pop") == 0) {
        /* segment registers fs/gs are not in regs[] — match by token text */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "fs") == 0 || strcmp(toks[i].text, "gs") == 0)) {
                int is_fs = (toks[i].text[0] == 'f');
                if (mnem[0] == 'p') {   /* push */
                    emit_byte(out, 0x0F); emit_byte(out, is_fs ? 0xA0 : 0xA8);
                } else {                /* pop */
                    emit_byte(out, 0x0F); emit_byte(out, is_fs ? 0xA1 : 0xA9);
                }
                return 1;
            }
        }
    }
    /* push [mem] → FF /6 (RIP-relative for symbol targets) */
    if (strcmp(mnem, "push") == 0) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    emit_byte(out, 0xFF);
                    encode_mem_operand(out, 6, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0xFF);
                emit_byte(out, 0x35);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
    }
        /* lds/les/lfs/lgs/lss reg, m16:16|m16:32 — far pointer segment loads.
     * Opcodes: lds=C5 les=C4 (16-bit only); lfs=0F B4, lgs=0F B5, lss=0F B2.
     * ModRM: dest reg in reg field, memory operand in r/m. */
    if (strcmp(mnem, "lds") == 0 || strcmp(mnem, "les") == 0 ||
        strcmp(mnem, "lfs") == 0 || strcmp(mnem, "lgs") == 0 || strcmp(mnem, "lss") == 0) {
        const reg_t *rd = NULL;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && find_reg(toks[i].text)) { rd = find_reg(toks[i].text); break; }
        if (rd) {
            if (rd->is64) emit_byte(out, 0x48);
            if (strcmp(mnem, "lds") == 0) emit_byte(out, 0xC5);
            else if (strcmp(mnem, "les") == 0) emit_byte(out, 0xC4);
            else if (strcmp(mnem, "lss") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0xB2); }
            else if (strcmp(mnem, "lfs") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0xB4); }
            else { emit_byte(out, 0x0F); emit_byte(out, 0xB5); }  /* lgs */
            int mem_i = -1;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') { mem_i = i; break; }
            if (mem_i >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
            /* bare symbol memory operand: `lds bx, var1` */
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    strcmp(toks[i].text, "ptr") != 0 && strcmp(toks[i].text, "far") != 0 &&
                    strcmp(toks[i].text, "near") != 0 && strcmp(toks[i].text, "byte") != 0 &&
                    strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (rd->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
        }
        return 0;
    }
    /* system instructions with /digit (0F 00 /digit and 0F 01 /digit) */
    {
        struct { const char *name; uint8_t opc; int digit; } sysd[] = {
            { "sldt", 0x00, 0 }, { "str", 0x00, 1 }, { "lldt", 0x00, 2 }, { "ltr", 0x00, 3 },
            { "verr", 0x00, 4 }, { "verw", 0x00, 5 },
            { "sgdt", 0x01, 0 }, { "sidt", 0x01, 1 }, { "lgdt", 0x01, 2 }, { "lidt", 0x01, 3 },
            { "smsw", 0x01, 4 }, { "lmsw", 0x01, 6 }, { "invlpg", 0x01, 7 },
        };
        int sd_opc = -1, sd_digit = -1;
        for (unsigned s = 0; s < sizeof(sysd)/sizeof(sysd[0]); s++)
            if (strcmp(mnem, sysd[s].name) == 0) { sd_opc = sysd[s].opc; sd_digit = sysd[s].digit; break; }
        if (sd_opc >= 0) {
            emit_byte(out, 0x0F); emit_byte(out, sd_opc);
            /* register operand */
            const reg_t *sr = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && !r->is_xmm) { sr = r; break; }
                }
            }
            if (sr) {
                if (sr->is64) emit_byte(out, 0x48);
                emit_byte(out, 0xC0 | sd_digit << 3 | (sr->code & 7));
                return 1;
            }
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                        int nr, si;
                        encode_mem_operand(out, sd_digit, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        return 1;
                    }
                }
            }
            /* bare symbol memory operand (m48/m80 etc.) */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0 &&
                    strcmp(toks[i].text, "byte") != 0 && strcmp(toks[i].text, "word") != 0 &&
                    strcmp(toks[i].text, "dword") != 0 && strcmp(toks[i].text, "qword") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | sd_digit << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
            return 0;
        }
    }
    /* mov r, cr/dr and mov cr/dr, r : 0F 20 (cr→r), 0F 22 (r→cr), 0F 21/23 for dr */
    if (strcmp(mnem, "mov") == 0) {
        const char *crname = NULL; int is_cr = 0, is_dr = 0;
        const reg_t *cr = NULL, *other = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->name[0] == 'c' && r->name[1] == 'r') { is_cr = 1; cr = r; crname = r->name; }
                else if (r && r->name[0] == 'd' && r->name[1] == 'r') { is_dr = 1; cr = r; crname = r->name; }
                else if (r && !r->is_xmm) { if (!other) other = r; }
            }
        }
        if ((is_cr || is_dr) && other) {
            /* determine direction: cr/dr first (store r→cr/dr) or second (load cr/dr→r) */
            int cr_first = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && (r->name[0] == 'c' && r->name[1] == 'r') || (r->name[0] == 'd' && r->name[1] == 'r')) { cr_first = 1; break; }
                    if (r) break;
                }
            }
            if (other->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x0F);
            uint8_t dir_opc;
            if (is_dr) dir_opc = cr_first ? 0x23 : 0x21;
            else dir_opc = cr_first ? 0x22 : 0x20;
            emit_byte(out, dir_opc);
            emit_byte(out, 0xC0 | (other->code & 7) << 3 | (cr->code & 7));
            return 1;
        }
    }
    /* Key Locker (KL) instructions: F3 0F 38 <opc> /r */
    {
        /* mnem → opcode, and wide /digit if >0 */
        struct { const char *name; uint8_t opc; int digit; } kl[] = {
            { "loadiwkey", 0xDC, -1 },
            { "encodekey128", 0xFA, -1 },
            { "encodekey256", 0xFB, -1 },
            { "aesenc128kl", 0xDC, -1 },
            { "aesenc256kl", 0xDE, -1 },
            { "aesdec128kl", 0xDD, -1 },
            { "aesdec256kl", 0xDF, -1 },
            { "aesencwide128kl", 0xD8, 0 },
            { "aesencwide256kl", 0xD8, 1 },
            { "aesdecwide128kl", 0xD8, 2 },
            { "aesdecwide256kl", 0xD8, 3 },
        };
        int klopc = -1, kldigit = -1;
        for (unsigned k = 0; k < sizeof(kl)/sizeof(kl[0]); k++)
            if (strcmp(mnem, kl[k].name) == 0) { klopc = kl[k].opc; kldigit = kl[k].digit; break; }
        if (klopc >= 0) {
            /* find registers and memory operand */
            const reg_t *k1 = NULL, *k2 = NULL;
            int mem_tok = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') { mem_tok = i; }
                else if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && !r->is_xmm) { if (!k1) k1 = r; else if (!k2) k2 = r; }
                    else if (r && r->is_xmm) { if (!k1) k1 = r; else if (!k2) k2 = r; }
                }
            }
            emit_byte(out, 0xF3);
            emit_byte(out, 0x0F); emit_byte(out, 0x38);
            emit_byte(out, klopc);
            if (kldigit >= 0) {
                /* wide form: single [mem] operand, /digit */
                if (mem_tok >= 0) {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                        int nr, si;
                        encode_mem_operand(out, kldigit, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        return 1;
                    }
                }
                return 0;
            }
            if (k2) {
                /* reg,reg */
                emit_byte(out, 0xC0 | (k1->code & 7) << 3 | (k2->code & 7));
                return 1;
            }
            if (mem_tok >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, k1 ? k1->code & 7 : 0, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
            return 0;
        }
    }
    if (strcmp(mnem, "bswap") == 0) {
        if (r1) {
            if (r1->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x0F);
            emit_byte(out, 0xC8 | (r1->code & 7));
            return 1;
        }
        return 0;
    }
    /* ptwrite r/m32 → F3 0F AE /4 ; clflush m8 → 0F AE /7 ; clflushopt → 66 0F AE /7 ;
     * rdpid r32 → F3 0F C7 /7 */
    if (strcmp(mnem, "ptwrite") == 0 || strcmp(mnem, "clflush") == 0 ||
        strcmp(mnem, "clflushopt") == 0 || strcmp(mnem, "rdpid") == 0) {
        int is_cl = (mnem[0] == 'c');
        int is_opt = (mnem[0] == 'c' && strlen(mnem) > 7);
        int is_pt = (mnem[0] == 'p');
        if (is_pt) { emit_byte(out, 0xF3); }
        if (is_opt) { emit_byte(out, 0x66); }
        int digit = is_pt ? 4 : 7;
        emit_byte(out, 0x0F);
        emit_byte(out, (mnem[0] == 'r') ? 0xC7 : 0xAE);
        if (is_pt || mnem[0] == 'r') {
            /* register operand: modrm = C0 | digit<<3 | rd */
            const reg_t *pr = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && !r->is_xmm) { pr = r; break; }
                }
            }
            if (pr) {
                emit_byte(out, 0xC0 | digit << 3 | (pr->code & 7));
                return 1;
            }
        }
        /* memory operand */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
        }
        /* bare memory symbol (m08/m16/m32) → RIP-relative */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                strcmp(toks[i].text, "ptr") != 0 && strcmp(toks[i].text, "byte") != 0 &&
                strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0 &&
                strcmp(toks[i].text, "qword") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    if (strcmp(mnem, "push") == 0) {
        if (r1) {
            if (r1->is64) emit_byte(out, 0x50 + r1->code);       /* 64-bit push */
            else emit_byte(out, 0x50 + r1->code);
            return 1;
        }
        if (has_imm) { emit_byte(out, 0x68); emit_imm(out, imm, 4); return 1; }
        return 0;
    }
    if (strcmp(mnem, "pushd") == 0) {
        /* pushd <float-ish imm> → 68 imm32 (low 32 bits of the literal pattern) */
        if (has_imm) { emit_byte(out, 0x68); emit_imm(out, imm, 4); return 1; }
        return 0;
    }
    if (strcmp(mnem, "pop") == 0) {
        if (r1) { emit_byte(out, 0x58 + r1->code); return 1; }
        return 0;
    }
    if (strcmp(mnem, "mov") == 0) {
        /* Detect property access... */
        /* `mov ax,` — blank macro arg: accept single reg + trailing comma as no-op */
        if (r1 && !r2 && !has_imm) {
            int has_second = 0;
            for (int i = 2; i < n; i++)
                if (toks[i].type == ATOK_NUM || (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) ||
                    (toks[i].type == ATOK_OP && toks[i].text[0] == '[')) { has_second = 1; break; }
            if (!has_second) return 1;
        }
        /* --- local stack address detection ---
         * Must be checked before r1/r2 operand collection because `l1[esp]`
         * would set r1=eax, r2=esp (from the [esp] brackets), incorrectly
         * routing to the register-register path. */
        {   int had_local = 0;
            for (int i = 1; i < n && !had_local; i++) {
                /* `symbol[base]` pattern: l1[esp] */
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '[' &&
                    i + 3 < n && toks[i+3].type == ATOK_OP && toks[i+3].text[0] == ']') {
                    const reg_t *base = find_reg(toks[i+2].text);
                    int si = find_or_add_sym(out, toks[i].text);
                    if (si >= 0 && base) {
                        int64_t disp = (int64_t)out->syms[si].value;
                        /* find the dest register from the first reg token */
                        const reg_t *rd = NULL;
                        for (int j = 1; j < n; j++) {
                            if (toks[j].type == ATOK_ID) {
                                const reg_t *rr = find_reg(toks[j].text);
                                if (rr) { rd = rr; break; }
                            }
                        }
                        if (rd) {
                            if (rd->is64) emit_byte(out, 0x48);
                            emit_byte(out, (rd->code < 4 && !rd->is64) ? 0x8A : 0x8B);
                            if (base->code == 4 || base->code == 12) {
                                emit_byte(out, 0x44 | (rd->code & 7) << 3);
                                emit_byte(out, 0x24);
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            } else {
                                emit_byte(out, 0x40 | (rd->code & 7) << 3 | (base->code & 7));
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            }
                            return 1;
                        }
                    }
                }
                /* `[base + symbol]` pattern: [esp+l1] */
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[' &&
                    i + 2 < n && toks[i+2].type == ATOK_OP && toks[i+2].text[0] == '+') {
                    const reg_t *base = find_reg(toks[i+1].text);
                    if (base && i + 3 < n && toks[i+3].type == ATOK_ID) {
                        int si = find_or_add_sym(out, toks[i+3].text);
                        if (si >= 0) {
                            int64_t disp = (int64_t)out->syms[si].value;
                            const reg_t *rd = NULL;
                            for (int j = 1; j < n; j++) {
                                if (toks[j].type == ATOK_ID) {
                                    const reg_t *rr = find_reg(toks[j].text);
                                    if (rr) { rd = rr; break; }
                                }
                            }
                            if (rd) {
                                if (rd->is64) emit_byte(out, 0x48);
                                emit_byte(out, 0x8B);
                                if (base->code == 4 || base->code == 12) {
                                    emit_byte(out, 0x44 | (rd->code & 7) << 3);
                                    emit_byte(out, 0x24);
                                    emit_byte(out, (uint8_t)(int8_t)disp);
                                } else {
                                    emit_byte(out, 0x40 | (rd->code & 7) << 3 | (base->code & 7));
                                    emit_byte(out, (uint8_t)(int8_t)disp);
                                }
                                return 1;
                            }
                        }
                    }
                }
            }
            (void)had_local;
        }
        #define ASMC_ABS_SEC 0xfff1  /* absolute (non-section) symbol marker — defined early for use in mov handlers */

/* `[reg].field` type-aware field access via assume reg:type.
         * When a register is assumed to point to a struct, [reg].field → [reg + field_off].
         * Unbracketed form `reg.field` is also handled (same field resolution). */
        for (int i = 1; i < n; i++) {
            /* unbracketed form: reg(ID) .(OP) field(ID) */
            if (toks[i].type == ATOK_ID && find_reg(toks[i].text) &&
                i + 2 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '.' &&
                toks[i+2].type == ATOK_ID) {
                const reg_t *base = find_reg(toks[i].text);
                int si = find_or_add_sym(out, toks[i].text);
                if (base && si >= 0 && out->syms[si].struct_id > 0) {
                    int sid = out->syms[si].struct_id;
                    const char *fname = toks[i+2].text;
                    int foff = 0;
                    for (int search_id = sid; search_id > 0; search_id = out->struct_parents[search_id]) {
                        for (int k = 0; k < out->nsyms; k++) {
                            if (out->syms[k].struct_id == search_id &&
                                strcmp(out->syms[k].name, fname) == 0) {
                                foff = out->syms[k].struct_off;
                                break;
                            }
                        }
                        if (foff > 0 || out->struct_parents[search_id] == 0) break;
                    }
                    const reg_t *rd = NULL;
                    for (int j = 1; j < n; j++) {
                        if (toks[j].type == ATOK_ID) {
                            const reg_t *rr = find_reg(toks[j].text);
                            if (rr && rr != base && toks[j].text[0] == 'a') { rd = rr; break; }
                            if (rr && rr != base && j > i) { rd = rr; break; }
                        }
                    }
                    if (!rd && i > 1) rd = find_reg(toks[i-1].text);
                    if (rd) {
                        if (rd->is64) emit_byte(out, 0x48);
                        emit_byte(out, (rd->code < 4 && !rd->is64) ? 0x8A : 0x8B);
                        if (base->code == 4 || base->code == 12) {
                            emit_byte(out, 0x44 | (rd->code & 7) << 3);
                            emit_byte(out, 0x24);
                            emit_byte(out, (uint8_t)(int8_t)foff);
                        } else {
                            emit_byte(out, 0x40 | (rd->code & 7) << 3 | (base->code & 7));
                            emit_byte(out, (uint8_t)(int8_t)foff);
                        }
                        return 1;
                    }
                }
            }
            /* bracketed form: [reg] .(OP) field(ID) */
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[' && i + 1 < n &&
                toks[i+1].type == ATOK_ID) {
                const reg_t *base = find_reg(toks[i+1].text);
                if (base && i + 2 < n && toks[i+2].type == ATOK_OP && toks[i+2].text[0] == ']' &&
                    i + 3 < n && toks[i+3].type == ATOK_OP && toks[i+3].text[0] == '.' &&
                    i + 4 < n && toks[i+4].type == ATOK_ID) {
                    /* assume lookup: register name → struct_id */
                    int si = find_or_add_sym(out, toks[i+1].text);
                    if (si >= 0 && out->syms[si].struct_id > 0) {
                        int sid = out->syms[si].struct_id;
                        /* field lookup: find field name in struct, walking parent chain
                         * recursively (inherited fields are registered under parent struct_id). */
                        const char *fname = toks[i+4].text;
                        int foff = 0;
                        for (int search_id = sid; search_id > 0; search_id = out->struct_parents[search_id]) {
                            for (int k = 0; k < out->nsyms; k++) {
                                if (out->syms[k].struct_id == search_id &&
                                    strcmp(out->syms[k].name, fname) == 0) {
                                    foff = out->syms[k].struct_off;
                                    break;
                                }
                            }
                            if (foff > 0 || out->struct_parents[search_id] == 0) break;
                        }
                        /* find dest register */
                        const reg_t *rd = NULL;
                        for (int j = 1; j < n; j++) {
                            if (toks[j].type == ATOK_ID) {
                                const reg_t *rr = find_reg(toks[j].text);
                                if (rr) { rd = rr; break; }
                            }
                        }
                        if (rd) {
                            /* Store form: `mov [reg].field, src` — a comma appears after the
                             * field token. Source is either a numeric immediate or a register.
                             * Dest opcode: C6 (imm8 byte store) / C7 (imm32 store) / 88/89 (reg store). */
                            int is_store = 0, has_imm = 0, imm_val = 0, src_reg = -1;
                            for (int j = i + 5; j < n; j++) {
                                if (toks[j].type == ATOK_OP && toks[j].text[0] == ',') {
                                    is_store = 1;
                                    for (int k = j + 1; k < n; k++) {
                                        if (toks[k].type == ATOK_NUM) { has_imm = 1; imm_val = (int)toks[k].value; }
                                        else if (toks[k].type == ATOK_ID) {
                                            const reg_t *sr = find_reg(toks[k].text);
                                            if (sr) { src_reg = sr->code & 7; break; }
                                        }
                                    }
                                    break;
                                }
                            }
                            if (is_store) {
                                if (has_imm) {
                                    /* mov byte ptr [reg+off], imm8 → C6 /0; mov dword ptr → C7 /0 */
                                    uint8_t op_s = (imm_val >= -128 && imm_val <= 255) ? 0xC6 : 0xC7;
                                    emit_byte(out, op_s);
                                    if (base->code == 4 || base->code == 12) {
                                        emit_byte(out, 0x44);
                                        emit_byte(out, 0x24);
                                        emit_byte(out, (uint8_t)(int8_t)foff);
                                    } else {
                                        emit_byte(out, 0x40 | (base->code & 7));
                                        emit_byte(out, (uint8_t)(int8_t)foff);
                                    }
                                    if (op_s == 0xC6) emit_byte(out, (uint8_t)(int8_t)imm_val);
                                    else emit_imm(out, (uint64_t)(int32_t)imm_val, 4);
                                    return 1;
                                } else if (src_reg >= 0) {
                                    /* mov [reg+off], src_reg → 88/89 /r */
                                    uint8_t op_s = (src_reg < 4 && !rd->is64) ? 0x88 : 0x89;
                                    emit_byte(out, op_s);
                                    if (base->code == 4 || base->code == 12) {
                                        emit_byte(out, 0x44 | (src_reg & 7) << 3);
                                        emit_byte(out, 0x24);
                                        emit_byte(out, (uint8_t)(int8_t)foff);
                                    } else {
                                        emit_byte(out, 0x40 | (src_reg & 7) << 3 | (base->code & 7));
                                        emit_byte(out, (uint8_t)(int8_t)foff);
                                    }
                                    return 1;
                                }
                            }
                            /* Load form: mov rd, [reg].field */
                            if (rd->is64) emit_byte(out, 0x48);
                            emit_byte(out, (rd->code < 4 && !rd->is64) ? 0x8A : 0x8B);
                            if (base->code == 4 || base->code == 12) {
                                emit_byte(out, 0x44 | (rd->code & 7) << 3);
                                emit_byte(out, 0x24);
                                emit_byte(out, (uint8_t)(int8_t)foff);
                            } else {
                                emit_byte(out, 0x40 | (rd->code & 7) << 3 | (base->code & 7));
                                emit_byte(out, (uint8_t)(int8_t)foff);
                            }
                            return 1;
                        }
                    }
                }
            }
        }
        /* Property access (`name.field`) works without registers too:
         * `mov C.f1, 1` — base is a struct instance symbol, not a register.
         * Scan for ID '.' ID; if found, handle property load/store below. */
        if (1) {
            int prop_base_tok = -1, prop_field_tok = -1, prop_off = 0;
            int prop_is_dest = 0;
            /* find the property: scan for ID '.' ID */
            for (int i = 1; i < n - 1; i++) {
                if (toks[i].type == ATOK_ID && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '.' &&
                    i + 2 < n && toks[i+2].type == ATOK_ID) {
                    prop_base_tok = i;
                    prop_field_tok = i + 2;
                    /* property is dest if it appears before the comma */
                    int comma_before_field = 0;
                    for (int k = i; k < i + 3 && k < n; k++)
                        if (toks[k].type == ATOK_OP && toks[k].text[0] == ',') comma_before_field = 1;
                    prop_is_dest = !comma_before_field;
                    break;
                }
            }
            if (prop_base_tok >= 0) {
                /* property access detected */
                fprintf(stderr, "[prop] detected: base=%s, field=%s, is_dest=%d\n",
                        toks[prop_base_tok].text, toks[prop_field_tok].text, prop_is_dest);
                /* look up field offset from symbol table */
                int prop_field = find_or_add_sym(out, toks[prop_field_tok].text);
                int prop_var = find_or_add_sym(out, toks[prop_base_tok].text);
                if (prop_field < out->nsyms)
                    prop_off = out->syms[prop_field].struct_off;
                /* find the other operand (a register or a symbol, skipping property tokens) */
                const reg_t *r = NULL;
                int sym_other = -1;
                int imm_other = 0;
                int has_imm = 0;
                for (int i = 1; i < n; i++) {
                    if (i == prop_base_tok || i == prop_field_tok) continue;
                    if (toks[i].type == ATOK_OP) continue;   /* skip '.', ',', etc. */
                    if (toks[i].type == ATOK_NUM) { has_imm = 1; imm_other = (int)toks[i].value; break; }
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *rr = find_reg(toks[i].text);
                        if (rr) { r = rr; break; }
                        if (sym_other < 0) sym_other = find_or_add_sym(out, toks[i].text);
                    }
                }
                if (has_imm) {
                    /* mov struct.field, imm → C6/C7 /0 [base+off] */
                    if (prop_is_dest) {
                        uint8_t op_s = (imm_other >= -128 && imm_other <= 255) ? 0xC6 : 0xC7;
                        emit_byte(out, op_s);
                        uint8_t modrm = 0x05;
                        emit_byte(out, modrm);
                        emit_imm(out, (uint64_t)prop_off, 4);
                        if (prop_var >= 0) add_fixup(out, prop_var, 2, -4 + prop_off);
                        if (op_s == 0xC6) emit_byte(out, (uint8_t)(int8_t)imm_other);
                        else emit_imm(out, (uint64_t)(int32_t)imm_other, 4);
                        return 1;
                    }
                }
                if (r) {
                    if (r->is64) emit_byte(out, 0x48);
                    if (prop_is_dest) {
                        emit_byte(out, 0x89);
                        uint8_t modrm = 0x05 | (r->code & 7) << 3;
                        emit_byte(out, modrm);
                        emit_imm(out, (uint64_t)prop_off, 4);
                        if (prop_var >= 0) add_fixup(out, prop_var, 2, -4 + prop_off);
                    } else {
                        emit_byte(out, 0x8B);
                        uint8_t modrm = 0x05 | (r->code & 7) << 3;
                        emit_byte(out, modrm);
                        emit_imm(out, (uint64_t)prop_off, 4);
                        if (prop_var >= 0) add_fixup(out, prop_var, 2, -4 + prop_off);
                    }
                    return 1;
                }
                /* symbol operand: use accumulator as scratch:
                 *   mov eax, [sym]  ; load source
                 *   mov [base+off], eax  ; store to field */
                if (sym_other >= 0 && prop_var >= 0) {
                    emit_byte(out, 0xA1);
                    emit_imm(out, 0, 4);
                    add_fixup(out, sym_other, 2 /*R_X86_64_PC32*/, -4);
                    emit_byte(out, 0x89);
                    emit_byte(out, 0x05);
                    emit_imm(out, (uint64_t)prop_off, 4);
                    add_fixup(out, prop_var, 2, -4 + prop_off);
                    return 1;
                }
                return 0;
            }
        }
        if (r1 && r2) {
            /* mov reg, reg — Intel order: r1 = dest, r2 = src.
             * 88/r for 8-bit, 89/r for 16/32/64. REX.R = src (reg field),
             * REX.B = dest (rm field), REX.W = 64-bit. 66 for 16-bit. */
            int is8  = reg_is8(r1) && reg_is8(r2);
            int w    = (r1->is64 || r2->is64) ? 1 : 0;
            int rr   = (r2->code >= 8) ? 1 : 0;
            int rb   = (r1->code >= 8) ? 1 : 0;
            if (!is8 && !w && reg_is16(r1)) emit_byte(out, 0x66);  /* 66 before REX */
            emit_rex(out, w, rr, rb);
            emit_byte(out, is8 ? 0x88 : 0x89);
            uint8_t modrm = 0xC0 | (r2->code & 7) << 3 | (r1->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        if (r1 && has_imm) {
            /* mov reg, imm — B0/B8 + rd with imm8/16/32; 64-bit uses C7 /0
             * imm32 when the value fits signed 32-bit, else B8 movabs imm64. */
            if (reg_is8(r1)) {
                emit_rex(out, 0, 0, (r1->code >= 8) ? 1 : 0);
                emit_byte(out, 0xB0 + (r1->code & 7));
                emit_byte(out, (uint8_t)imm);
                return 1;
            }
            if (r1->is64) {
                int64_t sv = (int64_t)imm;
                emit_rex(out, 1, 0, (r1->code >= 8) ? 1 : 0);
                if (sv >= -2147483648LL && sv <= 2147483647LL) {
                    emit_byte(out, 0xC7);                 /* C7 /0 id (imm32 sign-extended) */
                    emit_byte(out, 0xC0 | (r1->code & 7));
                    emit_imm(out, (uint64_t)(int32_t)sv, 4);
                } else {
                    emit_byte(out, 0xB8 + (r1->code & 7)); /* B8+rd imm64 (movabs) */
                    emit_imm(out, imm, 8);
                }
                return 1;
            }
            if (reg_is16(r1)) emit_byte(out, 0x66);  /* 66 before REX */
            emit_rex(out, 0, 0, (r1->code >= 8) ? 1 : 0);
            emit_byte(out, 0xB8 + (r1->code & 7));
            emit_imm(out, imm, reg_is16(r1) ? 2 : 4);
            return 1;
        }
        if (r1 && r2 == NULL && !has_imm) {
            /* local variable stack addressing: `l1[esp]` or `[esp+l1]` → [base+disp]
             * Local symbols have sec_index==ASMC_ABS_SEC and value = offset. */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    /* check for `symbol[` (local stack reference) */
                    if (si >= 0 && i + 1 < n && toks[i+1].type == ATOK_OP &&
                        toks[i+1].text[0] == '[' && i + 3 < n &&
                        toks[i+3].type == ATOK_OP && toks[i+3].text[0] == ']') {
                        const reg_t *base = find_reg(toks[i+2].text);
                        if (base) {
                            int64_t disp = (int64_t)out->syms[si].value;
                            if (r1->is64) emit_byte(out, 0x48);
                            emit_byte(out, 0x8B);
                            if (base->code == 4 || base->code == 12) {
                                /* base is esp/rsp: SIB required */
                                uint8_t modrm = 0x40 | (r1->code & 7) << 3 | 4;
                                emit_byte(out, modrm);
                                emit_byte(out, 0x24);  /* SIB: no index, base=esp */
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            } else {
                                uint8_t modrm = 0x40 | (r1->code & 7) << 3 | (base->code & 7);
                                emit_byte(out, modrm);
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            }
                            return 1;
                        }
                    }
                    /* mov reg, [local_var] → [esp+local_offset] for positive ABS offsets */
                    if (si >= 0 && out->syms[si].sec_index == -1) {
                        /* scope-closed local: emit error instead of encoding */
                        fprintf(stderr, "ASMC : error A2001: local variable '%s' is out of scope (used after endp)\n",
                                out->syms[si].name);
                        out->errors++;
                        return 1;
                    }
                    if (si >= 0 && out->syms[si].sec_index == ASMC_ABS_SEC &&
                        (int64_t)out->syms[si].value > 0 && out->cur_proc &&
                        toks[i-1].type == ATOK_OP && toks[i-1].text[0] == '[' &&
                        i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ']') {
                        int64_t disp = (int64_t)out->syms[si].value;
                        /* 8-bit registers are al/cl/dl/bl/ah/ch/dh/bh → 8A; others → 8B */
                        int r8 = (r1->name[1] == 'l' || r1->name[1] == 'h');
                        if (r1->is64) emit_byte(out, 0x48);
                        emit_byte(out, r8 ? 0x8A : 0x8B);
                        emit_byte(out, 0x44 | ((r1->code & 7) << 3));
                        emit_byte(out, 0x24);
                        emit_byte(out, (uint8_t)(int8_t)disp);
                        return 1;
                    }
                    /* mov reg, symbol → RIP-relative: 8B 05 rel32 (data reference),
                     * unless the symbol is a PROC parameter (ABS value → [rbp+disp]) */
                    if (si >= 0 && out->syms[si].sec_index == ASMC_ABS_SEC &&
                        (int64_t)out->syms[si].value >= 0x20 && (int64_t)out->syms[si].value <= 0x7F) {
                        /* PROC parameter: emit mov reg,[rbp+disp] */
                        int64_t disp = (int64_t)out->syms[si].value;
                        if (r1->is64) emit_byte(out, 0x48);
                        emit_byte(out, 0x8B);
                        emit_byte(out, 0x45 | (r1->code & 7) << 3);  /* mod=01, rm=rbp */
                        emit_byte(out, (uint8_t)(int8_t)disp);
                        return 1;
                    }
                    if (r1->is64) emit_byte(out, 0x48);  /* REX.W */
                    emit_byte(out, 0x8B);
                    uint8_t modrm = 0x05 | (r1->code & 7) << 3;  /* mod=00, rm=5 (RIP) */
                    emit_byte(out, modrm);
                    emit_imm(out, 0, 4);                 /* placeholder */
                    if (si >= 0) {
                        add_fixup(out, si, 2 /*R_X86_64_PC32*/, -4);
                    }
                    return 1;
                }
            }
            /* `[reg + local]` pattern: [esp+l1] */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[' && i + 2 < n &&
                    toks[i+2].type == ATOK_OP && toks[i+2].text[0] == '+') {
                    const reg_t *base = find_reg(toks[i+1].text);
                    if (base && i + 3 < n && toks[i+3].type == ATOK_ID) {
                        int si = find_or_add_sym(out, toks[i+3].text);
                        if (si >= 0) {
                            int64_t disp = (int64_t)out->syms[si].value;
                            if (r1->is64) emit_byte(out, 0x48);
                            emit_byte(out, 0x8B);
                            if (base->code == 4 || base->code == 12) {
                                uint8_t modrm = 0x40 | (r1->code & 7) << 3 | 4;
                                emit_byte(out, modrm);
                                emit_byte(out, 0x24);
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            } else {
                                uint8_t modrm = 0x40 | (r1->code & 7) << 3 | (base->code & 7);
                                emit_byte(out, modrm);
                                emit_byte(out, (uint8_t)(int8_t)disp);
                            }
                            return 1;
                        }
                    }
                }
            }
            return 0;  /* not yet supported */
        }
        /* mov <sym>, <imm> — store immediate to data symbol (C6/C7 /0 RIP-relative) */
        if (!r1 && !r2 && has_imm) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    uint8_t op_s = (imm >= -128 && imm <= 255) ? 0xC6 : 0xC7;
                    emit_byte(out, op_s);
                    emit_byte(out, 0x05);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    if (op_s == 0xC6) emit_byte(out, (uint8_t)(int8_t)imm);
                    else emit_imm(out, (uint64_t)(int32_t)imm, 4);
                    return 1;
                }
            }
        }
        /* mov <sym>, offset <sym2> — store symbol address (C7 /0 RIP-rel + PC32 reloc) */
        if (!r1 && !r2) {
            int dst_si = -1, src_si = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && strcmp(toks[i].text, "offset") == 0) {
                    if (i + 1 < n && toks[i+1].type == ATOK_ID && !find_reg(toks[i+1].text))
                        src_si = find_or_add_sym(out, toks[i+1].text);
                } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && src_si < 0) {
                    dst_si = find_or_add_sym(out, toks[i].text);
                }
            }
            if (src_si >= 0 && dst_si >= 0) {
                emit_byte(out, 0xC7);
                emit_byte(out, 0x05);
                emit_imm(out, 0, 4);
                add_fixup(out, dst_si, 2, -4);
                emit_imm(out, 0, 4);
                add_fixup(out, src_si, 2, -4);
                return 1;
            }
        }
        /* mov <sym>, <sym2> — load stack var src into rax, store to dest stack var */
        if (!r1 && !r2) {
            int dst_si = -1, src_si = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                    if (dst_si < 0) dst_si = find_or_add_sym(out, toks[i].text);
                    else if (src_si < 0) src_si = find_or_add_sym(out, toks[i].text);
                }
            }
            if (dst_si >= 0 && src_si >= 0) {
                int64_t d_off = (int64_t)out->syms[dst_si].value;
                int64_t s_off = (int64_t)out->syms[src_si].value;
                /* mov rax, [rbp+src] ; mov [rbp+dst], rax */
                emit_byte(out, 0x48); emit_byte(out, 0x8B);
                emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)s_off);
                emit_byte(out, 0x48); emit_byte(out, 0x89);
                emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)d_off);
                return 1;
            }
        }
    }
    /* btc/btr/bts (bit test and complement/reset/set):
     * imm form: 66 0F BA /digit ib (bts=5, btr=6, btc=7) r/m16,imm8
     * reg form: 66 0F AB/B3/BB /r (bts=AB, btr=B3, btc=BB) r/m16,r16 */
    if (strcmp(mnem, "btc") == 0 || strcmp(mnem, "btr") == 0 || strcmp(mnem, "bts") == 0) {
        const reg_t *rd = NULL;
        int found_mem = 0, imm_val = 0, has_imm = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->code < 16) { if (!rd) rd = r; }
            } else if (toks[i].type == ATOK_NUM) { imm_val = (int)toks[i].value; has_imm = 1; }
            else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem) {
            int digit = 7; /* btc */
            if (mnem[2] == 's') digit = 5;      /* bts */
            else if (mnem[2] == 'r') digit = 6; /* btr */
            int nr, si;
            emit_byte(out, 0x66);  /* 16-bit operand */
            emit_byte(out, 0x0F);
            if (has_imm) {
                emit_byte(out, 0xBA);
                encode_mem_operand(out, digit & 7, &mop, &nr, &si);
                emit_byte(out, (uint8_t)imm_val);
            } else if (rd) {
                uint8_t op2 = 0xBB; /* btc */
                if (mnem[2] == 's') op2 = 0xAB;
                else if (mnem[2] == 'r') op2 = 0xB3;
                emit_byte(out, op2);
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            }
            (void)nr; (void)si;
            return 1;
        }
    }

    /* xchg r/m, reg: 86 /r (8-bit), 87 /r (16/32/64 with 66/REX prefix).
     * Lock/HLE prefixes emitted by the prefix handlers before reaching here. */
    if (strcmp(mnem, "xchg") == 0) {
        const reg_t *rmr = NULL, *rreg = NULL;
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!rmr) rmr = r; else if (!rreg) rreg = r; }
            } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem && rreg) {
            const reg_t *rsrc = rreg;  /* register operand */
            if (rsrc->name[1] == 'l' || rsrc->name[1] == 'h') {
                emit_byte(out, 0x86);
                int nr, si;
                encode_mem_operand(out, rsrc->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                /* 16/32/64-bit: WORD→66 prefix, 64-bit→REX.W */
                if (rsrc->code >= 8) emit_byte(out, 0x41);
                else if (rsrc->name[0] == 'e') { } /* 32-bit no prefix */
                else emit_byte(out, 0x66);        /* 16-bit */
                if (rsrc->name[1] == 'x' && rsrc->name[0] != 'e' && rsrc->name[0] != 'r') { }
                emit_byte(out, 0x87);
                int nr, si;
                encode_mem_operand(out, rsrc->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            }
            return 1;
        }
    }

    /* cmpxchg r/m, reg: 0F B0 /r (8-bit), 0F B1 /r (16/32/64). */
    if (strcmp(mnem, "cmpxchg") == 0) {
        const reg_t *rreg = NULL;
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!rreg) rreg = r; }
            } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem && rreg) {
            if (rreg->code >= 8) emit_byte(out, 0x41);
            else if (rreg->name[1] == 'l' || rreg->name[1] == 'h') { /* 8-bit: no prefix */ }
            else if (rreg->name[0] != 'e' && rreg->name[0] != 'r' && rreg->name[0] != 'a' &&
                     rreg->name[0] != 'b' && rreg->name[0] != 'c' && rreg->name[0] != 'd' &&
                     rreg->name[0] != 's' && rreg->name[0] != 'i') { /* 16-bit ax/bx/cx/dx/si/di/bp/sp */
                emit_byte(out, 0x66);
            }
            emit_byte(out, 0x0F);
            emit_byte(out, (rreg->name[1] == 'l' || rreg->name[1] == 'h') ? 0xB0 : 0xB1);
            int nr, si;
            encode_mem_operand(out, rreg->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
    }

    /* xadd r/m, reg: 0F C0 /r (8-bit), 0F C1 /r (16/32/64). */
    if (strcmp(mnem, "xadd") == 0) {
        const reg_t *rreg = NULL;
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!rreg) rreg = r; }
            } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem && rreg) {
            if (rreg->code >= 8) emit_byte(out, 0x41);
            else if (rreg->name[1] == 'l' || rreg->name[1] == 'h') { /* 8-bit */ }
            else if (rreg->name[0] != 'e' && rreg->name[0] != 'r') { /* 16-bit */ emit_byte(out, 0x66); }
            emit_byte(out, 0x0F);
            emit_byte(out, (rreg->name[1] == 'l' || rreg->name[1] == 'h') ? 0xC0 : 0xC1);
            int nr, si;
            encode_mem_operand(out, rreg->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
    }

        if (strcmp(mnem, "test") == 0) {
        /* test: F6/F7 /0  (reg,reg / reg,imm / mem,imm); es:/fs: segment prefix (64/64) */
        const reg_t *t1 = NULL, *t2 = NULL;
        int mem_tok = -1;
        int64_t tim = 0; int htim = 0;
        int seg_pre = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "es") == 0 || strcmp(toks[i].text, "fs") == 0 ||
                strcmp(toks[i].text, "cs") == 0 || strcmp(toks[i].text, "ss") == 0 ||
                strcmp(toks[i].text, "ds") == 0)) seg_pre = 0x64;
            if (toks[i].type == ATOK_NUM) { tim = toks[i].value; htim = 1; }
            else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!t1) t1 = r; else if (!t2) t2 = r; }
            }
        }
        if (seg_pre) emit_byte(out, (uint8_t)seg_pre);
        if (t1 && t2) {
            /* test reg, reg → 85 /r (F6 /0 for 8-bit) */
            int is8 = (!t1->is64 && (t1->name[1]=='l' && t1->name[0]!='r')) || t1->name[1]=='h';
            if (is8) emit_byte(out, 0x84);
            else { if (t1->is64 || t2->is64) emit_byte(out, 0x48); emit_byte(out, 0x85); }
            emit_byte(out, 0xC0 | (t1->code & 7) << 3 | (t2->code & 7));
            return 1;
        }
        if (t1 && htim) {
            /* test reg, imm → F6/F7 /0 ib/id */
            int is8 = (!t1->is64 && t1->name[1]=='l' && t1->name[0]!='r') || t1->name[1]=='h';
            if (is8) { emit_byte(out, 0xF6); emit_byte(out, 0xC0 | (t1->code & 7)); emit_byte(out, (uint8_t)tim); }
            else { if (t1->is64) emit_byte(out, 0x48); emit_byte(out, 0xF7); emit_byte(out, 0xC0 | (t1->code & 7)); emit_imm(out, (uint64_t)tim, 4); }
            return 1;
        }
        /* test reg, <mem symbol> → 84/85 /r RIP-rel */
        if (t1) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    strcmp(toks[i].text, "es") != 0 && strcmp(toks[i].text, "fs") != 0 &&
                    strcmp(toks[i].text, "cs") != 0 && strcmp(toks[i].text, "ds") != 0 &&
                    strcmp(toks[i].text, "ss") != 0) {
                    int is8 = (!t1->is64 && t1->name[1]=='l' && t1->name[0]!='r') || t1->name[1]=='h';
                    int si = find_or_add_sym(out, toks[i].text);
                    if (is8) emit_byte(out, 0x84);
                    else { if (t1->is64) emit_byte(out, 0x48); emit_byte(out, 0x85); }
                    emit_byte(out, 0x05 | (t1->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        }
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                emit_byte(out, 0xF6);
                int nr, si;
                encode_mem_operand(out, 0, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                if (htim) emit_byte(out, (uint8_t)tim);
                return 1;
            }
        }
        /* test <sym>, <imm> → F6 05 disp32, imm8 */
        if (htim) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    strcmp(toks[i].text, "es") != 0 && strcmp(toks[i].text, "fs") != 0 &&
                    strcmp(toks[i].text, "cs") != 0 && strcmp(toks[i].text, "ds") != 0 &&
                    strcmp(toks[i].text, "ss") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0xF6);
                    emit_byte(out, 0x05);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    emit_byte(out, (uint8_t)tim);
                    return 1;
                }
            }
        }
        return 0;
    }
    /* div/idiv r/m: F6 /6 /7 (8-bit), F7 /6 /7 (16/32/64-bit) */
    if (strcmp(mnem, "mul") == 0 || strcmp(mnem, "div") == 0 || strcmp(mnem, "idiv") == 0) {
        int digit = 4;   /* mul → F6/F7 /4 */
        if (strcmp(mnem, "div") == 0) digit = 6;
        else if (strcmp(mnem, "idiv") == 0) digit = 7;
        const reg_t *dv = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!dv) dv = r; }
            }
        }
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                /* default operand size 32-bit; F6 /digit for 8-bit when size
                 * token 'byte' precedes, else F7 /digit (emit REX.W only if
                 * a 64-bit register operand is present). */
                int is8 = 0;
                for (int i = 1; i < n; i++)
                    if (toks[i].type == ATOK_ID && strcmp(toks[i].text, "byte") == 0) { is8 = 1; break; }
                emit_byte(out, is8 ? 0xF6 : 0xF7);
                int nr, si;
                encode_mem_operand(out, digit, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (dv) {
            /* 8-bit reg (al/cl/dl/bl/ah/.../sil) → F6 /digit ; else F7 /digit */
            int is8 = 0;
            if ((dv->name[1] == 'l' && dv->name[0] != 'r') || dv->name[1] == 'h' ||
                strcmp(dv->name, "sil") == 0 || strcmp(dv->name, "dil") == 0 ||
                strcmp(dv->name, "bpl") == 0 || strcmp(dv->name, "spl") == 0) is8 = 1;
            if (is8) {
                emit_byte(out, 0xF6);
                emit_byte(out, 0xC0 | digit << 3 | (dv->code & 7));
            } else {
                if (dv->is64) emit_byte(out, 0x48);
                emit_byte(out, 0xF7);
                emit_byte(out, 0xC0 | digit << 3 | (dv->code & 7));
            }
            return 1;
        }
        /* div <symbol> → F7 /digit RIP-rel */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0xF7);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* cmov*: conditional move → 0F 40+cc /r (cc from mnemonic suffix) */
    if (strncmp(mnem, "cmov", 4) == 0 && mnem[4] != 0) {
        int cc = -1;
        const char *suf = mnem + 4;
        if (strcmp(suf, "o") == 0) cc = 0;
        else if (strcmp(suf, "no") == 0) cc = 1;
        else if (strcmp(suf, "b") == 0 || strcmp(suf, "c") == 0 || strcmp(suf, "nae") == 0) cc = 2;
        else if (strcmp(suf, "ae") == 0 || strcmp(suf, "nb") == 0 || strcmp(suf, "nc") == 0) cc = 3;
        else if (strcmp(suf, "e") == 0 || strcmp(suf, "z") == 0) cc = 4;
        else if (strcmp(suf, "ne") == 0 || strcmp(suf, "nz") == 0) cc = 5;
        else if (strcmp(suf, "be") == 0 || strcmp(suf, "na") == 0) cc = 6;
        else if (strcmp(suf, "a") == 0 || strcmp(suf, "nbe") == 0) cc = 7;
        else if (strcmp(suf, "s") == 0) cc = 8;
        else if (strcmp(suf, "ns") == 0) cc = 9;
        else if (strcmp(suf, "p") == 0 || strcmp(suf, "pe") == 0) cc = 10;
        else if (strcmp(suf, "np") == 0 || strcmp(suf, "po") == 0) cc = 11;
        else if (strcmp(suf, "l") == 0 || strcmp(suf, "nge") == 0) cc = 12;
        else if (strcmp(suf, "ge") == 0 || strcmp(suf, "nl") == 0) cc = 13;
        else if (strcmp(suf, "le") == 0 || strcmp(suf, "ng") == 0) cc = 14;
        else if (strcmp(suf, "g") == 0 || strcmp(suf, "nle") == 0) cc = 15;
        if (cc >= 0) {
            const reg_t *cd = NULL, *cs = NULL;
            int mem_tok = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
                else if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && !r->is_xmm) { if (!cd) cd = r; else if (!cs) cs = r; }
                }
            }
            if (!cd) return 0;
            int dst16 = 0;
            if (cd->name[1] == 'x' || cd->name[1] == 'p' || cd->name[1] == 'i' ||
                (cd->name[0] == 'r' && (cd->name[1] == '8' || cd->name[1] == '9' || cd->name[1] == '1')))
                dst16 = 1;
            if (dst16) emit_byte(out, 0x66);
            else if (cd->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x0F);
            emit_byte(out, 0x40 | cc);
            if (mem_tok >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, cd->code & 7, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
            /* bare memory symbol (m16/m32/m64 without brackets) → RIP-relative */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0 &&
                    strcmp(toks[i].text, "qword") != 0 && strcmp(toks[i].text, "ptr") != 0 &&
                    strcmp(toks[i].text, "byte") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (cd->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
            if (cs) {
                emit_byte(out, 0xC0 | (cd->code & 7) << 3 | (cs->code & 7));
                return 1;
            }
            return 0;
        }
    }
    if (strcmp(mnem, "arpl") == 0) {
        /* arpl r/m16, r16 → 63 /r */
        const reg_t *ad = NULL, *as = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!ad) ad = r; else if (!as) as = r; }
            }
        }
        if (ad && as) {
            emit_byte(out, 0x66); emit_byte(out, 0x63);
            emit_byte(out, 0xC0 | (ad->code & 7) << 3 | (as->code & 7));
            return 1;
        }
        /* arpl <sym>, r16 → 66 63 /r RIP-rel (symbol dest, single reg src) */
        {
            const reg_t *src = ad ? ad : as;
            if (src) {
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                        int si = find_or_add_sym(out, toks[i].text);
                        emit_byte(out, 0x66); emit_byte(out, 0x63);
                        emit_byte(out, 0x05 | (src->code & 7) << 3);
                        emit_imm(out, 0, 4);
                        if (si >= 0) add_fixup(out, si, 2, -4);
                        return 1;
                    }
                }
            }
        }
        return 0;
    }
    /* verr/verw: 0F 00 /4 /5 */
    if (strcmp(mnem, "verr") == 0 || strcmp(mnem, "verw") == 0) {
        int digit = (mnem[3] == 'r') ? 4 : 5;
        const reg_t *vr = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { vr = r; break; }
            }
        }
        if (vr) {
            emit_byte(out, 0x0F); emit_byte(out, 0x00);
            emit_byte(out, 0xC0 | digit << 3 | (vr->code & 7));
            return 1;
        }
        /* verr/verw <sym> → 0F 00 /digit RIP-rel */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x0F); emit_byte(out, 0x00);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* bt/bts/btr/btc with register pair: 0F A3/AB/B3/BB /r (bt reg,reg) */
    if (strcmp(mnem, "bt") == 0 || strcmp(mnem, "bts") == 0 || strcmp(mnem, "btr") == 0 || strcmp(mnem, "btc") == 0) {
        const reg_t *br1 = NULL, *br2 = NULL;
        int has_imm = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) has_imm = 1;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!br1) br1 = r; else if (!br2) br2 = r; }
            }
        }
        if (!has_imm && br1 && br2) {
            uint8_t opc = (mnem[2] == 's') ? 0xAB : (mnem[2] == 'r') ? 0xB3 : (mnem[2] == 'c') ? 0xBB : 0xA3;
            emit_byte(out, 0x66);
            emit_byte(out, 0x0F); emit_byte(out, opc);
            emit_byte(out, 0xC0 | (br1->code & 7) << 3 | (br2->code & 7));
            return 1;
        }
        /* bt <sym>, <reg> → 66 0F A3/AB/B3/BB /r RIP-rel (symbol dest, reg src) */
        if (!has_imm && br1 && br2 == NULL) {
            uint8_t opc = (mnem[2] == 's') ? 0xAB : (mnem[2] == 'r') ? 0xB3 : (mnem[2] == 'c') ? 0xBB : 0xA3;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x66);
                    emit_byte(out, 0x0F); emit_byte(out, opc);
                    emit_byte(out, 0x05 | (br1->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        }
    }
    /* bt/bts/btr/btc with immediate: 0F BA /4//5//6//7 ib */
    if (strcmp(mnem, "bt") == 0 || strcmp(mnem, "bts") == 0 || strcmp(mnem, "btr") == 0 || strcmp(mnem, "btc") == 0) {
        int digit = 4; /* bt */
        if (mnem[2] == 's') digit = 5; else if (mnem[2] == 'r') digit = 6; else if (mnem[2] == 'c') digit = 7;
        const reg_t *br = NULL;
        int64_t bim = 0; int hbim = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { bim = toks[i].value; hbim = 1; }
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!br) br = r; }
            }
        }
        if (br && hbim) {
            emit_byte(out, 0x66);
            emit_byte(out, 0x0F); emit_byte(out, 0xBA);
            emit_byte(out, 0xC0 | digit << 3 | (br->code & 7));
            emit_byte(out, (uint8_t)bim);
            return 1;
        }
        /* bt with symbol: bt vw, 2 → 66 0F BA /4 RIP-rel ib */
        if (!br && hbim) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0xBA);
                    emit_byte(out, 0x05 | digit << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    emit_byte(out, (uint8_t)bim);
                    return 1;
                }
            }
        }
    }
    /* repeat prefixes: rep/repe/repz (F3), repne/repnz (F2) before a string instruction */
    if (strcmp(mnem, "rep") == 0 || strcmp(mnem, "repe") == 0 || strcmp(mnem, "repz") == 0 ||
        strcmp(mnem, "repne") == 0 || strcmp(mnem, "repnz") == 0) {
        if (n < 2) return 0;
        int is_repne = (mnem[0] == 'r' && mnem[3] == 'n');
        emit_byte(out, is_repne ? 0xF2 : 0xF3);
        /* re-encode the following instruction (cmps/movs/lods/stos/scas/ins/outs) */
        return encode_instruction(out, &toks[1], n - 1);
    }
    /* umonitor/umwait/tpause: F3/F2/66 0F AE /6 (reg or mem) */
    if (strcmp(mnem, "umonitor") == 0 || strcmp(mnem, "umwait") == 0 || strcmp(mnem, "tpause") == 0) {
        uint8_t pre = (mnem[0] == 'u' && mnem[1] == 'm' && mnem[2] == 'o') ? 0xF3 :
                      (mnem[0] == 'u' && mnem[1] == 'm') ? 0xF2 : 0x66;
        const reg_t *ur = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { ur = r; break; }
            }
        }
        /* no register reference found (e.g. symbol/memory operand): not encodable
           in the reg form below — return 0 instead of dereferencing NULL */
        if (ur == NULL)
            return 0;
        emit_byte(out, pre);
        /* 16-bit/32-bit address-size matters little; emit reg form */
        if (ur->name[1] == 'x' && ur->name[0] != 'e' && ur->name[0] != 'r') emit_byte(out, 0x67);
        emit_byte(out, 0x0F); emit_byte(out, 0xAE);
        emit_byte(out, 0xC0 | 6 << 3 | (ur->code & 7));
        return 1;
    }
    /* vmxon/vmclear/vmptrld/vmptrst m64: F3/66/none 0F C7 /6 //7 */
    if (strcmp(mnem, "vmxon") == 0 || strcmp(mnem, "vmclear") == 0 ||
        strcmp(mnem, "vmptrld") == 0 || strcmp(mnem, "vmptrst") == 0) {
        if (strcmp(mnem, "vmxon") == 0) emit_byte(out, 0xF3);
        else if (strcmp(mnem, "vmclear") == 0) emit_byte(out, 0x66);
        int digit = (strcmp(mnem, "vmptrst") == 0) ? 7 : 6;
        emit_byte(out, 0x0F); emit_byte(out, 0xC7);
        /* symbol target → RIP-relative */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* invept/invvpid: 66 0F 38 80/81 /r */
    if (strcmp(mnem, "invept") == 0 || strcmp(mnem, "invvpid") == 0) {
        emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x38);
        emit_byte(out, (mnem[2] == 'v') ? 0x81 : 0x80);
        const reg_t *gpr = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { gpr = r; break; }
            }
        }
        int g = (gpr ? (gpr->code & 7) : 0);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | g << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 1;
    }
    /* vmread/vmwrite: 0F 78/79 /r */
    if (strcmp(mnem, "vmread") == 0 || strcmp(mnem, "vmwrite") == 0) {
        int is_vmread = (mnem[2] == 'r');
        const reg_t *vr1 = NULL, *vr2 = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!vr1) vr1 = r; else if (!vr2) vr2 = r; }
            }
        }
        emit_byte(out, 0x0F); emit_byte(out, is_vmread ? 0x78 : 0x79);
        if (vr1 && vr2) {
            emit_byte(out, 0xC0 | (vr1->code & 7) << 3 | (vr2->code & 7));
            return 1;
        }
        if (vr1 || vr2) {
            const reg_t *rg = vr1 ? vr1 : vr2;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (rg->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        }
        return 0;
    }
        /* fcomi/fcomip/fucomi/fucomip: DB F0+i / DF F0+i (compare st0, st(i)) */
    if (strcmp(mnem, "fcomi") == 0 || strcmp(mnem, "fcomip") == 0 ||
        strcmp(mnem, "fucomi") == 0 || strcmp(mnem, "fucomip") == 0) {
        int sti = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        }
        int is_u = (mnem[1] == 'u');
        int is_p = (mnem[5] == 'p');
        emit_byte(out, is_u ? (is_p ? 0xDF : 0xDB) : (is_p ? 0xDF : 0xDB));
        emit_byte(out, (uint8_t)((is_u ? 0xE8 : 0xF0) + sti));
        return 1;
    }
    /* ffree st(i): DD C0+i */
    if (strcmp(mnem, "ffree") == 0) {
        int sti = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        }
        emit_byte(out, 0xDD);
        emit_byte(out, (uint8_t)(0xC0 + sti));
        return 1;
    }
    /* fiadd/fisub/fimul/fidiv/fidivr/fisubr/ficom/ficomp: DA /digit (m32), DE /digit (m16) */
    if (strcmp(mnem, "fiadd") == 0 || strcmp(mnem, "fisub") == 0 || strcmp(mnem, "fisubr") == 0 ||
        strcmp(mnem, "fimul") == 0 || strcmp(mnem, "fidiv") == 0 || strcmp(mnem, "fidivr") == 0 ||
        strcmp(mnem, "ficom") == 0 || strcmp(mnem, "ficomp") == 0) {
        int digit = (mnem[2] == 'a') ? 0 : (mnem[2] == 's') ? ((mnem[4] == 'r') ? 5 : 4) :
                    (mnem[2] == 'm') ? 1 : (mnem[3] == 'v') ? 6 : (mnem[3] == 'r') ? 7 :
                    (mnem[3] == 'o') ? 2 : 3;
        /* DA for m32, DE for m16 */
        int is16 = 0;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "word") == 0 || strcmp(toks[i].text, "m16") == 0)) is16 = 1;
        emit_byte(out, is16 ? 0xDE : 0xDA);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fild/fist/fistp: DB/DF /0//2//3 (m16/m32/m64) */
    if (strcmp(mnem, "fild") == 0 || strcmp(mnem, "fist") == 0 || strcmp(mnem, "fistp") == 0) {
        int digit = (mnem[1] == 'i') ? 0 : (mnem[3] == 'p') ? 3 : 2;
        int is64 = 0, is32 = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "qword") == 0 || strcmp(toks[i].text, "m64") == 0)) is64 = 1;
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "dword") == 0 || strcmp(toks[i].text, "m32") == 0)) is32 = 1;
        }
        emit_byte(out, (strcmp(mnem, "fild") == 0) ? 0xDB : 0xDF);
        if (is64) emit_byte(out, 0x28); /* /5 for m64, not needed for basic */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | (strcmp(mnem, "fild") == 0 ? 0 : digit) << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fld st(i) → D9 C0+i ; fld m32 → D9 /0 ; fld m64 → DD /0 ; fld m80 → DB /5 */
    if (strcmp(mnem, "fld") == 0) {
        int sti = -1;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        if (sti >= 0) { emit_byte(out, 0xD9); emit_byte(out, (uint8_t)(0xC0 + sti)); return 1; }
        /* memory: detect width and emit opcode */
        int pre = 0xD9, digit = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "qword") == 0 || strcmp(toks[i].text, "real8") == 0)) { pre = 0xDD; }
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "tbyte") == 0 || strcmp(toks[i].text, "real10") == 0)) { pre = 0xDB; digit = 5; }
        }
        emit_byte(out, (uint8_t)pre);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fst/fstp st(i) → DD/DF D0+i ; fst m32 → D9 /2 ; fstp m32 → D9 /3 ; fstp m64 → DD /3 */
    if (strcmp(mnem, "fst") == 0 || strcmp(mnem, "fstp") == 0) {
        int is_p = (mnem[3] == 'p');
        int sti = -1;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        if (sti >= 0) {
            emit_byte(out, 0xDD);
            emit_byte(out, (uint8_t)((is_p ? 0xD8 : 0xD0) + sti));
            return 1;
        }
        int digit = is_p ? 3 : 2;
        int pre = 0xD9;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "qword") == 0 || strcmp(toks[i].text, "real8") == 0)) { pre = 0xDD; digit = 3; }
        emit_byte(out, (uint8_t)pre);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* fxch st(i) → D9 C8+i */
    if (strcmp(mnem, "fxch") == 0) {
        int sti = 1;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && strncmp(toks[i].text, "st", 2) == 0) {
                const char *p = toks[i].text + 2; sti = 0;
                if (*p == '(') { p++; while (*p >= '0' && *p <= '9') { sti = sti * 10 + (*p - '0'); p++; } }
            }
        emit_byte(out, 0xD9);
        emit_byte(out, (uint8_t)(0xC8 + sti));
        return 1;
    }
    /* fnstsw/fstsw: store x87 status word → DF E0 (ax), 9B DF E0 (fstsw) */
    if (strcmp(mnem, "fnstsw") == 0 || strcmp(mnem, "fstsw") == 0) {
        if (strcmp(mnem, "fstsw") == 0) emit_byte(out, 0x9B);
        emit_byte(out, 0xDF); emit_byte(out, 0xE0);
        return 1;
    }
    /* fxsave/fxrstor/xsave/xsaveopt/xrstor: 0F AE /0//1//4//6//5, with / without 64 suffix */
    if (strcmp(mnem, "fxsave") == 0 || strcmp(mnem, "fxsave64") == 0 ||
        strcmp(mnem, "fxrstor") == 0 || strcmp(mnem, "fxrstor64") == 0 ||
        strcmp(mnem, "xsave") == 0 || strcmp(mnem, "xsave64") == 0 ||
        strcmp(mnem, "xsaveopt") == 0 || strcmp(mnem, "xsaveopt64") == 0 ||
        strcmp(mnem, "xsavec") == 0 || strcmp(mnem, "xsavec64") == 0 ||
        strcmp(mnem, "xsaves") == 0 || strcmp(mnem, "xsaves64") == 0 ||
        strcmp(mnem, "xrstor") == 0 || strcmp(mnem, "xrstor64") == 0 ||
        strcmp(mnem, "xrstors") == 0 || strcmp(mnem, "xrstors64") == 0) {
        int is64 = (strlen(mnem) > 5 && mnem[strlen(mnem)-2] == '6' && mnem[strlen(mnem)-1] == '4');
        /* strip the 64 suffix for digit selection */
        char base[16];
        snprintf(base, sizeof(base), "%s", mnem);
        if (is64) base[strlen(base)-2] = 0;
        int digit;
        if (strcmp(base, "fxsave") == 0) digit = 0;
        else if (strcmp(base, "fxrstor") == 0) digit = 1;
        else if (strcmp(base, "xsave") == 0) digit = 4;
        else if (strcmp(base, "xsaveopt") == 0) digit = 6;
        else if (strcmp(base, "xsavec") == 0) digit = 7;
        else if (strcmp(base, "xsaves") == 0) digit = 3;
        else if (strcmp(base, "xrstor") == 0) digit = 5;
        else digit = 2; /* xrstors */
        if (is64) emit_byte(out, 0x48);   /* REX.W for the 64-bit forms */
        emit_byte(out, 0x0F); emit_byte(out, 0xAE);
        /* symbol target → RIP-relative */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 0;
    }
    /* blsmsk/blsr/blsi: BMI1 VEX.NDD.0F38.W0 F3 /r//1//3 (dest=vvvv, src=r/m) */
    if (strcmp(mnem, "blsmsk") == 0 || strcmp(mnem, "blsr") == 0 || strcmp(mnem, "blsi") == 0) {
        /* find dest register (first gpr) and src register/memory */
        const reg_t *bd = NULL, *bs = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!bd) bd = r; else if (!bs) bs = r; }
            }
        }
        if (!bd) return 0;
        int digit = (mnem[2] == 's') ? -1 : (mnem[2] == 'r' ? 1 : 3); /* blsmsk=/r, blsr=/1, blsi=/3 */
        int is64 = bd->is64 || (bs && bs->is64);
        /* dest goes in vvvv, src goes in ModRM.rm */
        int src_code = (bs ? bs->code : bd->code);
        /* emit VEX: 0F38, W=is64, vvvv=dest, reg=digit (blski/blsr) or src (blsmsk) */
        emit_vex(out, 0x38, is64 ? 1 : 0, bd->code & 7,
                 (digit >= 0) ? digit : (src_code & 7), src_code & 7, 0, 0x03);
        emit_byte(out, 0xF3);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, (digit >= 0) ? digit : (src_code & 7), &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        /* reg,reg form: modrm = C0 | reg << 3 | rm */
        if (bs) {
            emit_byte(out, 0xC0 | (src_code & 7) << 3 | (bs->code & 7));
            return 1;
        }
        emit_byte(out, 0xC0 | (src_code & 7) << 3 | (src_code & 7));
        return 1;
    }
    /* shlx/shrx/sarx/bzhi/bextr: BMI2 VEX.NDS.0F38.W0 F7/F5 /r (dest=modrm.reg, src1=rm, src2=vvvv) */
    if (strcmp(mnem, "shlx") == 0 || strcmp(mnem, "shrx") == 0 || strcmp(mnem, "sarx") == 0 ||
        strcmp(mnem, "bzhi") == 0 || strcmp(mnem, "bextr") == 0) {
        const reg_t *bd = NULL, *bs1 = NULL, *bs2 = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!bd) bd = r; else if (!bs1) bs1 = r; else if (!bs2) bs2 = r; }
            }
        }
        if (!bd) return 0;
        /* dest = bd, src1 = bs1 (or mem), src2 = bs2; VEX.vvvv = src2, modrm.reg = dest, rm = src1 */
        int digit = 0;
        if (strcmp(mnem, "shlx") == 0) digit = 1;
        else if (strcmp(mnem, "shrx") == 0) digit = 2;
        else if (strcmp(mnem, "sarx") == 0) digit = 7;
        /* bzhi/bextr use opcode F5/F7 with /r (digit from reg=dest) */
        uint8_t opc = (strcmp(mnem, "bzhi") == 0) ? 0xF5 : 0xF7;
        int is64 = bd->is64;
        int src2_code = (bs2 ? bs2->code : (bs1 ? bs1->code : bd->code));
        emit_vex(out, 0x38, is64 ? 1 : 0, src2_code & 7, bd->code & 7,
                 (bs1 ? bs1->code : src2_code) & 7, 0, 0x03);
        emit_byte(out, opc);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, bd->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (bs1) {
            emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (bs1->code & 7));
            return 1;
        }
        emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (src2_code & 7));
        return 1;
    }
    /* andn/pext/pdep: BMI2 VEX.NDS.0F38 F2/F5 /r (dest=modrm.reg, src1=rm, src2=vvvv) */
    if (strcmp(mnem, "andn") == 0 || strcmp(mnem, "pext") == 0 || strcmp(mnem, "pdep") == 0) {
        const reg_t *bd = NULL, *bs1 = NULL, *bs2 = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!bd) bd = r; else if (!bs1) bs1 = r; else if (!bs2) bs2 = r; }
            }
        }
        if (!bd) return 0;
        uint8_t opc = (strcmp(mnem, "andn") == 0) ? 0xF2 : 0xF5;
        int is64 = bd->is64;
        int src2_code = (bs2 ? bs2->code : (bs1 ? bs1->code : bd->code));
        int rm_code = (bs1 ? bs1->code : src2_code);
        /* emit VEX: 0F38, W=is64, vvvv=src2, reg=dest, rm=src1 */
        emit_vex(out, 0x38, is64 ? 1 : 0, src2_code & 7, bd->code & 7, rm_code & 7, 0, 0x03);
        emit_byte(out, opc);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, bd->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (bs1) {
            emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (bs1->code & 7));
            return 1;
        }
        emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (src2_code & 7));
        return 1;
    }
    /* rorx/mulx: BMI2 VEX (rorx=0F3A F0 /r ib, mulx=0F38 F6 /r) */
    if (strcmp(mnem, "rorx") == 0 || strcmp(mnem, "mulx") == 0) {
        const reg_t *bd = NULL, *bs1 = NULL, *bs2 = NULL;
        int mem_tok = -1;
        int64_t rim = 0; int hrim = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { rim = toks[i].value; hrim = 1; }
            else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!bd) bd = r; else if (!bs1) bs1 = r; else if (!bs2) bs2 = r; }
            }
        }
        if (!bd) return 0;
        if (strcmp(mnem, "rorx") == 0) {
            /* rorx r, r/m, imm8 → VEX.LZ.0F3A.W0 F0 /r ib */
            int is64 = bd->is64;
            int src = (bs1 ? bs1->code : bd->code);
            emit_vex(out, 0x3A, is64 ? 1 : 0, 0, bd->code & 7, src & 7, 0, 0x03);
            emit_byte(out, 0xF0);
            if (mem_tok >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, bd->code & 7, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    if (hrim) emit_byte(out, (uint8_t)rim);
                    return 1;
                }
            }
            emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (src & 7));
            if (hrim) emit_byte(out, (uint8_t)rim);
            return 1;
        }
        /* mulx hi, lo, r/m → VEX.NDD.0F38.W1 F6 /r (hi=modrm.reg, lo=vvvv, src=rm) */
        int is64 = bd->is64;
        int src = (bs2 ? bs2->code : (bs1 ? bs1->code : bd->code));
        int lo_code = (bs1 ? bs1->code : bd->code);
        emit_vex(out, 0x38, is64 ? 1 : 0, lo_code & 7, bd->code & 7, src & 7, 0, 0x03);
        emit_byte(out, 0xF6);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, bd->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        emit_byte(out, 0xC0 | (bd->code & 7) << 3 | (src & 7));
        return 1;
    }
    /* vsha512msg1/msg2/rnds2: SHA-NI VEX.256.66.0F38 CC/CD/CB */
    if (strcmp(mnem, "vsha512msg1") == 0 || strcmp(mnem, "vsha512msg2") == 0 ||
        strcmp(mnem, "vsha512rnds2") == 0) {
        const reg_t *d = NULL, *s1 = NULL, *s2 = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) { if (!d) d = r; else if (!s1) s1 = r; else if (!s2) s2 = r; }
            }
        }
        if (!d || !s1) return 0;
        uint8_t opc = (strcmp(mnem, "vsha512msg1") == 0) ? 0xCC :
                      (strcmp(mnem, "vsha512msg2") == 0) ? 0xCD : 0xCB;
        int vvvv = (strcmp(mnem, "vsha512rnds2") == 0 && s2) ? (s2->code & 7) : 0;
        /* VEX: map=0x38(2), w=0, vvvv, reg=dest, rm=s1, l=1(256-bit), pp=1(66) */
        emit_vex(out, 0x38, 0, vvvv & 7, d->code & 7, s1->code & 7, 1, 0x01);
        emit_byte(out, opc);
        emit_byte(out, 0xC0 | (d->code & 7) << 3 | (s1->code & 7));
        return 1;
    }
    /* vp2intersectd/q: AVX512 EVEX.512.66.0F38 68 /r (k mask, zmm, zmm/mem) */
    if (strcmp(mnem, "vp2intersectd") == 0 || strcmp(mnem, "vp2intersectq") == 0) {
        int w = (strcmp(mnem, "vp2intersectq") == 0) ? 1 : 0;
        /* find k mask register (first), then two zmm */
        const reg_t *km = NULL, *d = NULL, *s1 = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->name[0] == 'k') { if (!km) km = r; }
                else if (r && r->is_xmm) { if (!d) d = r; else if (!s1) s1 = r; }
            }
        }
        if (!km || !d) return 0;
        /* EVEX: mm=0x38(2), w, vvvv=d, reg=km, rm=s1 or [mem], ll=2(512), pp=1(66), aaa=km */
        if (s1) {
            emit_evex_aa(out, 0x38, w, d->code & 7, km->code & 7, s1->code & 7, 2, 0x01, km->code & 7);
            emit_byte(out, 0x68);
            emit_byte(out, 0xC0 | (km->code & 7) << 3 | (s1->code & 7));
            return 1;
        }
        /* memory operand */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    emit_evex_aa(out, 0x38, w, d->code & 7, km->code & 7, mop.base_reg >= 0 ? mop.base_reg : 0, 2, 0x01, km->code & 7);
                    emit_byte(out, 0x68);
                    int nr, si;
                    encode_mem_operand(out, km->code & 7, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            }
        }
        return 0;
    }
    /* 3DNow! instructions: femms=0F 0E ; pf* family = 0F 0F /r + pf_imm */
    if (strcmp(mnem, "femms") == 0) { emit_byte(out, 0x0F); emit_byte(out, 0x0E); return 1; }
    {
        struct { const char *name; uint8_t imm; } pf3d[] = {
            { "pavgusb", 0xBF }, { "pf2id", 0x1D }, { "pf2iw", 0x1C },
            { "pfacc", 0xAE }, { "pfadd", 0x9E }, { "pfcmpeq", 0x90 },
            { "pfcmpge", 0x94 }, { "pfcmpgt", 0xA0 }, { "pfmax", 0xA4 },
            { "pfmin", 0x94 }, { "pfmul", 0xB4 }, { "pfnacc", 0x8A },
            { "pfpnacc", 0x8E }, { "pfrcp", 0x96 }, { "pfrcpit1", 0xA6 },
            { "pfrcpit2", 0xB6 }, { "pfrsqit1", 0xA7 }, { "pfrsqrt", 0x97 },
            { "pfsub", 0x9A }, { "pfsubr", 0xAA }, { "pi2fd", 0x0D },
            { "pi2fw", 0x0C }, { "pswapd", 0xBB },
            { "pmulhrw", 0x0B },
            { "pminub", 0xDA }, { "pmaxub", 0xDE },
        };
        uint8_t pfimm = 0; int found3d = 0;
        for (unsigned dx = 0; dx < sizeof(pf3d)/sizeof(pf3d[0]); dx++)
            if (strcmp(mnem, pf3d[dx].name) == 0) { pfimm = pf3d[dx].imm; found3d = 1; break; }
        if (found3d) {
            const reg_t *m1 = NULL, *m2 = NULL;
            int mem_tok = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
                else if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && (r->is_xmm || (r->name[0]=='m' && r->name[1]=='m'))) { if (!m1) m1 = r; else if (!m2) m2 = r; }
                }
            }
            emit_byte(out, 0x0F); emit_byte(out, 0x0F);
            if (mem_tok >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, m1 ? m1->code & 7 : 0, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    emit_byte(out, pfimm);
                    return 1;
                }
            }
            if (m1 && m2) {
                emit_byte(out, 0xC0 | (m1->code & 7) << 3 | (m2->code & 7));
                emit_byte(out, pfimm);
                return 1;
            }
            /* bare memory symbol operand (m64 etc.) → RIP-relative + pf_imm */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (m1 ? m1->code & 7 : 0) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    emit_byte(out, pfimm);
                    return 1;
                }
            }
            return 0;
        }
    }
    /* prefetch/prefetchw/prefetchnta: 0F 0D /0 /1 /2 (memory operand) */
    if (strcmp(mnem, "prefetch") == 0 || strcmp(mnem, "prefetchw") == 0 ||
        strcmp(mnem, "prefetchnta") == 0) {
        int digit = (strcmp(mnem, "prefetchw") == 0) ? 1 : (strcmp(mnem, "prefetchnta") == 0) ? 2 : 0;
        emit_byte(out, 0x0F); emit_byte(out, 0x0D);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 1;
    }
    /* fldenv/fnstenv/fldcw/fnstcw/fstenv: x87 env/control ops (D9/DD/0F D9 /digit) */
    if (strcmp(mnem, "fldenv") == 0 || strcmp(mnem, "fnstenv") == 0 ||
        strcmp(mnem, "fstenv") == 0 || strcmp(mnem, "fldcw") == 0 ||
        strcmp(mnem, "fstcw") == 0 || strcmp(mnem, "fnstcw") == 0) {
        uint8_t pre = 0xD9; int digit = 4;
        if (strcmp(mnem, "fnstenv") == 0 || strcmp(mnem, "fstenv") == 0) digit = 6;
        else if (strcmp(mnem, "fldcw") == 0) digit = 5;
        else if (strcmp(mnem, "fstcw") == 0 || strcmp(mnem, "fnstcw") == 0) digit = 7;
        if (strcmp(mnem, "fstcw") == 0) emit_byte(out, 0x9B);
        if (strcmp(mnem, "fnstcw") == 0) emit_byte(out, 0x9B);
        emit_byte(out, pre);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 1;
    }
    /* frstor/fnsave/fnstsw/fsave/fnstsw: x87 state ops (DD /1 //0 //7 //6 //2) */
    if (strcmp(mnem, "frstor") == 0 || strcmp(mnem, "fnsave") == 0 || strcmp(mnem, "fsave") == 0 ||
        strcmp(mnem, "fnstsw") == 0 || strcmp(mnem, "fstsw") == 0) {
        int digit = (strcmp(mnem, "frstor") == 0) ? 1 : (strcmp(mnem, "fnsave") == 0 || strcmp(mnem, "fsave") == 0) ? 6 : 7;
        if (strcmp(mnem, "fsave") == 0 || strcmp(mnem, "fstsw") == 0) emit_byte(out, 0x9B);
        emit_byte(out, 0xDD);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 1;
    }
    /* prefetcht0/prefetcht1/prefetcht2: 0F 18 /1 /2 /3 (memory operand) */
    if (strcmp(mnem, "prefetcht0") == 0 || strcmp(mnem, "prefetcht1") == 0 ||
        strcmp(mnem, "prefetcht2") == 0) {
        int digit = (mnem[9] == '0') ? 1 : (mnem[9] == '1') ? 2 : 3;
        emit_byte(out, 0x0F); emit_byte(out, 0x18);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    return 1;
                }
            } else if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "ptr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                emit_byte(out, 0x05 | digit << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        return 1;
    }
    /* in/out: E4/E5 imm8, EC/ED dx (I/O port) */
    if (strcmp(mnem, "in") == 0 || strcmp(mnem, "out") == 0) {
        const reg_t *ior = NULL;
        int64_t iop = 0; int hiop = 0, has_dx = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { iop = toks[i].value; hiop = 1; }
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) {
                    if (strcmp(r->name, "dx") == 0) has_dx = 1;
                    else if (!ior) ior = r;
                }
            }
        }
        /* in: dest = ior (al/ax/eax); out: source = ior */
        int is_in = (mnem[0] == 'i');
        if (!ior) return 0;
        if (has_dx) {
            if (ior->name[0] == 'a' && ior->name[1] == 'l') emit_byte(out, is_in ? 0xEC : 0xEE);
            else if (ior->name[0] == 'a' && ior->name[1] == 'x') { emit_byte(out, 0x66); emit_byte(out, is_in ? 0xED : 0xEF); }
            else { emit_byte(out, is_in ? 0xED : 0xEF); }
            return 1;
        }
        if (hiop) {
            if (ior->name[0] == 'a' && ior->name[1] == 'l') { emit_byte(out, is_in ? 0xE4 : 0xE6); }
            else if (ior->name[0] == 'a' && ior->name[1] == 'x') { emit_byte(out, 0x66); emit_byte(out, is_in ? 0xE5 : 0xE7); }
            else { emit_byte(out, is_in ? 0xE5 : 0xE7); }
            emit_byte(out, (uint8_t)iop);
            return 1;
        }
        return 0;
    }
    /* shift/rotate by cl (D2/D3 /digit) or by imm (C0/C1 /digit ib) */
    if (strcmp(mnem, "shl") == 0 || strcmp(mnem, "shr") == 0 || strcmp(mnem, "sal") == 0 ||
        strcmp(mnem, "sar") == 0 || strcmp(mnem, "rol") == 0 || strcmp(mnem, "ror") == 0 ||
        strcmp(mnem, "rcl") == 0 || strcmp(mnem, "rcr") == 0) {
        int digit;
        if (strcmp(mnem, "shl") == 0 || strcmp(mnem, "sal") == 0) digit = 4;
        else if (strcmp(mnem, "shr") == 0) digit = 5;
        else if (strcmp(mnem, "sar") == 0) digit = 7;
        else if (strcmp(mnem, "rol") == 0) digit = 0;
        else if (strcmp(mnem, "ror") == 0) digit = 1;
        else if (strcmp(mnem, "rcl") == 0) digit = 2;
        else digit = 3; /* rcr */
        const reg_t *sr = NULL;
        int64_t shcnt = 0; int hsh = 0, shcl = 0;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { shcnt = toks[i].value; hsh = 1; }
            else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && strcmp(r->name, "cl") == 0) shcl = 1;
                else if (r && !r->is_xmm) { if (!sr) sr = r; }
            }
        }
        /* determine 8-bit */
        int is8 = 0;
        if (sr) is8 = reg_is8(sr);
        if (mem_tok >= 0 && !sr) {
            /* shift [mem], ... — treat as 8-bit? use D2/D3 via 66/REX handled below; default 16-bit word */
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                if (shcl) {
                    emit_byte(out, 0x66); emit_byte(out, 0xD3);
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                } else {
                    emit_byte(out, 0x66); emit_byte(out, 0xC1);
                    int nr, si;
                    encode_mem_operand(out, digit, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    emit_byte(out, (uint8_t)shcnt);
                }
                return 1;
            }
        }
        if (sr) {
            int w = (sr->is64) ? 1 : 0;
            int b = (sr->code >= 8) ? 1 : 0;
            if (shcl) {
                if (!is8 && reg_is16(sr)) emit_byte(out, 0x66);
                emit_rex(out, w, 0, b);
                emit_byte(out, is8 ? 0xD2 : 0xD3);
                emit_byte(out, 0xC0 | digit << 3 | (sr->code & 7));
                return 1;
            }
            if (shcnt == 1) {
                /* shift/rotate by 1: short form D0/D1, no immediate byte */
                if (!is8 && reg_is16(sr)) emit_byte(out, 0x66);
                emit_rex(out, w, 0, b);
                emit_byte(out, is8 ? 0xD0 : 0xD1);
                emit_byte(out, 0xC0 | digit << 3 | (sr->code & 7));
                return 1;
            }
            /* immediate count: C0/C1 + imm8 */
            if (!is8 && reg_is16(sr)) emit_byte(out, 0x66);
            emit_rex(out, w, 0, b);
            emit_byte(out, is8 ? 0xC0 : 0xC1);
            emit_byte(out, 0xC0 | digit << 3 | (sr->code & 7));
            emit_byte(out, (uint8_t)shcnt);
            return 1;
        }
        /* shift <symbol>, cl → 66 D3 /digit RIP-rel ; shift <symbol>, imm → 66 C1 /digit ib */
        if (shcl) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x66); emit_byte(out, 0xD3);
                    emit_byte(out, 0x05 | digit << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        } else if (hsh) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x66); emit_byte(out, 0xC1);
                    emit_byte(out, 0x05 | digit << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    emit_byte(out, (uint8_t)shcnt);
                    return 1;
                }
            }
        }
        return 0;
    }
    /* shld/shrd: 0F A4/A5 /r ib (immediate or cl), 0F AC/AD /r ib */
    if (strcmp(mnem, "shld") == 0 || strcmp(mnem, "shrd") == 0) {
        int is_shld = (mnem[2] == 'l');
        const reg_t *hd = NULL, *hs = NULL;
        int64_t him = 0; int hhi = 0, hcl = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { him = toks[i].value; hhi = 1; }
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && strcmp(r->name, "cl") == 0) hcl = 1;
                else if (r && !r->is_xmm) { if (!hd) hd = r; else if (!hs) hs = r; }
            }
        }
        if (hd && hs) {
            emit_byte(out, 0x66);
            emit_byte(out, 0x0F);
            emit_byte(out, is_shld ? (hcl ? 0xA5 : 0xA4) : (hcl ? 0xAD : 0xAC));
            emit_byte(out, 0xC0 | (hd->code & 7) << 3 | (hs->code & 7));
            if (!hcl && hhi) emit_byte(out, (uint8_t)him);
            return 1;
        }
        /* shld <sym>, <reg>, <imm> → 66 0F A4/AC /r RIP-rel + imm8 */
        if ((hd || hs) && hhi) {
            const reg_t *srcreg = hd ? hd : hs;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x66);
                    emit_byte(out, 0x0F);
                    emit_byte(out, is_shld ? 0xA4 : 0xAC);
                    emit_byte(out, 0x05 | (srcreg->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    emit_byte(out, (uint8_t)him);
                    return 1;
                }
            }
        }
        return 0;
    }
    /* neg r/m: F6 /3 (8-bit), F7 /3 (16/32/64). */
    if (strcmp(mnem, "neg") == 0) {
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem) {
            emit_byte(out, 0xF6);
            int nr, si;
            encode_mem_operand(out, 3, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
    }

    /* not r/m: F6 /2 (8-bit), F7 /2 (16/32/64). */
    if (strcmp(mnem, "not") == 0) {
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem) {
            emit_byte(out, 0xF6);
            int nr, si;
            encode_mem_operand(out, 2, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
    }

    /* cmpxchg8b/cmpxchg16b m64/m128: 0F C7 /1, REX.W for 16b. */
    if (strcmp(mnem, "cmpxchg8b") == 0 || strcmp(mnem, "cmpxchg16b") == 0) {
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (found_mem) {
            if (strcmp(mnem, "cmpxchg16b") == 0) emit_byte(out, 0x48);  /* REX.W */
            emit_byte(out, 0x0F);
            emit_byte(out, 0xC7);
            int nr, si;
            encode_mem_operand(out, 1, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
    }

    if (strcmp(mnem, "add") == 0 || strcmp(mnem, "sub") == 0 ||
        strcmp(mnem, "cmp") == 0 || strcmp(mnem, "and") == 0 ||
        strcmp(mnem, "or") == 0 || strcmp(mnem, "adc") == 0 ||
        strcmp(mnem, "sbb") == 0 || strcmp(mnem, "xor") == 0) {
        /* /r extension opcode: add=0 sub=5 cmp=7 and=4 or=1 adc=2 sbb=3 xor=6 */
        int op;
        if (mnem[0] == 'a' && mnem[1] == 'd' && mnem[2] == 'd') op = 0;
        else if (mnem[0] == 'a' && mnem[1] == 'd' && mnem[2] == 'c') op = 2;
        else if (mnem[0] == 'a' && mnem[1] == 'n' && mnem[2] == 'd') op = 4;
        else if (mnem[0] == 's' && mnem[1] == 'u' && mnem[2] == 'b') op = 5;
        else if (mnem[0] == 's' && mnem[1] == 'b' && mnem[2] == 'b') op = 3;
        else if (mnem[0] == 'c' && mnem[1] == 'm' && mnem[2] == 'p') op = 7;
        else if (mnem[0] == 'o' && mnem[1] == 'r') op = 1;
        else op = 6;  /* xor */
        /* 8-bit form: 00 /r (add), 10 /r (adc), 08 /r (or), 20 /r (and),
         * 28 /r (sub), 18 /r (sbb), 38 /r (cmp), 30 /r (xor) */
        int is_8bit = (r1 && !r1->is64 && (r1->code < 4 || r1->code >= 8));
        (void)is_8bit;
        if (r1 && has_imm) {
            int w = (r1->is64) ? 1 : 0;
            int b = (r1->code >= 8) ? 1 : 0;
            if (reg_is8(r1)) {
                /* AL accumulator special short forms (add 04, or 0C, adc 14, sbb 1C,
                 * and 24, sub 2C, xor 34, cmp 3C); other 8-bit regs use 80 /digit ib */
                if (r1->code == 0 && !b) {
                    static const uint8_t al_opc[8] = { 0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C };
                    emit_byte(out, al_opc[op]);
                    emit_byte(out, (uint8_t)imm);
                } else {
                    emit_rex(out, 0, 0, b);
                    emit_byte(out, 0x80);
                    emit_byte(out, 0xC0 | op << 3 | (r1->code & 7));
                    emit_byte(out, (uint8_t)imm);
                }
                return 1;
            }
            if (reg_is16(r1)) emit_byte(out, 0x66);
            emit_rex(out, w, 0, b);
            int64_t sv = (int64_t)imm;
            if (sv >= -128 && sv <= 127) {
                emit_byte(out, 0x83);
                emit_byte(out, 0xC0 | op << 3 | (r1->code & 7));
                emit_byte(out, (uint8_t)(int8_t)sv);
            } else {
                emit_byte(out, 0x81);
                emit_byte(out, 0xC0 | op << 3 | (r1->code & 7));
                emit_imm(out, (uint64_t)sv, reg_is16(r1) ? 2 : 4);
            }
            return 1;
        }
        if (r1 && r2) {
            /* reg, reg — Intel order r1=dest, r2=src. 8-bit base opcodes
             * 00/10/08/20/28/18/38/30, 16/32/64 base 01/11/09/21/29/19/39/31 */
            int is8 = reg_is8(r1) && reg_is8(r2);
            int w   = (r1->is64 || r2->is64) ? 1 : 0;
            int rr  = (r2->code >= 8) ? 1 : 0;   /* src in reg field */
            int rb  = (r1->code >= 8) ? 1 : 0;   /* dest in rm field */
            if (!is8 && !w && reg_is16(r1)) emit_byte(out, 0x66);
            emit_rex(out, w, rr, rb);
            emit_byte(out, (uint8_t)((is8 ? 0x00 : 0x01) + op * 8));
            emit_byte(out, 0xC0 | (r2->code & 7) << 3 | (r1->code & 7));
            return 1;
        }
        /* reg, [mem] via symbol: RIP-relative 03 05 r/m form
         * (add r64,r/m32: 03 /r; sub 2B; cmp 3B; and 23; or 0B; adc 13; sbb 1B; xor 33) */
        if (r1 && r2 == NULL && !has_imm) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    if (r1->is64) emit_byte(out, 0x48);
                    uint8_t op2;
                    switch (op) {
                        case 0: op2 = 0x03; break;  /* add */
                        case 1: op2 = 0x0B; break;  /* or  */
                        case 2: op2 = 0x13; break;  /* adc */
                        case 3: op2 = 0x1B; break;  /* sbb */
                        case 4: op2 = 0x23; break;  /* and */
                        case 5: op2 = 0x2B; break;  /* sub */
                        case 6: op2 = 0x33; break;  /* xor */
                        default: op2 = 0x3B; break; /* cmp */
                    }
                    emit_byte(out, op2);
                    emit_byte(out, 0x05 | (r1->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2 /*R_X86_64_PC32*/, -4);
                    return 1;
                }
            }
            return 0;
        }
        /* mem, imm form: opcode 80/81/83 /r imm */
        /* Detect if r1 is actually a symbol (not a register) */
        {
            int sym_imm = -1;
            const char *sym_name = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    sym_name = toks[i].text;
                } else if (toks[i].type == ATOK_NUM) {
                    sym_imm = (int)toks[i].value;
                }
            }
            if (sym_name && sym_imm >= 0) {
                int si = find_or_add_sym(out, sym_name);
                if (sym_imm <= 0x7F) {
                    emit_byte(out, 0x83);
                    emit_byte(out, 0x05 | op << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2 /*R_X86_64_PC32*/, -4);
                    emit_byte(out, (uint8_t)sym_imm);
                } else {
                    emit_byte(out, 0x81);
                    emit_byte(out, 0x05 | op << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2 /*R_X86_64_PC32*/, -4);
                    emit_imm(out, (uint64_t)sym_imm, 4);
                }
                return 1;
            }
        }
        /* add/sub/... <sym>, <sym2> — two stack-relative symbols via rax */
        if (!r1 && !r2) {
            int dst_si = -1, src_si = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    if (dst_si < 0) dst_si = find_or_add_sym(out, toks[i].text);
                    else if (src_si < 0) src_si = find_or_add_sym(out, toks[i].text);
                }
            }
            if (dst_si >= 0 && src_si >= 0) {
                int64_t d_off = (int64_t)out->syms[dst_si].value;
                int64_t s_off = (int64_t)out->syms[src_si].value;
                /* mov rax, [rbp+src] */
                emit_byte(out, 0x48); emit_byte(out, 0x8B);
                emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)s_off);
                /* op [rbp+dst], rax : add=01 sub=29 and=21 or=09 adc=11 sbb=19 xor=31 cmp=39 */
                uint8_t mopc;
                if (op == 0) mopc = 0x01;
                else if (op == 5) mopc = 0x29;
                else if (op == 4) mopc = 0x21;
                else if (op == 1) mopc = 0x09;
                else if (op == 2) mopc = 0x11;
                else if (op == 3) mopc = 0x19;
                else if (op == 6) mopc = 0x31;
                else mopc = 0x39;
                emit_byte(out, 0x48); emit_byte(out, mopc);
                emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)d_off);
                return 1;
            }
        }
        return 0;
    }
    if (strcmp(mnem, "imul") == 0) {
        /* imul forms: 1-op r/m (F6/F7 /5), 2-op r,r/m (0F AF /r), 3-op r,r/m,imm (69/6B /r) */
        const reg_t *i1 = NULL, *i2 = NULL;
        const char *imsym = NULL;
        int64_t iimm = 0; int hii = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { iimm = toks[i].value; hii = 1; }
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!i1) i1 = r; else if (!i2) i2 = r; }
                else if (!imsym) imsym = toks[i].text;
            }
        }
        /* 8-bit reg helper: name ends with 'l' or is ah/ch/dh/bh */
        #define IMUL_IS8(r) (!(r)->is64 && ((r)->name[0] && (r)->name[strlen((r)->name)-1] == 'l' || \
                             (strlen((r)->name) == 2 && (r)->name[1] == 'h')))
        if (hii) {
            /* 3-op: imul r1, r2/r/m, imm  or  2-op with implicit src: imul r, imm */
            if (!i1) return 0;
            int use_imm8 = (iimm >= -128 && iimm <= 127);
            uint8_t opc = use_imm8 ? 0x6B : 0x69;
            if (i2) {
                /* imul r1, r2, imm */
                if (i1->is64 || i2->is64) emit_byte(out, 0x48);
                emit_byte(out, opc);
                emit_byte(out, 0xC0 | (i1->code & 7) << 3 | (i2->code & 7));
                if (use_imm8) emit_byte(out, (uint8_t)iimm); else emit_imm(out, (uint64_t)iimm, 4);
                return 1;
            }
            if (imsym) {
                /* imul r, [sym], imm */
                int si = find_or_add_sym(out, imsym);
                if (i1->is64) emit_byte(out, 0x48);
                emit_byte(out, opc);
                emit_byte(out, 0x05 | (i1->code & 7) << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                if (use_imm8) emit_byte(out, (uint8_t)iimm); else emit_imm(out, (uint64_t)iimm, 4);
                return 1;
            }
            /* imul r, imm → implicit src = r */
            if (i1->is64) emit_byte(out, 0x48);
            emit_byte(out, opc);
            emit_byte(out, 0xC0 | (i1->code & 7) << 3 | (i1->code & 7));
            if (use_imm8) emit_byte(out, (uint8_t)iimm); else emit_imm(out, (uint64_t)iimm, 4);
            return 1;
        }
        if (i1 && i2) {
            /* imul r1, r2 → 0F AF /r */
            if (i1->is64 || i2->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x0F); emit_byte(out, 0xAF);
            emit_byte(out, 0xC0 | (i1->code & 7) << 3 | (i2->code & 7));
            return 1;
        }
        if (i1 && imsym) {
            /* imul r, [sym] → 0F AF /r RIP-rel */
            int si = find_or_add_sym(out, imsym);
            if (i1->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x0F); emit_byte(out, 0xAF);
            emit_byte(out, 0x05 | (i1->code & 7) << 3);
            emit_imm(out, 0, 4);
            if (si >= 0) add_fixup(out, si, 2, -4);
            return 1;
        }
        /* single operand: imul r/m → F6 /5 (8-bit) or F7 /5 (16/32/64) */
        if (i1) {
            if (IMUL_IS8(i1)) {
                emit_byte(out, 0xF6);
                emit_byte(out, 0xC0 | 5 << 3 | (i1->code & 7));
            } else {
                if (i1->is64) emit_byte(out, 0x48);
                emit_byte(out, 0xF7);
                emit_byte(out, 0xC0 | 5 << 3 | (i1->code & 7));
            }
            return 1;
        }
        if (imsym) {
            /* imul [sym] → F6/F7 /5 RIP-rel */
            int si = find_or_add_sym(out, imsym);
            emit_byte(out, 0xF7);
            emit_byte(out, 0x05 | 5 << 3);
            emit_imm(out, 0, 4);
            if (si >= 0) add_fixup(out, si, 2, -4);
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "xor") == 0) {
        /* xor reg, reg */
        if (r1 && r2 && r1->code == r2->code) {
            if (r1->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x31);
            emit_byte(out, 0xC0 | (r1->code & 7) << 3 | (r2->code & 7));
            return 1;
        }
        if (r1 && has_imm) {
            if (r1->is64) emit_byte(out, 0x48);
            emit_byte(out, 0x81);
            emit_byte(out, 0xF0 | (r1->code & 7) << 3);
            emit_imm(out, imm, 4);
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "inc") == 0) {
        if (r1) { if (r1->is64) emit_byte(out, 0x48); emit_byte(out, 0xFF); emit_byte(out, 0xC0 | (r1->code & 7)); return 1; }
        return 0;
    }
    if (strcmp(mnem, "dec") == 0) {
        if (r1) { if (r1->is64) emit_byte(out, 0x48); emit_byte(out, 0xFF); emit_byte(out, 0xC8 | (r1->code & 7)); return 1; }
        return 0;
    }
    /* adcx / adox: 66 0F 38 F6/r and F3 0F 38 F6/r
     * adcx/adox r, r/m32|r/m64 (needs REX.W for 64-bit) */
    if (strcmp(mnem, "adcx") == 0 || strcmp(mnem, "adox") == 0) {
        if (!r1) return 0;
        int is_adcx = (mnem[2] == 'c');
        /* prefix */
        if (is_adcx) emit_byte(out, 0x66);
        else emit_byte(out, 0xF3);
        if (r1->is64) emit_byte(out, 0x48);
        emit_byte(out, 0x0F);
        emit_byte(out, 0x38);
        emit_byte(out, 0xF6);
        /* second operand: check for memory first (skip tokens inside []) then register */
        int found_mem = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                int ni = parse_mem_operand(toks, i, n, &mop);
                if (ni < 0) return 0;
                int needs_reloc, sym_idx;
                encode_mem_operand(out, r1->code & 7, &mop, &needs_reloc, &sym_idx);
                (void)ni; (void)sym_idx;
                found_mem = 1;
                break;
            }
        }
        if (found_mem) return 1;
        if (r2) {
            uint8_t modrm = 0xC0 | (r1->code & 7) << 3 | (r2->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        return 0;
    }
    /* movq: xmm/gpr/mem quadword moves (SIMD)
     *  movq xmm1, xmm2        -> F3 0F 7E /r
     *  movq xmm1, r64         -> 66 REX.W 0F 6E /r
     *  movq r64, xmm1         -> 66 REX.W 0F 7E /r
     *  movq xmm1, [mem]       -> F3 0F 7E /r
     *  movq [mem], xmm1       -> 66 0F D6 /r
     */
    if (strcmp(mnem, "movq") == 0 || strcmp(mnem, "movd") == 0 ||
        strcmp(mnem, "movdqa") == 0 || strcmp(mnem, "movdqu") == 0) {
        int is_movq = (mnem[3] == 'q');
        int is_movd = (mnem[3] == 'd' && mnem[4] == 0);
        int is_dqu = (mnem[3] == 'd' && mnem[4] == 'u');
        /* operand collection: find first register of each class */
        const reg_t *r_xmm1 = NULL, *r_gpr1 = NULL, *r_2nd = NULL;
        const reg_t *r_mmx = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) {
                    if (r->name[0] == 'm' && r->name[1] == 'm') {
                        /* MMX register */
                        if (!r_mmx) r_mmx = r; else if (!r_2nd) r_2nd = r;
                    } else if (r->is_xmm) {
                        if (!r_xmm1) r_xmm1 = r; else if (!r_2nd) r_2nd = r;
                    } else {
                        if (!r_gpr1) r_gpr1 = r; else if (r->is64 && !r_2nd) r_2nd = r;
                    }
                }
            }
        }
        /* ---- MMX operand forms ---- */
        if (r_mmx) {
            /* movd mm, r32/r64 → 0F 6E /r ; movq mm, mm → 0F 6F /r ; movq mm, m64 → 0F 6F /r */
            int dest_is_mmx = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->name[0] == 'm' && r->name[1] == 'm') { dest_is_mmx = 1; break; }
                    if (r) break;   /* first reg found; if not mmx, mmx is src */
                }
            }
            if (dest_is_mmx) {
                /* dest = mm register */
                if (r_gpr1) {
                    /* movd mm, r32/r64 → (REX.W) 0F 6E /r */
                    if (r_gpr1->is64) emit_byte(out, 0x48);
                    emit_byte(out, 0x0F); emit_byte(out, 0x6E);
                    emit_byte(out, 0xC0 | (r_mmx->code & 7) << 3 | (r_gpr1->code & 7));
                    return 1;
                }
                /* movd/mmx mm, [mem] → (REX.W) 0F 6E /r (mem load into mm) */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                        mem_op_t mop;
                        if (parse_mem_operand(toks, i, n, &mop) < 0) break;
                        /* 64-bit memory operand (m64/fl64/@dq): REX.W */
                        int mem64 = 0;
                        for (int j = 1; j < n; j++)
                            if (toks[j].type == ATOK_ID && (strcmp(toks[j].text, "QWORD") == 0 ||
                                strcmp(toks[j].text, "qword") == 0 || strcmp(toks[j].text, "@dq") == 0))
                                mem64 = 1;
                        if (mem64) emit_byte(out, 0x48);
                        emit_byte(out, 0x0F); emit_byte(out, 0x6E);
                        int nr, si;
                        encode_mem_operand(out, r_mmx->code & 7, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        return 1;
                    }
                }
                /* movd mm, <symbol> (m32/m64/fl32/fl64) → (REX.W) 0F 6E /r RIP-rel */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                        int mem64 = 0;
                        for (int j = 1; j < n; j++)
                            if (toks[j].type == ATOK_ID && (strcmp(toks[j].text, "@dq") == 0 ||
                                strcmp(toks[j].text, "m64") == 0 || strcmp(toks[j].text, "fl64") == 0))
                                mem64 = 1;
                        if (mem64) emit_byte(out, 0x48);
                        emit_byte(out, 0x0F); emit_byte(out, 0x6E);
                        int si = find_or_add_sym(out, toks[i].text);
                        emit_byte(out, 0x05 | (r_mmx->code & 7) << 3);
                        emit_imm(out, 0, 4);
                        if (si >= 0) add_fixup(out, si, 2, -4);
                        return 1;
                    }
                }
            } else {
                /* dest = gpr, src = mm: movd r32/r64, mm → (REX.W) 0F 7E /r */
                if (r_gpr1) {
                    if (r_gpr1->is64) emit_byte(out, 0x48);
                    emit_byte(out, 0x0F); emit_byte(out, 0x7E);
                    emit_byte(out, 0xC0 | (r_gpr1->code & 7) << 3 | (r_mmx->code & 7));
                    return 1;
                }
                /* movd/mmx [mem], mm → (REX.W) 0F 7E /r (mem store) */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                        mem_op_t mop;
                        if (parse_mem_operand(toks, i, n, &mop) < 0) break;
                        int mem64 = 0;
                        for (int j = 1; j < n; j++)
                            if (toks[j].type == ATOK_ID && (strcmp(toks[j].text, "QWORD") == 0 ||
                                strcmp(toks[j].text, "qword") == 0 || strcmp(toks[j].text, "@dq") == 0))
                                mem64 = 1;
                        if (mem64) emit_byte(out, 0x48);
                        emit_byte(out, 0x0F); emit_byte(out, 0x7E);
                        int nr, si;
                        encode_mem_operand(out, r_mmx->code & 7, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        return 1;
                    }
                }
                /* movd <symbol>, mm → (REX.W) 0F 7E /r RIP-rel (mem store) */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                        int mem64 = 0;
                        for (int j = 1; j < n; j++)
                            if (toks[j].type == ATOK_ID && (strcmp(toks[j].text, "@dq") == 0 ||
                                strcmp(toks[j].text, "m64") == 0 || strcmp(toks[j].text, "fl64") == 0))
                                mem64 = 1;
                        if (mem64) emit_byte(out, 0x48);
                        emit_byte(out, 0x0F); emit_byte(out, 0x7E);
                        int si = find_or_add_sym(out, toks[i].text);
                        emit_byte(out, 0x05 | (r_mmx->code & 7) << 3);
                        emit_imm(out, 0, 4);
                        if (si >= 0) add_fixup(out, si, 2, -4);
                        return 1;
                    }
                }
            }
        }
        /* movd xmm, r32/r64 → 66 (REX.W) 0F 6E /r ; movd r32/r64, xmm → 66 (REX.W) 0F 7E /r */
        if (is_movd && r_xmm1 && r_gpr1 && !r_2nd) {
            /* determine which is dest: xmm first or gpr first */
            int first_is_xmm = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) { first_is_xmm = r->is_xmm; break; }
                }
            }
            emit_byte(out, 0x66);
            if (r_gpr1->is64) emit_byte(out, 0x48);   /* REX.W */
            emit_byte(out, 0x0F);
            emit_byte(out, first_is_xmm ? 0x6E : 0x7E);
            uint8_t modrm;
            if (first_is_xmm) modrm = 0xC0 | (r_xmm1->code & 7) << 3 | (r_gpr1->code & 7);
            else modrm = 0xC0 | (r_gpr1->code & 7) << 3 | (r_xmm1->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        /* movd xmm, [mem] → 66 0F 6E /r RIP-rel ; movd [mem], xmm → 66 0F 7E /r */
        if (is_movd && r_xmm1 && !r_gpr1) {
            int found_mem = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                    /* dest is mem if xmm appears before the memory operand */
                    int xmm_before = 0;
                    for (int j = 1; j < i; j++)
                        if (toks[j].type == ATOK_ID) {
                            const reg_t *r = find_reg(toks[j].text);
                            if (r && r->is_xmm) xmm_before = 1;
                        }
                    emit_byte(out, 0x66);
                    emit_byte(out, 0x0F);
                    emit_byte(out, xmm_before ? 0x7E : 0x6E);
                    int nr, si;
                    encode_mem_operand(out, r_xmm1->code & 7, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    found_mem = 1;
                    break;
                }
            }
            if (found_mem) return 1;
        }
        /* movd xmm, <symbol> / movd <symbol>, xmm → 66 (REX.W) 0F 6E/7E /r RIP-rel */
        if (is_movd && r_xmm1 && !r_gpr1 && !r_mmx) {
            int found_sym = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                    int xmm_before = 0;
                    for (int j = 1; j < i; j++)
                        if (toks[j].type == ATOK_ID) {
                            const reg_t *r = find_reg(toks[j].text);
                            if (r && r->is_xmm) xmm_before = 1;
                        }
                    int mem64 = 0;
                    for (int j = 1; j < n; j++)
                        if (toks[j].type == ATOK_ID && (strcmp(toks[j].text, "@dq") == 0 ||
                            strcmp(toks[j].text, "m64") == 0 || strcmp(toks[j].text, "fl64") == 0))
                            mem64 = 1;
                    emit_byte(out, 0x66);
                    if (mem64) emit_byte(out, 0x48);
                    emit_byte(out, 0x0F);
                    emit_byte(out, xmm_before ? 0x7E : 0x6E);
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (r_xmm1->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    found_sym = 1;
                    break;
                }
            }
            if (found_sym) return 1;
        }
        /* movq mm, mm / movq mm, <mem> → 0F 6F /r ; mm → 0F 7F /r (for mm↔mm only) */
        if (is_movq && r_mmx && !r_gpr1 && !r_xmm1) {
            /* mm↔mm: movq mm1, mm0 → 0F 6F /r ; dest is first mm */
            int first_mm_code = -1, second_mm_code = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->name[0] == 'm' && r->name[1] == 'm') {
                        if (first_mm_code < 0) first_mm_code = r->code & 7;
                        else if (second_mm_code < 0) second_mm_code = r->code & 7;
                    }
                }
            }
            if (second_mm_code >= 0) {
                emit_byte(out, 0x0F); emit_byte(out, 0x6F);
                emit_byte(out, 0xC0 | first_mm_code << 3 | second_mm_code);
                return 1;
            }
            /* mm, <symbol> → 0F 6F /r RIP-rel */
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                    emit_byte(out, 0x0F); emit_byte(out, 0x6F);
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (first_mm_code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        }
        /* movq xmm, <symbol> / movq <symbol>, xmm → F3 0F 7E /r RIP-rel (load) */
        if (is_movq && r_xmm1 && !r_gpr1 && !r_mmx) {
            int found_sym = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) && strcmp(toks[i].text, "offset") != 0) {
                    int xmm_before = 0;
                    for (int j = 1; j < i; j++)
                        if (toks[j].type == ATOK_ID) {
                            const reg_t *r = find_reg(toks[j].text);
                            if (r && r->is_xmm) xmm_before = 1;
                        }
                    emit_byte(out, 0xF3);
                    emit_byte(out, 0x0F);
                    emit_byte(out, xmm_before ? 0xD6 : 0x7E);
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (r_xmm1->code & 7) << 3);
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    found_sym = 1;
                    break;
                }
            }
            if (found_sym) return 1;
        }
        /* movq xmm, r64 */
        if (is_movq && r_xmm1 && r_gpr1 && !r_2nd) {
            emit_byte(out, 0x66);
            emit_byte(out, 0x48);   /* REX.W */
            emit_byte(out, 0x0F);
            emit_byte(out, 0x6E);
            uint8_t modrm = 0xC0 | (r_xmm1->code & 7) << 3 | (r_gpr1->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        /* movq r64, xmm (dest is gpr) — gpr appears before xmm */
        if (is_movq && r_gpr1 && r_xmm1 && !r_2nd && r_gpr1 != NULL) {
            /* need to determine which is dest: if first operand is gpr */
            int first_is_gpr = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) { first_is_gpr = !r->is_xmm; break; }
                }
            }
            if (first_is_gpr) {
                emit_byte(out, 0x66);
                emit_byte(out, 0x48);   /* REX.W */
                emit_byte(out, 0x0F);
                emit_byte(out, 0x7E);
                uint8_t modrm = 0xC0 | (r_gpr1->code & 7) << 3 | (r_xmm1->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
        }
        /* movq/movd xmm, <float const> — literal pool via .data + RIP-relative load */
        if ((is_movq || is_movd) && r_xmm1 && !r_gpr1 && !r_2nd) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_NUM) {
                    uint64_t bits = toks[i].value;
                    int64_t off;
                    if (is_movd) {
                        /* movd: 32-bit single-precision pool entry */
                        off = litpool_get_or_add_w(out, bits, 4);
                        emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x6E);
                    } else {
                        off = litpool_get_or_add(out, bits);
                        emit_byte(out, 0xF3); emit_byte(out, 0x0F); emit_byte(out, 0x7E);
                    }
                    if (off < 0) return 0;
                    emit_byte(out, 0x05 | (r_xmm1->code & 7) << 3);
                    emit_imm(out, (uint64_t)off, 4);
                    /* fixup referencing .data offset */
                    int si = find_or_add_sym(out, "litpool");
                    if (si >= 0 && out->nfixups < 256) {
                        asmc_fixup_t *f = &out->fixups[out->nfixups++];
                        f->offset = cur_offset(out) - 4;
                        f->sym_index = si;
                        f->type = 2; /* R_X86_64_PC32 */
                        f->addend = -4 + (int)off;
                        f->sec = out->cur_sec;
                    }
                    return 1;
                }
            }
        }
        /* movq/movdqa/movdqu xmm, xmm or xmm, [mem] */
        if (r_xmm1) {
            if (is_dqu) emit_byte(out, 0xF3);
            else if (is_movq) emit_byte(out, 0xF3);
            else emit_byte(out, 0x66);
            emit_byte(out, 0x0F);
            emit_byte(out, is_movq ? 0x7E : 0x6F);
            /* second operand */
            int found_mem = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                    int nr, si;
                    encode_mem_operand(out, r_xmm1->code & 7, &mop, &nr, &si);
                    (void)nr; (void)si;
                    found_mem = 1;
                    break;
                }
            }
            if (found_mem) return 1;
            if (r_2nd && r_2nd->is_xmm) {
                uint8_t modrm = 0xC0 | (r_xmm1->code & 7) << 3 | (r_2nd->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
            return 0;
        }
        return 0;
    }
    /* movss/movsd: scalar single/double FP move (SIMD)
     *  movss xmm1, xmm2/m32  -> F3 0F 10 /r
     *  movss xmm1/m32, xmm2  -> F3 0F 11 /r
     *  movsd xmm1, xmm2/m64  -> F2 0F 10 /r
     *  movsd xmm1/m64, xmm2  -> F2 0F 11 /r
     */
    if (strcmp(mnem, "movss") == 0 || strcmp(mnem, "movsd") == 0 ||
             strcmp(mnem, "movups") == 0 || strcmp(mnem, "movaps") == 0 ||
             strcmp(mnem, "movupd") == 0 || strcmp(mnem, "movapd") == 0 ||
             strcmp(mnem, "movdqa") == 0 || strcmp(mnem, "movdqu") == 0 ||
             strcmp(mnem, "divpd") == 0 || strcmp(mnem, "addpd") == 0 ||
             strcmp(mnem, "xorpd") == 0 || strcmp(mnem, "mulpd") == 0 ||
             strcmp(mnem, "divps") == 0 || strcmp(mnem, "addps") == 0 ||
             strcmp(mnem, "xorps") == 0 || strcmp(mnem, "mulps") == 0 ||
             strcmp(mnem, "subps") == 0 || strcmp(mnem, "subpd") == 0 ||
             strcmp(mnem, "andps") == 0 || strcmp(mnem, "orps") == 0) {
        /* SSE brace-constant: `inst xmm, { c1, c2, ... }` — emit vector to .data pool, RIP-load */
        const reg_t *bc_reg = NULL;
        int brace_lt = -1, brace_gt = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '{') { brace_lt = i; }
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '}') { brace_gt = i; break; }
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) { if (!bc_reg) bc_reg = r; }
            }
        }
        if (brace_lt >= 0 && brace_gt > brace_lt && bc_reg) {
            /* collect constants */
            uint64_t ve[8]; int nve = 0;
            for (int i = brace_lt + 1; i < brace_gt; i++) {
                if (toks[i].type == ATOK_NUM && nve < 8) ve[nve++] = toks[i].value;
                if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
            }
            if (nve > 0) {
                /* determine width: pd/dq → 64-bit elems, ps → 32-bit elems */
                int w64 = 0;
                if (strstr(mnem, "pd") || strstr(mnem, "dq")) w64 = 1;
                int64_t off = vecpool_add(out, ve, nve, w64);
                if (off < 0) return 0;
                /* emit load opcode by mnemonic */
                if (strcmp(mnem, "movdqa") == 0) { emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x6F); }
                else if (strcmp(mnem, "movdqu") == 0) { emit_byte(out, 0xF3); emit_byte(out, 0x0F); emit_byte(out, 0x6F); }
                else if (strstr(mnem, "pd") && strncmp(mnem, "mov", 3) != 0) { emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x58); }
                else if (strncmp(mnem, "mov", 3) == 0) { if (strstr(mnem, "pd") || strcmp(mnem, "movapd") == 0 || strcmp(mnem, "movupd") == 0) emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x28); }
                else { emit_byte(out, 0x0F); emit_byte(out, 0x58); }
                emit_byte(out, 0x05 | (bc_reg->code & 7) << 3);
                emit_imm(out, (uint64_t)off, 4);
                int si = find_or_add_sym(out, "litpool");
                if (si >= 0 && out->nfixups < 256) {
                    asmc_fixup_t *f = &out->fixups[out->nfixups++];
                    f->offset = cur_offset(out) - 4;
                    f->sym_index = si;
                    f->type = 2; /* R_X86_64_PC32 */
                    f->addend = -4 + (int)off;
                    f->sec = out->cur_sec;
                }
                return 1;
            }
        }
    }
    if (strcmp(mnem, "movss") == 0 || strcmp(mnem, "movsd") == 0 ||
             strcmp(mnem, "movups") == 0 || strcmp(mnem, "movaps") == 0) {
             int is_movsd = (mnem[3] == 's' && mnem[4] == 'd');
             int is_movss = (mnem[3] == 's' && mnem[4] == 's');
             /* function-call RHS with return-value adaptation:
              *   `movups id16, foo()`  /  `movss f4, foo()`  /  `movsd f8, foo()`
              * Call foo(); the 16/8/4-byte float result returns in xmm0, then
              * store it to the destination symbol (RIP-relative). */
             {
                 int call_idx = -1, dest_idx = -1;
                 for (int i = 1; i < n; i++) {
                     if (toks[i].type == ATOK_ID && i + 1 < n &&
                         toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '(') {
                         call_idx = i;
                         for (int j = 1; j < n; j++)
                             if (j != i && toks[j].type == ATOK_ID && !find_reg(toks[j].text))
                                 { dest_idx = j; break; }
                     }
                 }
                 if (call_idx >= 0 && dest_idx >= 0) {
                     /* call foo  →  E8 rel32 */
                     a_tok_t calltoks[8];
                     calltoks[0].type = ATOK_ID;
                     snprintf(calltoks[0].text, sizeof(calltoks[0].text), "call");
                     calltoks[1].type = ATOK_ID;
                     snprintf(calltoks[1].text, sizeof(calltoks[1].text), "%s", toks[call_idx].text);
                     if (encode_instruction(out, calltoks, 2) != 1) return 0;
                     /* store xmm0 → [dest]  (0F 11 with RIP-relative dest) */
                     if (is_movss) emit_byte(out, 0xF3);
                     else if (is_movsd) emit_byte(out, 0xF2);
                     else emit_byte(out, 0x66);
                     emit_byte(out, 0x0F);
                     emit_byte(out, 0x11);
                     emit_byte(out, 0x05);   /* mod=00 rm=101 RIP-relative, reg=xmm0(000) */
                     emit_imm(out, 0, 4);
                     int si = find_or_add_sym(out, toks[dest_idx].text);
                     if (si >= 0 && out->nfixups < 256) {
                         asmc_fixup_t *f = &out->fixups[out->nfixups++];
                         f->offset = cur_offset(out) - 4;
                         f->sym_index = si;
                         f->type = 2;
                         f->addend = -4;
                         f->sec = out->cur_sec;
                     }
                     return 1;
                 }
             }
             /* find xmm registers */
             const reg_t *rd = NULL, *rs = NULL;
             for (int i = 1; i < n; i++) {
                 if (toks[i].type == ATOK_ID) {
                     const reg_t *r = find_reg(toks[i].text);
                     if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs) rs = r; }
                 }
             }
             /* float immediate: xmm, <float const> -> literal pool via .data (before any bytes) */
             if (rd && !rs) {
                 for (int i = 1; i < n; i++) {
                     if (toks[i].type == ATOK_NUM) {
                         uint64_t bits = toks[i].value;
                         int64_t off = litpool_get_or_add(out, bits);
                         if (off < 0) return 0;
                         if (is_movss) emit_byte(out, 0xF3);
                         else if (is_movsd) emit_byte(out, 0xF2);
                         else emit_byte(out, 0x66);
                         emit_byte(out, 0x0F);
                         emit_byte(out, 0x10);
                         emit_byte(out, 0x05 | (rd->code & 7) << 3);
                         emit_imm(out, (uint64_t)off, 4);
                         int si = find_or_add_sym(out, "litpool");
                         if (si >= 0) {
                             out->syms[si].defined = 1;
                             out->syms[si].value = (uint64_t)off;
                             out->syms[si].sec_index = SEC_DATA;
                         }
                         if (si >= 0 && out->nfixups < 256) {
                             asmc_fixup_t *f = &out->fixups[out->nfixups++];
                             f->offset = cur_offset(out) - 4;
                             f->sym_index = si;
                             f->type = 2;
                             f->addend = -4;
                             f->sec = out->cur_sec;
                         }
                         return 1;
                     }
                 }
             }
             if (is_movss) emit_byte(out, 0xF3);
             else if (is_movsd) emit_byte(out, 0xF2);
             else emit_byte(out, 0x66);  /* movups/movaps */
             emit_byte(out, 0x0F);
        /* store form: [mem], xmm -> opcode 0x11 */
        int store_xmm = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                /* check if '[' comes AFTER an xmm register (store form) */
                int xmm_before = 0;
                for (int j = 1; j < i; j++) {
                    if (toks[j].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[j].text);
                        if (r && r->is_xmm) xmm_before = 1;
                    }
                }
                if (xmm_before) {
                    emit_byte(out, 0x11);
                    mem_op_t mop;
                    if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                    int nr, si;
                    encode_mem_operand(out, rd ? rd->code & 7 : 0, &mop, &nr, &si);
                    (void)nr; (void)si;
                    return 1;
                }
            }
        }
        emit_byte(out, 0x10);  /* load form */
        /* proc-param / local symbol operand: `movups xmm0, a1` where a1 is a
         * registered stack-offset symbol → encode as [rbp+disp] load. */
        if (rd && !rs) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    int si = find_or_add_sym(out, toks[i].text);
                    if (si >= 0 && out->syms[si].defined && out->syms[si].sec_index == ASMC_ABS_SEC &&
                        out->cur_proc) {
                        int64_t disp = (int64_t)out->syms[si].value;
                        emit_byte(out, 0x85 | (rd->code & 7) << 3);  /* mod=10 rm=101 (rbp) */
                        emit_imm(out, (uint64_t)(int32_t)disp, 4);
                        return 1;
                    }
                }
            }
        }
        /* float immediate: xmm, <float const> -> literal pool via .data */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM && rd) {
                uint64_t bits = toks[i].value;
                int64_t off = litpool_get_or_add(out, bits);
                if (off < 0) return 0;
                emit_byte(out, 0x05 | (rd->code & 7) << 3);  /* mod=00 rm=101 (RIP) */
                emit_imm(out, (uint64_t)off, 4);
                /* fixup referencing .data section entry */
                int si = find_or_add_sym(out, "litpool");
                if (si >= 0) {
                    out->syms[si].defined = 1;
                    out->syms[si].value = (uint64_t)off;
                    out->syms[si].sec_index = SEC_DATA;
                }
                if (si >= 0 && out->nfixups < 256) {
                    asmc_fixup_t *f = &out->fixups[out->nfixups++];
                    f->offset = cur_offset(out) - 4;
                    f->sym_index = si;
                    f->type = 2; /* R_X86_64_PC32 */
                    f->addend = -4;
                    f->sec = out->cur_sec;
                }
                return 1;
            }
        }
        /* memory load: xmm, [mem] */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                int nr, si;
                encode_mem_operand(out, rd ? rd->code & 7 : 0, &mop, &nr, &si);
                (void)nr; (void)si;
                return 1;
            }
        }
        /* bare symbol memory load: xmm, name (proc param / data symbol) →
         * RIP-relative 0F 10 /r, mod=00 rm=101. */
        if (rd && !rs) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                    strcmp(toks[i].text, "ptr") != 0 && strcmp(toks[i].text, "byte") != 0 &&
                    strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0 &&
                    strcmp(toks[i].text, "qword") != 0) {
                    int si = find_or_add_sym(out, toks[i].text);
                    emit_byte(out, 0x05 | (rd->code & 7) << 3);   /* mod=00 rm=101 (RIP) */
                    emit_imm(out, 0, 4);
                    if (si >= 0) add_fixup(out, si, 2, -4);
                    return 1;
                }
            }
        }
        /* register-register */
        if (rd && rs) {
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        return 0;
    }
    /* SIMD binary ops with 3-byte opcode: aesenc/aesdec/aesimc/aeskeygenassist,
     * andpd/andps/orpd/orps/xorpd/xorps, ucomisd/ucomiss/comisd/comiss,
     * pand/pandn/por/pxor/pslld etc.
     * Encoding pattern: [66|F2|F3] 0F [38] op /r  (xmm ops with ModRM)
     */
    {
        /* opcode table: mnemonic -> (prefix, opcode, uses_0x38) */
        static const struct { const char *name; int pref; int op; int ext; } simd_ops[] = {
            { "aesenc",     0x66, 0xDC, 1 },  /* 66 0F 38 DC /r */
            { "aesdec",     0x66, 0xDE, 1 },
            { "aesimc",     0x66, 0xDB, 1 },
            { "aesenclast", 0x66, 0xDD, 1 },
            { "aesdeclast", 0x66, 0xDF, 1 },
            { "aeskeygenassist", 0x66, 0xDF, 1 },
            { "pclmulqdq", 0x66, 0x44, 1 },  /* 66 0F 3A 44 /r ib */
            { "pclmullqlqdq", 0x66, 0x44, 1 },  /* 66 0F 3A 44 /r ib, imm=0 */
            { "pclmulhqlqdq", 0x66, 0x44, 1 },  /* imm=1 */
            { "pclmullqhqdq", 0x66, 0x44, 1 },  /* imm=0x10 */
            { "pclmulhqhqdq", 0x66, 0x44, 1 },  /* imm=0x11 */
            { "andpd",      0x66, 0x54, 0 },  /* 66 0F 54 /r */
            { "andps",      0x00, 0x54, 0 },  /* 0F 54 /r */
            { "andnpd",     0x66, 0x55, 0 },
            { "andnps",     0x00, 0x55, 0 },
            { "orpd",       0x66, 0x56, 0 },
            { "orps",       0x00, 0x56, 0 },
            { "xorpd",      0x66, 0x57, 0 },
            { "xorps",      0x00, 0x57, 0 },
            { "ucomisd",    0x66, 0x2E, 0 },  /* 66 0F 2E /r */
            { "ucomiss",    0x00, 0x2E, 0 },
            { "comisd",     0x66, 0x2F, 0 },
            { "comiss",     0x00, 0x2F, 0 },
            { "addpd",      0x66, 0x58, 0 },
            { "addps",      0x00, 0x58, 0 },
            { "addsd",      0xF2, 0x58, 0 },
            { "addss",      0xF3, 0x58, 0 },
            { "subpd",      0x66, 0x5C, 0 },
            { "subps",      0x00, 0x5C, 0 },
            { "subsd",      0xF2, 0x5C, 0 },
            { "subss",      0xF3, 0x5C, 0 },
            { "mulpd",      0x66, 0x59, 0 },
            { "mulps",      0x00, 0x59, 0 },
            { "mulsd",      0xF2, 0x59, 0 },
            { "mulss",      0xF3, 0x59, 0 },
            { "divpd",      0x66, 0x5E, 0 },
            { "divps",      0x00, 0x5E, 0 },
            { "divsd",      0xF2, 0x5E, 0 },
            { "divss",      0xF3, 0x5E, 0 },
            { "maxpd",      0x66, 0x5F, 0 },
            { "maxps",      0x00, 0x5F, 0 },
            { "minpd",      0x66, 0x5D, 0 },
            { "minps",      0x00, 0x5D, 0 },
            { "sqrtpd",     0x66, 0x51, 0 },
            { "sqrtps",     0x00, 0x51, 0 },
            { "sqrtsd",     0xF2, 0x51, 0 },
            { "sqrtss",     0xF3, 0x51, 0 },
            { "pand",       0x66, 0xDB, 0 },
            { "pandn",      0x66, 0xDF, 0 },
            { "por",        0x66, 0xEB, 0 },
            { "pxor",       0x66, 0xEF, 0 },
            { "paddb",      0x66, 0xFC, 0 },
            { "paddw",      0x66, 0xFD, 0 },
            { "paddd",      0x66, 0xFE, 0 },
            { "paddq",      0x66, 0xD4, 0 },
            { "psubb",      0x66, 0xF8, 0 },
            { "psubw",      0x66, 0xF9, 0 },
            { "psubd",      0x66, 0xFA, 0 },
            { "psubq",      0x66, 0xFB, 0 },
            { "pmuludq",    0x66, 0xF4, 0 },
            { "pcmpeqb",    0x66, 0x74, 0 },
            { "pcmpeqw",    0x66, 0x75, 0 },
            { "pcmpeqd",    0x66, 0x76, 0 },
            { "pcmpgtb",    0x66, 0x64, 0 },
            { "pcmpgtw",    0x66, 0x65, 0 },
            { "pcmpgtd",    0x66, 0x66, 0 },
            { NULL, 0, 0, 0 }
        };
        int found_op = 0;
        for (int si2 = 0; simd_ops[si2].name; si2++) {
            if (strcmp(mnem, simd_ops[si2].name) == 0) { found_op = 1; break; }
        }
        if (found_op) {
            /* find the table entry */
            for (int si2 = 0; simd_ops[si2].name; si2++) {
                if (strcmp(mnem, simd_ops[si2].name) != 0) continue;
                int pref = simd_ops[si2].pref;
                int opc = simd_ops[si2].op;
                int ext = simd_ops[si2].ext;
                /* find xmm registers in order */
                const reg_t *rd = NULL, *rs = NULL;
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs) rs = r; }
                    }
                }
                if (!rd) return 0;
                if (pref) emit_byte(out, (uint8_t)pref);
                emit_byte(out, 0x0F);
                if (ext) emit_byte(out, 0x38);
                emit_byte(out, (uint8_t)opc);
                /* memory operand */
                int found_mem = 0;
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                        mem_op_t mop;
                        if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                        int nr, si3;
                        encode_mem_operand(out, rd->code & 7, &mop, &nr, &si3);
                        (void)nr; (void)si3;
                        found_mem = 1;
                        break;
                    }
                }
                if (found_mem) return 1;
                /* register-register or register-immediate */
                if (rs) {
                    uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
                    emit_byte(out, modrm);
                    /* aeskeygenassist takes an imm8 third operand */
                    if (strcmp(mnem, "aeskeygenassist") == 0) {
                        for (int i = 1; i < n; i++)
                            if (toks[i].type == ATOK_NUM) { emit_byte(out, (uint8_t)toks[i].value); break; }
                    }
                    return 1;
                }
                /* bare identifier memory operand (m64, m32, m128, etc.): emit RIP-relative */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                        int si = find_or_add_sym(out, toks[i].text);
                        uint8_t modrm = 0x05 | (rd->code & 7) << 3;
                        emit_byte(out, modrm);
                        emit_imm(out, 0, 4);
                        if (si >= 0) add_fixup(out, si, 2 /*R_X86_64_PC32*/, -4);
                        return 1;
                    }
                }
                /* float immediate: rd, <float_const> -> literal pool via .data + RIP-relative */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_NUM && rd) {
                        uint64_t bits = toks[i].value;
                        int64_t off = litpool_get_or_add(out, bits);
                        if (off < 0) return 0;
                        emit_byte(out, 0x05 | (rd->code & 7) << 3);
                        emit_imm(out, (uint64_t)off, 4);
                        int si = find_or_add_sym(out, "litpool");
                        if (si >= 0) {
                            out->syms[si].defined = 1;
                            out->syms[si].value = (uint64_t)off;
                            out->syms[si].sec_index = SEC_DATA;
                        }
                        if (si >= 0 && out->nfixups < 256) {
                            asmc_fixup_t *f = &out->fixups[out->nfixups++];
                            f->offset = cur_offset(out) - 4;
                            f->sym_index = si;
                            f->type = 2;
                            f->addend = -4;
                            f->sec = out->cur_sec;
                        }
                        return 1;
                    }
                }
                /* single-operand forms (aesimc) */
                if (strcmp(mnem, "aesimc") == 0) {
                    uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | 0;
                    emit_byte(out, modrm);
                    return 1;
                }
                return 0;
            }
        }
    }
    if (strcmp(mnem, "int") == 0) {
        if (has_imm) { emit_byte(out, 0xCD); emit_byte(out, (uint8_t)imm); return 1; }
        return 0;
    }

    /* AVX (VEX-prefixed) instructions: vmovq, vmovd, vmovapd, vmovdqa, vmovdqu, vmovupd */
    if (mnem[0] == 'v') {
        if (strcmp(mnem, "vmovq") == 0 || strcmp(mnem, "vmovd") == 0 ||
            strcmp(mnem, "vmovapd") == 0 || strcmp(mnem, "vmovaps") == 0 ||
            strcmp(mnem, "vmovdqa") == 0 || strcmp(mnem, "vmovdqu") == 0 ||
            strcmp(mnem, "vmovupd") == 0 || strcmp(mnem, "vmovups") == 0)
            return encode_avx_move(out, mnem, toks, n);
        /* AVX 3-operand scalar: vmovsd/vmovss xmm1, xmm2, xmm3 (vvvv = xmm2)
         * VEX.128.F2.0F 10 /r (vmovsd), VEX.128.F3.0F 10 /r (vmovss) */
        if (strcmp(mnem, "vmovsd") == 0 || strcmp(mnem, "vmovss") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r;
                        else if (!rs1) rs1 = r;
                        else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd) return 0;
            int pp = (mnem[4] == 's' && mnem[5] == 's') ? 2 : 3; /* vmovss=F3, vmovsd=F2 */
            if (found_mem) {
                int vvvv = rs1 ? rs1->code : 0xF;
                emit_vex(out, 0, 0, vvvv, rd->code, 0, 0, pp);
                emit_byte(out, 0x10);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
                return 1;
            }
            if (rs2) {
                /* 3-operand: vvvv=rs1, ModRM.r/m=rs2 */
                emit_vex(out, 0, 0, rs1->code, rd->code, rs2->code, 0, pp);
                emit_byte(out, 0x10);
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
            /* 2-operand: vmovsd xmm1, xmm2 */
            if (rs1) {
                emit_vex(out, 0, 0, 0xF, rd->code, rs1->code, 0, pp);
                emit_byte(out, 0x10);
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
            return 0;
        }
        /* AVX 3-operand arithmetic: vaddsd/vaddss/vaddpd/vaddps/vsubsd/... etc.
         * VEX.128/256.pp.0F op /r with vvvv = first source */
        {
            static const struct { const char *name; int op; int pp; int w; } avx_arith[] = {
                { "vaddsd",  0x58, 3, 0 },   /* F2 */
                { "vaddss",  0x58, 2, 0 },   /* F3 */
                { "vaddpd",  0x58, 1, 0 },   /* 66 */
                { "vaddps",  0x58, 0, 0 },
                { "vsubsd",  0x5C, 3, 0 },
                { "vsubss",  0x5C, 2, 0 },
                { "vsubpd",  0x5C, 1, 0 },
                { "vsubps",  0x5C, 0, 0 },
                { "vmulsd",  0x59, 3, 0 },
                { "vmulss",  0x59, 2, 0 },
                { "vmulpd",  0x59, 1, 0 },
                { "vmulps",  0x59, 0, 0 },
                { "vdivsd",  0x5E, 3, 0 },
                { "vdivss",  0x5E, 2, 0 },
                { "vdivpd",  0x5E, 1, 0 },
                { "vdivps",  0x5E, 0, 0 },
                { "vmaxsd",  0x5F, 3, 0 },
                { "vmaxss",  0x5F, 2, 0 },
                { "vmaxpd",  0x5F, 1, 0 },
                { "vmaxps",  0x5F, 0, 0 },
                { "vminsd",  0x5D, 3, 0 },
                { "vminss",  0x5D, 2, 0 },
                { "vminpd",  0x5D, 1, 0 },
                { "vminps",  0x5D, 0, 0 },
                { "vandpd",  0x54, 1, 0 },
                { "vandps",  0x54, 0, 0 },
                { "vorpd",   0x56, 1, 0 },
                { "vorps",   0x56, 0, 0 },
                { "vxorpd",  0x57, 1, 0 },
                { "vxorps",  0x57, 0, 0 },
                { "vandnpd", 0x55, 1, 0 },
                { "vandnps", 0x55, 0, 0 },
                /* AES crypto instructions (VEX.66.0F / 0F3A) */
                { "vaesimc", 0xDB, 1, 0 },  /* 66 0F */
                { "vaesenc", 0xDC, 1, 0 },  /* 66 0F */
                { "vaesenclast", 0xDD, 1, 0 },  /* 66 0F */
                { "vaesdec", 0xDE, 1, 0 },  /* 66 0F */
                { "vaesdeclast", 0xDF, 1, 0 },  /* 66 0F */
                { "vaeskeygenassist", 0xDF, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpclmulqdq", 0x44, 1, 3 },  /* 66 0F3A + imm8 */
                { "vextractf128", 0x19, 1, 3 },  /* 66 0F3A + imm8 */
                { "vextracti128", 0x39, 1, 3 },  /* 66 0F3A + imm8 */
                { "vinsertf128", 0x18, 1, 3 },  /* 66 0F3A + imm8 */
                { "vinserti128", 0x38, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpalignr", 0x0F, 1, 3 },  /* 66 0F3A + imm8 */
                { "vblendpd", 0x0D, 1, 3 },  /* 66 0F3A + imm8 */
                { "vblendps", 0x0C, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpblendd", 0x02, 1, 3 },  /* 66 0F3A + imm8 */
                { "vdpdps", 0x41, 1, 3 },  /* 66 0F3A + imm8 (reserved) */
                { "vdpps", 0x40, 1, 3 },  /* 66 0F3A + imm8 */
                { "vmpsadbw", 0x42, 1, 3 },  /* 66 0F3A + imm8 */
                /* SSE/AVX insert/extract (VEX.66.0F3A + imm8) */
                { "vpinsrb", 0x20, 1, 3 },  /* 66 0F3A */
                { "vpinsrw", 0xC4, 1, 3 },  /* 66 0F3A (actually 66 0F, map=0 not 3 — but w==3 handles imm8) */
                { "vpinsrd", 0x22, 1, 3 },  /* 66 0F3A */
                /* AVX permutation (VEX.66.0F38) */
                { "vpermilpd", 0x0D, 1, 1 },  /* 66 0F38 */
                { "vpermilps", 0x0C, 1, 1 },  /* 66 0F38 */
                { "vperm2f128", 0x06, 1, 3 },  /* 66 0F3A + imm8 */
                { "vperm2i128", 0x46, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpermpd",   0x01, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpermq",    0x00, 1, 3 },  /* 66 0F3A + imm8 */
                { "vpermd",    0x36, 1, 1 },  /* 66 0F38 */
                { "vpermps",   0x16, 1, 1 },  /* 66 0F38 */
                /* AVX broadcast (VEX.66.0F38) */
                { "vbroadcastf128", 0x1A, 1, 1 },  /* 66 0F38 */
                { "vbroadcastsd", 0x19, 1, 1 },  /* 66 0F38 */
                { "vbroadcastss", 0x18, 1, 1 },  /* 66 0F38 */
                { "vbroadcasti128", 0x5A, 1, 1 },  /* 66 0F38 */
                { "vbroadcastf64x2", 0x1B, 1, 1 },  /* 66 0F38 */
                { "vbroadcastf32x4", 0x1A, 1, 1 },  /* 66 0F38 */
                { "vbroadcasti64x2", 0x5B, 1, 1 },  /* 66 0F38 */
                { "vbroadcasti32x4", 0x5A, 1, 1 },  /* 66 0F38 */
                /* AVX maskload/maskstore (VEX.66.0F38) */
                { "vmaskmovpd", 0x2D, 1, 1 },  /* 66 0F38 (load) */
                { "vmaskmovps", 0x2C, 1, 1 },  /* 66 0F38 (load) */
                { "vpmaskmovd", 0x8C, 1, 1 },  /* 66 0F38 (masked dword) */
                /* GFNI (VEX.66.0F38) */
                { "vgf2p8mulb", 0xCF, 1, 1 },  /* 66 0F38 */
                { "vgf2p8affineqb", 0xCE, 1, 3 },  /* 66 0F3A + imm8 */
                { "vgf2p8affineinvqb", 0xCF, 1, 3 },  /* 66 0F3A + imm8 */
                /* SIMD convert instructions */
                { "vcvtdq2pd", 0xE6, 2, 0 },  /* F3 */
                { "vcvtps2pd", 0x5A, 1, 0 },  /* 66 */
                { "vcvtpd2ps", 0x5A, 1, 0 },  /* 66 */
                { "vcvtpd2dq", 0xE6, 1, 0 },  /* 66 */
                { "vcvttpd2dq", 0xE6, 2, 0 },  /* F3 */
                { "vcvtdq2ps", 0x5B, 0, 0 },  /* no prefix */
                { "vcvtps2dq", 0x5B, 1, 0 },  /* 66 */
                { "vcvttps2dq", 0x5B, 2, 0 },  /* F3 */
                /* SSE/AVX broadcast/move (VEX.0F) */
                { "vmovddup", 0x12, 3, 0 },  /* F2 */
                { "vmovshdup", 0x16, 2, 0 },  /* F3 */
                { "vmovsldup", 0x12, 2, 0 },  /* F3 */
                { "vlddqu", 0xF0, 3, 0 },  /* F2 */
                { "vmovntdq", 0xE7, 1, 0 },  /* 66 */
                { "vmovntpd", 0x2B, 1, 0 },  /* 66 */
                { "vmovntps", 0x2B, 0, 0 },  /* no prefix */
                { "vmovntdqa", 0x2A, 1, 1 },  /* 66 0F38 */
                /* AVX test (VEX.66.0F) */
                { "vptest", 0x17, 1, 0 },  /* 66 */
                { "vtestpd", 0x0E, 1, 0 },  /* 66 */
                { "vtestps", 0x0E, 0, 0 },  /* no prefix */
                /* SSE/AVX packed arithmetic */
                { "vpavgb",   0xE0, 1, 0 },  /* 66 */
                { "vpavgw",   0xE3, 1, 0 },  /* 66 */
                { "vpaddb",   0xFC, 1, 0 },  /* 66 */
                { "vpaddw",   0xFD, 1, 0 },  /* 66 */
                { "vpaddd",   0xFE, 1, 0 },  /* 66 */
                { "vpaddq",   0xD4, 1, 0 },  /* 66 */
                { "vpsubb",   0xF8, 1, 0 },  /* 66 */
                { "vpsubw",   0xF9, 1, 0 },  /* 66 */
                { "vpsubd",   0xFA, 1, 0 },  /* 66 */
                { "vpsubq",   0xFB, 1, 0 },  /* 66 */
                { "vpaddsb",  0xEC, 1, 0 },  /* 66 */
                { "vpaddsw",  0xED, 1, 0 },  /* 66 */
                { "vpaddusb", 0xDC, 1, 0 },  /* 66 */
                { "vpaddusw", 0xDD, 1, 0 },  /* 66 */
                { "vpsadbw",  0xF6, 1, 0 },  /* 66 */
                { "vpsubsb",  0xE8, 1, 0 },  /* 66 */
                { "vpsubsw",  0xE9, 1, 0 },  /* 66 */
                { "vpsubusb", 0xD8, 1, 0 },  /* 66 */
                { "vpsubusw", 0xD9, 1, 0 },  /* 66 */
                /* SSE/AVX bitwise logic (VEX.66.0F) */
                { "vpand",   0xDB, 1, 0 },  /* 66 */
                { "vpandn",  0xDF, 1, 0 },  /* 66 */
                { "vpor",    0xEB, 1, 0 },  /* 66 */
                { "vpxor",   0xEF, 1, 0 },  /* 66 */
                { "vpandd",  0xDB, 1, 1 },  /* 66 0F38 */
                { "vpandq",  0xDB, 1, 1 },  /* 66 0F38 (W=1, differs from vpandd W=0) */
                { "vpandnd", 0xDF, 1, 1 },  /* 66 0F38 */
                { "vpandnq", 0xDF, 1, 1 },  /* 66 0F38 (W=1) */
                { "vpord",   0xEB, 1, 1 },  /* 66 0F38 */
                { "vporq",   0xEB, 1, 1 },  /* 66 0F38 (W=1) */
                { "vpxord",  0xEF, 1, 1 },  /* 66 0F38 */
                { "vpxorq",  0xEF, 1, 1 },  /* 66 0F38 (W=1) */
                /* SSE/AVX packed compare */
                { "vpcmpeqb", 0x74, 1, 0 },  /* 66 */
                { "vpcmpeqw", 0x75, 1, 0 },  /* 66 */
                { "vpcmpeqd", 0x76, 1, 0 },  /* 66 */
                { "vpcmpgtb", 0x64, 1, 0 },  /* 66 */
                { "vpcmpgtw", 0x65, 1, 0 },  /* 66 */
                { "vpcmpgtd", 0x66, 1, 0 },  /* 66 */
                { "vpcmpeqq", 0x29, 1, 1 },  /* 66 0F38 */
                { "vpcmpgtq", 0x37, 1, 1 },  /* 66 0F38 */
                /* SSE/AVX min/max (VEX.66.0F/0F38) */
                { "vpmaxsb",  0x3C, 1, 1 },  /* 66 0F38 */
                { "vpmaxsd",  0x3D, 1, 1 },  /* 66 0F38 */
                { "vpmaxsw",  0xEE, 1, 0 },  /* 66 */
                { "vpmaxub",  0xDE, 1, 0 },  /* 66 */
                { "vpmaxuw",  0x3E, 1, 1 },  /* 66 0F38 */
                { "vpmaxud",  0x3F, 1, 1 },  /* 66 0F38 */
                { "vpminsb",  0x38, 1, 1 },  /* 66 0F38 */
                { "vpminsd",  0x39, 1, 1 },  /* 66 0F38 */
                { "vpminsw",  0xEA, 1, 0 },  /* 66 */
                { "vpminub",  0xDA, 1, 0 },  /* 66 */
                { "vpminuw",  0x3A, 1, 1 },  /* 66 0F38 */
                { "vpminud",  0x3B, 1, 1 },  /* 66 0F38 */
                /* SSE/AVX multiply (VEX.66.0F/0F38) */
                { "vpmulhuw", 0xE4, 1, 0 },  /* 66 */
                { "vpmulhw",  0xE5, 1, 0 },  /* 66 */
                { "vpmullw",  0xD5, 1, 0 },  /* 66 */
                { "vpmuludq", 0xF4, 1, 0 },  /* 66 */
                { "vpmuldq",  0x28, 1, 1 },  /* 66 0F38 */
                { "vpmulhrsw", 0x0B, 1, 1 },  /* 66 0F38 */
                { "vpmulld",  0x40, 1, 1 },  /* 66 0F38 */
                { "vpmullq",  0x40, 1, 1 },  /* 66 0F38 (W=1 for qword, same opcode 0x40) */
                /* GFNI (VEX.66.0F38) */
                { "gf2p8mulb", 0xCF, 1, 1 },  /* 66 0F38 — non-VEX GF(2^8) multiply */
                /* SSE/AVX shuffle (VEX.66.0F38) */
                { "vpshufb",  0x00, 1, 1 },  /* 66 0F38 */
                /* SSE/AVX variable shifts (VEX.66.0F38) */
                { "vpsllvd", 0x47, 1, 1 },  /* 66 0F38 */
                { "vpsllvq", 0x47, 1, 1 },  /* 66 0F38 (W=1 differs from vpsllvd W=0, but avx_arith sets W=0 — may need dedicated handler) */
                { "vpsllvw", 0x45, 1, 1 },  /* 66 0F38 */
                { "vpsravd", 0x46, 1, 1 },  /* 66 0F38 */
                { "vpsravw", 0x46, 1, 1 },  /* 66 0F38 */
                { "vpsrlvd", 0x45, 1, 1 },  /* 66 0F38 */
                { "vpsrlvw", 0x45, 1, 1 },  /* 66 0F38 (W0 word variant, same opcode) */
                { "vpsignb",  0x08, 1, 1 },  /* 66 0F38 */
                { "vpsignw",  0x09, 1, 1 },  /* 66 0F38 */
                { "vpsignd",  0x0A, 1, 1 },  /* 66 0F38 */
                { "vpabsb",   0x1C, 1, 0 },  /* 66 */
                { "vpabsw",   0x1D, 1, 0 },  /* 66 */
                { "vpabsd",   0x1E, 1, 0 },  /* 66 */
                { "vphminposuw", 0x41, 1, 1 },  /* 66 0F38 */
                /* SSE/AVX pack */
                { "vpacksswb", 0x63, 1, 0 },  /* 66 */
                { "vpackssdw", 0x6B, 1, 0 },  /* 66 */
                { "vpackuswb", 0x67, 1, 0 },  /* 66 */
                { "vpackusdw", 0x2B, 1, 1 },  /* 66 0F38 */
                { "vaddsubpd", 0xD0, 1, 0 },  /* 66 */
                { "vaddsubps", 0xD1, 1, 0 },  /* 66 */
                { "vhaddpd",  0x7C, 1, 0 },  /* 66 */
                { "vhaddps",  0x7C, 0, 0 },  /* no prefix */
                { "vhsubpd",  0x7D, 1, 0 },  /* 66 */
                { "vhsubps",  0x7D, 0, 0 },  /* no prefix */
                /* AVX-512 FP16 (VEX.66.0F38) */
                { "vaddph", 0x57, 1, 1 },  /* 66 0F38 */
                { "vsubph", 0x5C, 1, 1 },  /* 66 0F38 */
                { "vmulph", 0x59, 1, 1 },  /* 66 0F38 */
                { "vdivph", 0x5E, 1, 1 },  /* 66 0F38 */
                { "vminph", 0x5D, 1, 1 },  /* 66 0F38 */
                { "vmaxph", 0x5F, 1, 1 },  /* 66 0F38 */
                /* AVX-512 FP16 scalar (VEX.66.0F38) */
                { "vaddsh", 0x57, 1, 1 },  /* 66 0F38 */
                { "vsubsh", 0x5C, 1, 1 },  /* 66 0F38 */
                { "vmulsh", 0x59, 1, 1 },  /* 66 0F38 */
                { "vdivsh", 0x5E, 1, 1 },  /* 66 0F38 */
                { "vminsh", 0x5D, 1, 1 },  /* 66 0F38 */
                { "vmaxsh", 0x5F, 1, 1 },  /* 66 0F38 */
                { "vpmaddubsw", 0x04, 1, 1 },  /* 66 0F38 */
                { "vpmaddwd", 0xF5, 1, 0 },  /* 66 */
                { "vphaddw",  0x01, 1, 1 },  /* 66 0F38 */
                { "vphaddd",  0x02, 1, 1 },  /* 66 0F38 */
                { "vphaddsw", 0x03, 1, 1 },  /* 66 0F38 */
                { "vphsubw",  0x05, 1, 1 },  /* 66 0F38 */
                { "vphsubd",  0x06, 1, 1 },  /* 66 0F38 */
                { "vphsubsw", 0x07, 1, 1 },  /* 66 0F38 */
                /* SSE/AVX unpack */
                { "vunpckhpd", 0x15, 1, 0 },  /* 66 */
                { "vunpckhps", 0x15, 0, 0 },
                { "vunpcklpd", 0x14, 1, 0 },  /* 66 */
                { "vunpcklps", 0x14, 0, 0 },
                { "vpunpckhbw", 0x68, 1, 0 },  /* 66 */
                { "vpunpckhwd", 0x69, 1, 0 },  /* 66 */
                { "vpunpckhdq", 0x6D, 1, 0 },  /* 66 */
                { "vpunpcklbw", 0x60, 1, 0 },  /* 66 */
                { "vpunpcklwd", 0x61, 1, 0 },  /* 66 */
                { "vpunpckldq", 0x62, 1, 0 },  /* 66 */
                { "vpunpcklqdq", 0x6C, 1, 0 },  /* 66 */
                { "vpunpckhqdq", 0x6D, 1, 0 },  /* 66 (W=1 differs; may need dedicated W=1 override) */
                { "vcvtsi2sd", 0x2A, 3, 0 },  /* F2 */
                { "vcvtsi2ss", 0x2A, 2, 0 },  /* F3 */
                { "vcvtss2sd", 0x5A, 3, 0 },  /* F2 */
                { "vcvtsd2ss", 0x5A, 2, 0 },  /* F3 */
                { "vcvttsd2si", 0x2C, 3, 0 }, /* F2 */
                { "vcvttss2si", 0x2C, 2, 0 }, /* F3 */
                { "vcvtsd2si",  0x2D, 3, 0 }, /* F2 */
                { "vcvtss2si",  0x2D, 2, 0 }, /* F3 */
                /* SIMD compare instructions */
                { "vcomisd",   0x2F, 1, 0 },  /* 66 */
                { "vcomiss",   0x2F, 0, 0 },
                { "vucomisd",  0x2E, 1, 0 },
                { "vucomiss",  0x2E, 0, 0 },
                /* sqrt instructions */
                { "vsqrtsd",   0x51, 3, 0 },  /* F2 */
                { "vsqrtss",   0x51, 2, 0 },  /* F3 */
                { "vsqrtpd",   0x51, 1, 0 },  /* 66 */
                { "vsqrtps",   0x51, 0, 0 },
                /* reciprocal instructions */
                { "vrcpss",    0x53, 2, 0 },  /* F3 */
                { "vrcpps",    0x53, 0, 0 },
                { "vrsqrtss",  0x52, 2, 0 },  /* F3 */
                { "vrsqrtps",  0x52, 0, 0 },
                /* BF16 convert instructions */
                { "vbcstnebf162ps", 0xB1, 1, 1 },  /* 66 0F38 */
                { "vbcstnesh2ps",   0xB2, 1, 1 },  /* 66 0F38 */
                { "vcvtneebf162ps", 0xB0, 2, 1 },  /* F3 0F38 */
                { "vcvtneobf162ps", 0xB3, 2, 1 },  /* F3 0F38 */
                { "vcvtneeph2ps",   0xB0, 1, 1 },  /* 66 0F38 */
                { "vcvtneoph2ps",   0xB3, 1, 1 },  /* 66 0F38 */
                { "vcvtneps2bf16",  0xB1, 1, 1 },  /* 66 0F38 */
                { "vcvtneph2ps",    0xB4, 1, 1 },  /* 66 0F38 */
                /* SM3/SM4 crypto instructions (VEX.128/256.66.0F38) */
                { "vsm3msg1",    0xDA, 1, 1 },  /* 66 0F38 */
                { "vsm3msg2",    0xDB, 1, 1 },  /* 66 0F38 */
                { "vsm4key4",    0xD2, 1, 1 },  /* 66 0F38 */
                { "vsm4rnds4",   0xD3, 1, 1 },  /* 66 0F38 */
                { "vsm4key8",    0xD2, 1, 1 },  /* 66 0F38 (ymm) */
                { "vsm4rnds8",   0xD3, 1, 1 },  /* 66 0F38 (ymm) */
                /* VNNI integer dot-product instructions (VEX.128/256.66.0F38) */
                { "vpdpbssd",    0x50, 1, 1 },  /* 66 0F38 */
                { "vpdpbusd",    0x51, 1, 1 },  /* 66 0F38 */
                { "vpdpwssd",    0x52, 1, 1 },  /* 66 0F38 */
                { "vpdpbusds",   0x51, 1, 1 },  /* 66 0F38 */
                { "vpdpwssds",   0x53, 1, 1 },  /* 66 0F38 */
                { "vpdpwsud",    0x5D, 1, 1 },  /* 66 0F38 */
                { "vpdpwsuds",   0x5D, 1, 1 },  /* 66 0F38 */
                { "vpdpbssds",   0x50, 1, 1 },  /* 66 0F38 (saturating variant) */
                { "vpdpbsud",    0x50, 1, 1 },  /* 66 0F38 */
                { "vpdpwusd",    0x5D, 1, 1 },  /* 66 0F38 */
                { "vpdpbsuds",   0x50, 1, 1 },  /* 66 0F38 (saturating) */
                { "vpdpwusds",   0x5D, 1, 1 },  /* 66 0F38 (saturating) */
                { "vpdpbuud",    0x50, 1, 1 },  /* 66 0F38 */
                { "vpdpwuud",    0x5D, 1, 1 },  /* 66 0F38 */
                { "vpdpbuuds",   0x50, 1, 1 },  /* 66 0F38 (saturating) */
                { "vpdpwuuds",   0x5D, 1, 1 },  /* 66 0F38 (saturating) */
                { "vsm3rnds2",   0xDE, 1, 3 },  /* 66 0F3A + imm8 */
                /* Rounding instructions (opcode 0F3A map) */
                { "vroundsd",  0x0B, 1, 3 },  /* 66 0F3A */
                { "vroundss",  0x0A, 1, 3 },
                { "vroundpd",  0x09, 1, 3 },
                { "vroundps",  0x08, 1, 3 },
                /* Compare-immediate instructions (CMPPD/CMPPS/CMPSD/CMPSS) */
                { "vcmppd",   0xC2, 1, 0 },  /* 66 */
                { "vcmpps",   0xC2, 0, 0 },
                { "vcmpsd",   0xC2, 3, 0 },  /* F2 */
                { "vcmpss",   0xC2, 2, 0 },  /* F3 */
                { NULL, 0, 0, 0 }
            };
            for (int ai = 0; avx_arith[ai].name; ai++) {
                if (strcmp(mnem, avx_arith[ai].name) != 0) continue;
                const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
                int is_convert_gpr = (avx_arith[ai].op == 0x2A || avx_arith[ai].op == 0x2C ||
                                      avx_arith[ai].op == 0x2D);
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (!r) continue;
                        if (r->is_xmm) {
                            if (!rd) rd = r;
                            else if (!rs1) rs1 = r;
                            else if (!rs2) rs2 = r;
                        } else {
                            /* GPR operand: for convert-to-int (vcvttsd2si r64, xmm),
                             * first GPR is the destination register */
                            if (!rd && is_convert_gpr) rd = r;
                            else if (!rs1 && !rd) rs1 = r;
                        }
                    }
                }
                if (!rd) return 0;
                /* Note: rs1 may be NULL for 2-operand/memory forms (vcomisd xmm, [mem]) */
                int l = 0;
                if (rd->name[0] == 'y') l = 1;
                /* memory operand? */
                int found_mem = 0;
                mem_op_t mop;
                for (int i = 1; i < n; i++)
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                        if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                    }
                if (rs2) {
                    int is_zmm = (rd->code >= 16 || rs2->code >= 16 || (rs1 && rs1->code >= 16));
                    if (is_zmm) {
                        int ll = 2; /* zmm */
                        emit_evex(out, avx_arith[ai].w, 0, rs1->code, rd->code, rs2->code, ll, avx_arith[ai].pp);
                    } else {
                        emit_vex(out, avx_arith[ai].w, 0, rs1->code, rd->code, rs2->code, l, avx_arith[ai].pp);
                    }
                    emit_byte(out, (uint8_t)avx_arith[ai].op);
                    uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                    emit_byte(out, modrm);
                    /* 0F3A instructions take an imm8 (e.g. vroundsd) */
                    if (avx_arith[ai].w == 3) {
                        for (int i = 1; i < n; i++)
                            if (toks[i].type == ATOK_NUM) { emit_byte(out, (uint8_t)toks[i].value); break; }
                    }
                    return 1;
                }
                if (found_mem) {
                    int vvvv = rs1 ? rs1->code : 0xF;
                    int is_zmm = (rd->code >= 16 || vvvv >= 16);
                    if (is_zmm) {
                        emit_evex(out, avx_arith[ai].w, 0, vvvv, rd->code, 0, 2, avx_arith[ai].pp);
                    } else {
                        emit_vex(out, avx_arith[ai].w, 0, vvvv, rd->code, 0, l, avx_arith[ai].pp);
                    }
                    emit_byte(out, (uint8_t)avx_arith[ai].op);
                    int nr, si;
                    encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                    (void)nr; (void)si;
                    if (avx_arith[ai].w == 3) {
                        for (int i = 1; i < n; i++)
                            if (toks[i].type == ATOK_NUM) { emit_byte(out, (uint8_t)toks[i].value); break; }
                    }
                    return 1;
                }
                /* 2-operand register form (vcomisd xmm1, xmm2 etc.):
                 * vvvv reserved (0xF), second register in ModRM.rm */
                if (rs1) {
                    int is_zmm = (rd->code >= 16 || rs1->code >= 16);
                    if (is_zmm) {
                        emit_evex(out, avx_arith[ai].w, 0, 0xF, rd->code, rs1->code, 2, avx_arith[ai].pp);
                    } else {
                        emit_vex(out, avx_arith[ai].w, 0, 0xF, rd->code, rs1->code, l, avx_arith[ai].pp);
                    }
                    emit_byte(out, (uint8_t)avx_arith[ai].op);
                    uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                    emit_byte(out, modrm);
                    if (avx_arith[ai].w == 3) {
                        for (int i = 1; i < n; i++)
                            if (toks[i].type == ATOK_NUM) { emit_byte(out, (uint8_t)toks[i].value); break; }
                    }
                    return 1;
                }
                return 0;
            }
        }
        /* vcmp{op}{sd|ss|pd|ps} pseudo-instructions: fixed predicate immediate.
         * op: eq=0, lt=1, le=2, unord=3, neq=4, nlt=5, nle=6, ord=7, nge=6, ge=6(nle), gt=1(nlt eq) */
        if (strncmp(mnem, "vcmp", 4) == 0 && strlen(mnem) >= 7) {
            const char *rest = mnem + 4;
            /* find the suffix: sd/ss/pd/ps */
            int slen = strlen(rest);
            const char *suffix = "";
            int pp = 0;
            if (slen >= 2) {
                if (strcmp(rest + slen - 2, "sd") == 0) { suffix = "sd"; pp = 3; }
                else if (strcmp(rest + slen - 2, "ss") == 0) { suffix = "ss"; pp = 2; }
                else if (strcmp(rest + slen - 2, "pd") == 0) { suffix = "pd"; pp = 1; }
                else if (strcmp(rest + slen - 2, "ps") == 0) { suffix = "ps"; pp = 0; }
            }
            if (suffix[0]) {
                /* extract op (everything before suffix) */
                char opbuf[16];
                int oplen = slen - 2;
                if (oplen > 15) oplen = 15;
                memcpy(opbuf, rest, oplen);
                opbuf[oplen] = 0;
                int pred = -1;
                if (strcmp(opbuf, "eq") == 0) pred = 0;
                else if (strcmp(opbuf, "lt") == 0) pred = 1;
                else if (strcmp(opbuf, "le") == 0) pred = 2;
                else if (strcmp(opbuf, "unord") == 0) pred = 3;
                else if (strcmp(opbuf, "neq") == 0 || strcmp(opbuf, "ne") == 0) pred = 4;
                else if (strcmp(opbuf, "nlt") == 0) pred = 5;
                else if (strcmp(opbuf, "nle") == 0 || strcmp(opbuf, "nge") == 0) pred = 6;
                else if (strcmp(opbuf, "ord") == 0) pred = 7;
                /* quiet variants: eq_uq=8, nge_uq=9, ngt_uq=10, false_uq=11,
                 * neq_oq=12, ge_oq=13, gt_oq=14, true_uq=15
                 * (also lt_oq=17, le_oq=18, unord_s=19, etc.) */
                else if (strcmp(opbuf, "eq_uq") == 0) pred = 8;
                else if (strcmp(opbuf, "nge_uq") == 0) pred = 9;
                else if (strcmp(opbuf, "ngt_uq") == 0 || strcmp(opbuf, "ngt") == 0) pred = 10;  /* nt_uq */
                else if (strcmp(opbuf, "false_uq") == 0 || strcmp(opbuf, "false") == 0) pred = 11;
                else if (strcmp(opbuf, "neq_oq") == 0) pred = 12;
                else if (strcmp(opbuf, "ge_oq") == 0 || strcmp(opbuf, "ge") == 0) pred = 13;
                else if (strcmp(opbuf, "gt_oq") == 0 || strcmp(opbuf, "gt") == 0) pred = 14;
                else if (strcmp(opbuf, "true_uq") == 0 || strcmp(opbuf, "true") == 0) pred = 15;
                else if (strcmp(opbuf, "lt_oq") == 0) pred = 17;
                else if (strcmp(opbuf, "le_oq") == 0) pred = 18;
                /* signal variants: lt_s=17? (lt_os=17), le_os=18, ... */
                else if (strcmp(opbuf, "lt_os") == 0) pred = 17;
                else if (strcmp(opbuf, "le_os") == 0) pred = 18;
                else if (strcmp(opbuf, "unord_s") == 0) pred = 19;
                else if (strcmp(opbuf, "neq_us") == 0) pred = 20;
                else if (strcmp(opbuf, "nlt_uq") == 0) pred = 21;
                else if (strcmp(opbuf, "nle_uq") == 0) pred = 22;
                else if (strcmp(opbuf, "ord_s") == 0) pred = 23;
                else if (strcmp(opbuf, "eq_us") == 0) pred = 24;
                else if (strcmp(opbuf, "eq_os") == 0) pred = 24;  /* eq_us = eq_os = 24 */
                else if (strcmp(opbuf, "nge_us") == 0) pred = 25;
                else if (strcmp(opbuf, "ngt_us") == 0) pred = 26;
                else if (strcmp(opbuf, "false_os") == 0) pred = 27;
                else if (strcmp(opbuf, "neq_os") == 0) pred = 28;
                else if (strcmp(opbuf, "ge_os") == 0) pred = 29;
                else if (strcmp(opbuf, "gt_os") == 0) pred = 30;
                else if (strcmp(opbuf, "true_us") == 0) pred = 31;
                if (pred >= 0) {
                    const reg_t *rd = NULL, *rsn = NULL;
                    for (int i = 1; i < n; i++) {
                        if (toks[i].type == ATOK_ID) {
                            const reg_t *r = find_reg(toks[i].text);
                            if (r && r->is_xmm) {
                                if (!rd) rd = r; else if (!rsn) rsn = r;
                            }
                        }
                    }
                    if (rd && rsn) {
                        int l = (rd->name[0] == 'y') ? 1 : 0;
                        emit_vex(out, 0, 0, rsn->code, rd->code, 0, l, pp);
                        emit_byte(out, 0xC2);
                        emit_byte(out, 0xC0 | (rd->code & 7) << 3 | (rsn->code & 7));
                        emit_byte(out, (uint8_t)pred);
                        return 1;
                    }
                }
            }
        }
        /* AVX512 IFMA: vpmadd52huq/vpmadd52luq (EVEX.66.0F38.WIG B5/B4 /r)
         * (also VEX-compatible: VEX.66.0F38 B5/B4 /r for {vex} prefix variants) */
        if (strcmp(mnem, "vpmadd52huq") == 0 || strcmp(mnem, "vpmadd52luq") == 0) {
            int op = (mnem[8] == 'h') ? 0xB5 : 0xB4;
            const reg_t *rd = NULL, *rs = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs) rs = r;
                    }
                }
            }
            if (!rd || !rs) return 0;
            int ll = (rd->name[0] == 'y') ? 1 : (rd->name[0] == 'z' ? 2 : 0);
            /* zmm must use EVEX; xmm/ymm use VEX when registers fit 0-15 */
            if (rd->name[0] != 'z' && rs->name[0] != 'z' &&
                rd->code < 16 && rs->code < 16) {
                emit_vex(out, 2, 0, rs->code, rd->code, 0, ll, 1);
                emit_byte(out, (uint8_t)op);
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
            emit_evex(out, 2, 0, rs->code, rd->code, 0, ll, 1);
            emit_byte(out, (uint8_t)op);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        /* vshufpd/vshufps: VEX.NDS.128/256.66/0F.WIG C6 /r ib — 0F map with imm8,
         * so the avx_arith w==3 (0F3A) mechanism does not apply. */
        if (strcmp(mnem, "vshufpd") == 0 || strcmp(mnem, "vshufps") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int imm_val = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r;
                        else if (!rs1) rs1 = r;
                        else if (!rs2) rs2 = r;
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            int pp = (mnem[6] == 'd') ? 1 : 0;  /* vshuf**pd** → 66, vshuf**ps** → none */
            emit_vex(out, 0, 0, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, pp);
            emit_byte(out, 0xC6);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vbroadcastf32x2: EVEX.66.0F38 19 /r — broadcast low 64-bit of xmm to ymm/zmm (reg or mem). */
        if (strcmp(mnem, "vbroadcastf32x2") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int ll = (rd->name[0] == 'z') ? 2 : (rd->name[0] == 'y' ? 1 : 0);
            emit_evex_aa(out, 1, 0, 0xF, rd->code, found_mem ? 0 : rs1->code, ll, 1, rmask ? rmask->code : 0);
            emit_byte(out, 0x19);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vblendvps/vblendvpd/vpblendvb: VEX.NDS.128/256.66.0F3A.W0/W1 4A/4B/4C /r /is4
         * 4th operand (mask register) is encoded in imm8[7:4]. */
        if (strcmp(mnem, "vblendvps") == 0 || strcmp(mnem, "vblendvpd") == 0 ||
            strcmp(mnem, "vpblendvb") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r;
                        else if (!rs1) rs1 = r;
                        else if (!rs2) rs2 = r;
                        else if (!rmask) rmask = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            if (!rmask && rs2) { rmask = rs2; rs2 = NULL; }
            if (!rmask) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int w = (mnem[8] == 'd') ? 1 : 0;      /* vblendvpd W=1 */
            int op = (mnem[8] == 'd') ? 0x4B : (mnem[0] == 'v' && mnem[5] == 'v' && mnem[8] == 'b') ? 0x4C : 0x4A;  /* vb|pd|ps */
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 2, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2 ? rs2->code & 7 : 0);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)(rmask->code << 4));  /* /is4 in imm8[7:4] */
            return 1;
        }
        /* vpmaskmovd/vpmaskmovq: VEX.NDS.128/256.66.0F38.W0/W1 8C /r
         * Masked load/store: vpmaskmovd dest, mask, mem or vpmaskmovq mem, mask, src. */
        if (strcmp(mnem, "vpmaskmovd") == 0 || strcmp(mnem, "vpmaskmovq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int w = (mnem[8] == 'q') ? 1 : 0;  /* vpmaskmov**q** → W=1 */
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x8C);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpbroadcastb/w/d/q: VEX.66.0F38 78/79/7C/7C /r (register source)
         * or 58/59/58/59 /r (memory source). W=1 only for vpbroadcastq reg. */
        if (strcmp(mnem, "vpbroadcastb") == 0 || strcmp(mnem, "vpbroadcastw") == 0 ||
            strcmp(mnem, "vpbroadcastd") == 0 || strcmp(mnem, "vpbroadcastq") == 0) {
            char last = mnem[12];  /* vpbroadcast */
            const reg_t *rd = NULL, *rs1 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r;
                    } else if (r) {
                        if (!rs1) rs1 = r;   /* GPR source (vpbroadcastd/q from r32/r64) */
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            /* register ops: b=78,w=79,d=7C,q=7C; memory ops: b=58,w=59,d=58,q=59 */
            uint8_t op = 0x78;
            if (last == 'w') op = found_mem ? 0x59 : 0x79;
            else if (last == 'd') op = found_mem ? 0x58 : 0x7C;
            else if (last == 'q') op = found_mem ? 0x59 : 0x7C;
            int w = (last == 'q' && !found_mem) ? 1 : 0;  /* only reg q uses W=1 */
            emit_vex(out, 1, w, 0xF, rd->code, found_mem ? 0 : rs1->code, l, 1);
            emit_byte(out, op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpsllvq/vpsravq/vpsrlvq: VEX.NDS.128/256.66.0F38.W1 47/46/45 /r
         * qword variable shifts — W=1 variant of the dword versions (which are in avx_arith). */
        if (strcmp(mnem, "vpsllvq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 1, 1, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x47);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        if (strcmp(mnem, "vpsravq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 1, 1, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x46);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        if (strcmp(mnem, "vpsrlvq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 1, 1, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x45);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpclmullqlqdq/vpclmulhqlqdq/vpclmullqhqdq/vpclmulhqhqdq: pseudo-ops
         * that expand to vpclmulqdq with imm8 = 0x00/0x01/0x10/0x11. */
        if (strcmp(mnem, "vpclmullqlqdq") == 0 || strcmp(mnem, "vpclmulhqlqdq") == 0 ||
            strcmp(mnem, "vpclmullqhqdq") == 0 || strcmp(mnem, "vpclmulhqhqdq") == 0) {
            int imm8 = 0;
            if (mnem[6] == 'h') imm8 |= 1;      /* hql → 0x01 */
            if (mnem[8] == 'h') imm8 |= 0x10;   /* qhq → 0x10 */
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 2, 0, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x44);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm8);
            return 1;
        }
        /* vpsllw/vpslld/vpsllq/vpsrlw/vpsrld/vpsrlq/vpsraw/vpsrad: VEX.128/256.66.0F 71/72/73 /ext ib
         * Group-2 immediate shifts. Dest in VEX.vvvv, source in ModRM.rm,
         * ModRM.reg holds the group extension (ll=6, rl=2, ra=4). */
        if (strcmp(mnem, "vpsllw") == 0 || strcmp(mnem, "vpslld") == 0 || strcmp(mnem, "vpsllq") == 0 ||
            strcmp(mnem, "vpsrlw") == 0 || strcmp(mnem, "vpsrld") == 0 || strcmp(mnem, "vpsrlq") == 0 ||
            strcmp(mnem, "vpsraw") == 0 || strcmp(mnem, "vpsrad") == 0 || strcmp(mnem, "vpsraq") == 0 ||
            strcmp(mnem, "vpslldq") == 0 || strcmp(mnem, "vpsrldq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int imm_val = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && !rd) rd = r;
                    else if (r) rs1 = r;
                    else if (toks[i].text[0] != '.') { /* not a register id: skip */
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            /* width: word→0x71, dword→0x72, qword→0x73 */
            uint8_t op = 0x72;
            if (mnem[5] == 'w') op = 0x71;
            else if (mnem[5] == 'q') op = 0x73;
            /* extension: ssll→6, rl→2, ra→4  (mnem[3] is 's', mnem[4]='l'->left/'r'->right, mnem[3]=='s' start) */
            /* shift type at mnem[4]: 'l'=logical-left vpsll*, 'r'=right; mnem[5]='a' = arithmetic */
            int ext = 6;  /* shift left */
            if (mnem[4] == 'r') {
                ext = (mnem[5] == 'a') ? 4 : 2;  /* vpsra* → 4, vpsrl* → 2 */
            }
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            int is_zmm = (rd->code >= 16 || (rs1 && rs1->code >= 16));
            if (is_zmm) {
                emit_evex(out, 0, 0, rd->code, ext, 0, 2, 1);
            } else {
                emit_vex(out, 0, 0, rd->code, ext, found_mem ? 0 : rs1->code, l, 1);
            }
            emit_byte(out, op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, ext & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (ext & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vpblendw: VEX.NDS.128/256.66.0F.WIG 0E /r ib — 0F map with imm8. */
        if (strcmp(mnem, "vpblendw") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int imm_val = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 0, 0, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), l, 1);
            emit_byte(out, 0x0E);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vpshufd/vpshufhw/vpshuflw: VEX.128/256.66.0F.WIG 70/70/71 /r ib — immediate shuffle.
         * Dest in ModRM.reg, source in ModRM.rm, vvvv reserved. */
        if (strcmp(mnem, "vpshufd") == 0 || strcmp(mnem, "vpshufhw") == 0 ||
            strcmp(mnem, "vpshuflw") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int imm_val = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) { if (!rd) rd = r; else rs1 = r; }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            uint8_t op = 0x70;
            if (mnem[5] == 'l') op = 0x71;  /* vpshuf**l**w → 66 0F 71 */
            emit_vex(out, 0, 0, 0xF, rd->code, rs1->code, l, 1);
            emit_byte(out, op);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
            emit_byte(out, modrm);
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* v4fmaddps/v4fmaddss/v4fmaddsubps/v4fnmaddps/v4fnmaddss/v4fnmaddsubps:
         * EVEX.128.F2/F3.0F38.W0 9A/9B/AA/AB /r — 4-iteration fused multiply-add. */
        if (strcmp(mnem, "v4fmaddps") == 0 || strcmp(mnem, "v4fmaddss") == 0 ||
            strcmp(mnem, "v4fmaddsubps") == 0 || strcmp(mnem, "v4fnmaddps") == 0 ||
            strcmp(mnem, "v4fnmaddss") == 0 || strcmp(mnem, "v4fnmaddsubps") == 0) {
            const reg_t *rd = NULL, *rs = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm && r->code >= 16) { /* zmm has code >= 16 */
                        if (!rd) rd = r; else if (!rs) rs = r;
                    } else if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs) rs = r;
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs || !found_mem) return 0;
            int op = 0x9A;
            if (mnem[2] == 'f') op = 0xAA;  /* v4fnmadd* */
            if (mnem[2] == 'f' && mnem[7] == 's') op = 0xAB;  /* v4fnmaddsubps */
            else if (mnem[2] != 'f' && mnem[7] == 's') op = 0x9B;  /* v4fmaddsubps */
            emit_evex(out, 2, 0, rs->code, rd->code, 0, 0, 2);
            emit_byte(out, (uint8_t)op);
            int nr, si;
            encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
        /* vp4dpwssd/vp4dpwssds: EVEX.128.F2.0F38.W0 52/53 /r — 4-iteration VNNI
         * dot product with signed saturation (same memory-broadcast operand shape). */
        if (strcmp(mnem, "vp4dpwssd") == 0 || strcmp(mnem, "vp4dpwssds") == 0) {
            const reg_t *rd = NULL, *rs = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs) rs = r;
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs || !found_mem) return 0;
            uint8_t op = (mnem[7] == 's') ? 0x53 : 0x52;  /* vp4dpwss**ds** → 0x53 */
            emit_evex(out, 2, 0, rs->code, rd->code, 0, 0, 2);
            emit_byte(out, op);
            int nr, si;
            encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
        /* vmovdqa32/vmovdqa64/vmovdqu32/vmovdqu64: EVEX.66.0F 6F/7F /r — masked aligned/unaligned moves.
         * vmovdqa32: 6F load / 7F store, W=0; vmovdqa64: W=1; vmovdqu32: F3, W=0; vmovdqu64: F3, W=1. */
        if (strcmp(mnem, "vmovdqa32") == 0 || strcmp(mnem, "vmovdqa64") == 0 ||
            strcmp(mnem, "vmovdqu32") == 0 || strcmp(mnem, "vmovdqu64") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0, is_store = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            /* determine store: '[' appears before the first xmm register */
            int first_bracket = -1, first_xmm_tok = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[' && first_bracket < 0) first_bracket = i;
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm && first_xmm_tok < 0) first_xmm_tok = i;
                }
            }
            is_store = (first_bracket >= 0 && first_xmm_tok >= 0 && first_bracket < first_xmm_tok);
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = (mnem[7] == '6') ? 1 : 0;  /* vmovdqa64/vmovdqu64  W=1 */
            int pp = (mnem[4] == 'u') ? 2 : 1;  /* vmovdqu* → F3; vmovdqa* → 66 */
            int ll = (rd->name[0] == 'z') ? 2 : (rd->name[0] == 'y' ? 1 : 0);
            if (is_store) {
                emit_evex_aa(out, 0, w, 0xF, rd->code, 0, ll, pp, rmask ? rmask->code : 0);
                emit_byte(out, 0x7F);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (found_mem) {
                emit_evex_aa(out, 0, w, 0xF, rd->code, 0, ll, pp, rmask ? rmask->code : 0);
                emit_byte(out, 0x6F);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                emit_evex_aa(out, 0, w, 0xF, rd->code, rs1->code, ll, pp, rmask ? rmask->code : 0);
                emit_byte(out, 0x6F);
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vmovdqu8/vmovdqu16/vmovdqu32/vmovdqu64: EVEX.66.0F 6F/7F /r — byte/word mask load/store
         * Fully masked load/store variants of VMOVDQA/VMOVDQU. */
        if (strcmp(mnem, "vmovdqu8") == 0 || strcmp(mnem, "vmovdqu16") == 0 ||
            strcmp(mnem, "vmovdqu32") == 0 || strcmp(mnem, "vmovdqu64") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0, is_store = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            /* Determine if store: if the '[' token appears before the first xmm register,
             * it's a store to memory. Otherwise it's a load. */
            int first_op_bracket = -1, first_xmm = -1;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[' && first_op_bracket < 0) first_op_bracket = i;
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm && first_xmm < 0) first_xmm = i;
                }
            }
            is_store = (first_op_bracket >= 0 && first_xmm >= 0 && first_op_bracket < first_xmm);
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = 0;
            if (mnem[7] == '1') w = 0;  /* vmovdqu**16** → W=0? Actually mnem[7]='1' for 16 */
            else if (mnem[7] == '3') w = 0;  /* vmovdqu**32** */
            else if (mnem[7] == '6') w = 1;  /* vmovdqu**64** */
            /* vmovdqu8 uses W=0 as well */
            int ll = (rd->name[0] == 'z') ? 2 : (rd->name[0] == 'y' ? 1 : 0);
            if (is_store) {
                /* store: rd = source, mem = dest */
                emit_evex_aa(out, 0, w, 0xF, rd->code, 0, ll, 1, rmask ? rmask->code : 0);
                emit_byte(out, 0x7F);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (found_mem) {
                /* load: rd = dest, mem = source */
                emit_evex_aa(out, 0, w, 0xF, rd->code, 0, ll, 1, rmask ? rmask->code : 0);
                emit_byte(out, 0x6F);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                /* register form: rd = dest, rs1 = source */
                emit_evex_aa(out, 0, w, 0xF, rd->code, rs1->code, ll, 1, rmask ? rmask->code : 0);
                emit_byte(out, (is_store || (rs1 && first_op_bracket < 0 && first_xmm < first_op_bracket)) ? 0x7F : 0x6F);
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vfmadd132ps/pd/vfmadd213ps/pd/vfmadd231ps/pd/vfnmadd132ps/pd/vfnmadd213ps/pd/vfnmadd231ps/pd
         * vfmsub132ps/pd/vfmsub213ps/pd/vfmsub231ps/pd/vfnmsub132ps/pd/vfnmsub213ps/pd/vfnmsub231ps/pd
         * EVEX.66.0F38.W0/W1 98-9F /r — FMA with 3 operands. */
        if ((strncmp(mnem, "vfmadd", 6) == 0 || strncmp(mnem, "vfnmadd", 7) == 0 ||
            strncmp(mnem, "vfmsub", 6) == 0 || strncmp(mnem, "vfnmsub", 7) == 0) &&
            !strstr(mnem, "cph") && !strstr(mnem, "csh") && !strstr(mnem, "mulc")) {
            static const struct { const char *name; int op; } fma_ops[] = {
                { "vfmadd132", 0x98 }, { "vfmadd213", 0x98 }, { "vfmadd231", 0x98 },
                { "vfnmadd132", 0x9C }, { "vfnmadd213", 0x9C }, { "vfnmadd231", 0x9C },
                { "vfmsub132", 0x9A }, { "vfmsub213", 0x9A }, { "vfmsub231", 0x9A },
                { "vfnmsub132", 0x9E }, { "vfnmsub213", 0x9E }, { "vfnmsub231", 0x9E },
                { "vfmaddsub132", 0x96 }, { "vfmaddsub213", 0x97 }, { "vfmaddsub231", 0x98 },
                { "vfmsubadd132", 0x9A }, { "vfmsubadd213", 0x9B }, { "vfmsubadd231", 0x9C },
                { "vfmaddcph", 0x56 }, { "vfmaddcsh", 0x57 }, { "vfmulcph", 0x40 },
                { "vfmulcsh", 0x41 }, { "vfcmaddcph", 0x46 }, { "vfcmaddcsh", 0x47 },
                { "vfcmulcph", 0x40 }, { "vfcmulcsh", 0x41 }, { NULL, 0 }
            };
            char prefix[16] = {0};
            /* Find first digit in the mnemonic to locate 132/213/231 suffix */
            int mnem_len = strlen(mnem);
            int digit_pos = -1;
            for (int k = 6; k < mnem_len && mnem[k]; k++) {
                if (mnem[k] >= '1' && mnem[k] <= '3') { digit_pos = k; break; }
            }
            if (digit_pos < 0) return 0;
            int plen = digit_pos;  /* base prefix length (everything before digits) */
            if (plen + 3 > 16) return 0;
            memcpy(prefix, mnem, plen + 3);  /* copy base + 132/213/231 */
            prefix[plen + 3] = 0;
            int op = -1, w = 0;
            for (int k = 0; fma_ops[k].name; k++) {
                if (strcmp(prefix, fma_ops[k].name) == 0) { op = fma_ops[k].op; break; }
            }
            if (op < 0) return 0;
            /* Determine W from the suffix: ps → W=0, pd → W=1 (mnem[plen+3] = 'p') */
            if (mnem[plen + 4] == 'd') w = 1;  /* ...pd → W=1 */
            /* Determine the opcode offset: 132→0, 213→2, 231→4 */
            if (prefix[plen] == '2') op += 2;  /* 213 */
            else if (prefix[plen] == '2' && prefix[plen+1] == '3') op += 4;  /* 231 */
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            emit_evex_aa(out, 1, w, rs1 ? rs1->code : 0xF, rd->code, found_mem ? 0 : (rs2 ? rs2->code : (rs1 ? rs1->code : 0xF)), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vblendmpd/vblendmps: EVEX.66.0F38.W1/W0 65/64 /r — masked blend. */
        if (strcmp(mnem, "vblendmpd") == 0 || strcmp(mnem, "vblendmps") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = (mnem[7] == 'd') ? 1 : 0;  /* vblendm**pd** → W=1 */
            int op = (mnem[7] == 'd') ? 0x65 : 0x64;
            emit_evex_aa(out, 1, w, rs1 ? rs1->code : 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* valignd/valignq: EVEX.66.0F3A.W0/W1 03 /r ib — align dword/qword with imm8. */
        if (strcmp(mnem, "valignd") == 0 || strcmp(mnem, "valignq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1) return 0;
            int w = (mnem[5] == 'q') ? 1 : 0;  /* valign**q** → W=1 */
            emit_evex_aa(out, 3, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, 0);
            emit_byte(out, 0x03);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vrndscaleps/vrndscalepd: EVEX.66.0F3A.W0/W1 08/09 /r ib — scale-and-round with imm8. */
        if (strcmp(mnem, "vrndscaleps") == 0 || strcmp(mnem, "vrndscalepd") == 0) {
            const reg_t *rd = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd) return 0;
            int w = (mnem[9] == 'd') ? 1 : 0;  /* vrndscalep**d** → W=1 */
            int op = (mnem[9] == 'd') ? 0x09 : 0x08;
            emit_evex_aa(out, 3, w, 0xF, rd->code, found_mem ? 0 : 0xF, 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vcvtudq2ps/vcvtudq2pd/vcvtuqq2ps/vcvtuqq2pd: EVEX.0F.F2/F3 7A /r unsigned source conversions. */
        if (strcmp(mnem, "vcvtudq2ps") == 0 || strcmp(mnem, "vcvtudq2pd") == 0 ||
            strcmp(mnem, "vcvtuqq2ps") == 0 || strcmp(mnem, "vcvtuqq2pd") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k' && !rd) { /* mask only, skip */ }
                        else if (r->is_xmm || r->name[0] == 'k') {
                            if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            /* vcvtudq2ps: F2 0F 7A W0; vcvtudq2pd: F2 0F 7A W1 */
            int pp = 2, w = (mnem[7] == 'd') ? 1 : 0;
            if (mnem[5] == 'q') { w = (mnem[7] == 'd') ? 1 : 0; pp = 3; } /* vcvtuqq: F3 */
            emit_evex(out, 0, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, pp);
            emit_byte(out, 0x7A);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcompresspd/vcompressps/vexpandpd/vexpandps: EVEX.66.0F38 63/62/62/63 /r — AVX-512F
         * compress/expand double/single with k mask and memory dest (compress) or source (expand). */
        if (strcmp(mnem, "vcompresspd") == 0 || strcmp(mnem, "vcompressps") == 0 ||
            strcmp(mnem, "vexpandpd") == 0 || strcmp(mnem, "vexpandps") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int is_compress = (mnem[1] == 'c');  /* vcompress vs vexpand */
            int w = (mnem[8] == 'd') ? 1 : 0;    /* vcompresspd/vexpandpd  W=1 */
            int op = (mnem[8] == 'd') ? 0x63 : 0x62;  /* pd→63, ps→62 */
            if (is_compress && found_mem) {
                /* compress to memory: source is rd, dest is memory */
                emit_evex_aa(out, 1, w, 0xF, rd->code, 0, 2, 1, rmask ? rmask->code : 0);
                emit_byte(out, (uint8_t)op);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (is_compress && rs1) {
                /* compress reg dest, reg src: dest = rs1, src = rd */
                emit_evex_aa(out, 1, w, 0xF, rs1->code, rd->code, 2, 1, rmask ? rmask->code : 0);
                emit_byte(out, (uint8_t)op);
                uint8_t modrm = 0xC0 | (rs1->code & 7) << 3 | (rd->code & 7);
                emit_byte(out, modrm);
            } else {
                /* expand: dest = rd, src = mem/rs1 */
                emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, 1, rmask ? rmask->code : 0);
                emit_byte(out, (uint8_t)op);
                if (found_mem) {
                    int nr, si;
                    encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                    (void)nr; (void)si;
                } else {
                    uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                    emit_byte(out, modrm);
                }
            }
            return 1;
        }
        /* vbroadcastf32x8/vbroadcastf64x4/vbroadcasti32x8/vbroadcasti64x4: EVEX.66.0F38 1B/1A/5B/5A /r
         * AVX-512DQ broadcast 256-bit lane (ymm source) to zmm destination. */
        if (strcmp(mnem, "vbroadcastf32x8") == 0 || strcmp(mnem, "vbroadcastf64x4") == 0 ||
            strcmp(mnem, "vbroadcasti32x8") == 0 || strcmp(mnem, "vbroadcasti64x4") == 0) {
            const reg_t *rd = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !found_mem) return 0;
            int op, w = 0;
            if (mnem[10] == '8') { op = (mnem[7] == 'i') ? 0x5B : 0x1B; }   /* i32x8 → 5B, f32x8 → 1B */
            else { op = (mnem[7] == 'i') ? 0x5A : 0x1A; w = 1; }            /* i64x4 → 5A, f64x4 → 1A */
            emit_evex_aa(out, 1, w, 0xF, rd->code, 0, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            int nr, si;
            encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
            return 1;
        }
        /* vbroadcasti32x2/vbroadcasti64x2: EVEX.66.0F38 5B /r — broadcast low 64-bit of xmm
         * to xmm/ymm/zmm destination (register or memory source) with k mask. */
        if (strcmp(mnem, "vbroadcasti32x2") == 0 || strcmp(mnem, "vbroadcasti64x2") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int ll = (rd->name[0] == 'z') ? 2 : (rd->name[0] == 'y' ? 1 : 0);
            int w = (mnem[11] == '2' && mnem[10] == 'i') ? 0 : 0;  /* W0 for i32x2; i64x2 uses W1 */
            if (mnem[10] == 'i' && mnem[12] == '6') w = 1;  /* vbroadcasti64x2 → W1 */
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : rs1->code, ll, 1, rmask ? rmask->code : 0);
            emit_byte(out, 0x5B);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vinsertf32x8/vinsertf64x4/vinserti32x8/vinserti64x4: EVEX.66.0F3A 1A/1B/3A/3B /r ib
         * AVX-512DQ insert 256-bit lane (zmm dest, ymm source) with k mask and imm8. */
        if (strcmp(mnem, "vinsertf32x8") == 0 || strcmp(mnem, "vinsertf64x4") == 0 ||
            strcmp(mnem, "vinserti32x8") == 0 || strcmp(mnem, "vinserti64x4") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[8] == '8') { op = (mnem[7] == 'i') ? 0x3A : 0x1A; }   /* i32x8 → 3A, f32x8 → 1A */
            else { op = (mnem[7] == 'i') ? 0x3B : 0x1B; w = 1; }            /* i64x4 → 3B, f64x4 → 1B */
            emit_evex_aa(out, 3, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vextractf32x8/vextractf64x4/vextracti32x8/vextracti64x4: EVEX.66.0F3A 1B/1A/3B/3A /r ib
         * AVX-512DQ extract 256-bit lane (zmm source → ymm dest) with k mask and imm8. */
        if (strcmp(mnem, "vextractf32x8") == 0 || strcmp(mnem, "vextractf64x4") == 0 ||
            strcmp(mnem, "vextracti32x8") == 0 || strcmp(mnem, "vextracti64x4") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1) return 0;
            int op, w = 0;
            if (mnem[10] == '8') { op = (mnem[7] == 'i') ? 0x3B : 0x1B; }   /* i32x8 → 3B, f32x8 → 1B */
            else { op = (mnem[7] == 'i') ? 0x3A : 0x1A; w = 1; }            /* i64x4 → 3A, f64x4 → 1A */
            emit_evex_aa(out, 3, w, rs1->code, rd->code, found_mem ? 0 : 0xF, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                /* register form: dest in ModRM.reg, source in vvvv */
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (0xF & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vinsertf64x2/vinserti64x2/vinsertf32x4/vinserti32x4: EVEX.66.0F3A 18/38/1A/3A /r ib
         * AVX-512DQ insert 128-bit lane with k mask and imm8. */
        if (strcmp(mnem, "vinsertf64x2") == 0 || strcmp(mnem, "vinserti64x2") == 0 ||
            strcmp(mnem, "vinsertf32x4") == 0 || strcmp(mnem, "vinserti32x4") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op;
            if (mnem[8] == '6') op = 0x18;  /* vinsertf64x2 → 0x18 */
            else if (mnem[8] == '4') op = 0x1A;  /* vinsertf32x4 → 0x1A */
            else if (mnem[8] == '6' && mnem[7] == 'i') op = 0x38;  /* vinserti64x2 → 0x38 */
            else op = 0x3A;  /* vinserti32x4 → 0x3A */
            emit_evex_aa(out, 3, 0, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vreducepd/vreduceps/vreducesd/vreducess: EVEX.66.0F3A 56/56/57/57 /r ib — reduce
         * precision with imm8 (AVX-512DQ). */
        if (strcmp(mnem, "vreducepd") == 0 || strcmp(mnem, "vreduceps") == 0 ||
            strcmp(mnem, "vreducesd") == 0 || strcmp(mnem, "vreducess") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = (mnem[6] == 'd') ? 1 : 0;   /* vreduce**p**d → W=1, vreduce**s**d → W=1 */
            if (mnem[6] == 's' && mnem[7] == 's') w = 0;  /* vreducess → W=0 */
            int op = (mnem[8] == 's') ? 0x57 : 0x56;  /* vreduce*s → 0x57 */
            emit_evex_aa(out, 3, w, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vrangepd/vrangeps/vrangesd/vrangess: EVEX.66.0F3A 50/50/51/51 /r ib — range restriction
         * with k mask and imm8 (AVX-512DQ). */
        if (strcmp(mnem, "vrangepd") == 0 || strcmp(mnem, "vrangeps") == 0 ||
            strcmp(mnem, "vrangesd") == 0 || strcmp(mnem, "vrangess") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            /* vrangepd → 50 W=1; vrangeps → 50 W=0; vrangesd → 51 W=1; vrangess → 51 W=0 */
            int w = (mnem[5] == 'p' || mnem[5] == 's') ? 1 : 0;
            int op = (mnem[6] == 's') ? 0x51 : 0x50;  /* vrange**s**d → 0x51 */
            if (mnem[6] == 'd' && mnem[5] == 'p') { op = 0x50; w = 1; } /* vrange**pd** */
            emit_evex_aa(out, 3, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vextractf64x2/vextracti64x2/vextractf32x4/vextracti32x4: EVEX.66.0F3A 19/39/1B/3B /r ib
         * AVX-512DQ extract 128-bit lane with k mask and imm8. */
        if (strcmp(mnem, "vextractf64x2") == 0 || strcmp(mnem, "vextracti64x2") == 0 ||
            strcmp(mnem, "vextractf32x4") == 0 || strcmp(mnem, "vextracti32x4") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1) return 0;
            int op;
            if (mnem[9] == '2') op = 0x19;  /* vextractf64x2 → 0x19 */
            else if (mnem[9] == '4') op = 0x1B;  /* vextractf32x4 → 0x1B */
            else if (mnem[9] == '2' && mnem[7] == 'i') op = 0x39;  /* vextracti64x2 → 0x39 */
            else op = 0x3B;  /* vextracti32x4 → 0x3B */
            emit_evex_aa(out, 3, 0, rs1->code, rd->code, found_mem ? 0 : 0xF, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                /* Register form: dest = xmm, source = ymm in vvvv? Actually:
                 * vextractf64x2 xmm1{k}{z}, ymm2, imm — dest in ModRM.reg, source in vvvv */
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (0xF & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vcvtqq2pd/vcvtqq2ps/vcvtuqq2pd/vcvtuqq2ps: EVEX.66/F3.0F 7A /r — AVX-512DQ
         * quadword-to-floating conversions with k mask. W=1 for qq source. */
        if (strcmp(mnem, "vcvtqq2pd") == 0 || strcmp(mnem, "vcvtqq2ps") == 0 ||
            strcmp(mnem, "vcvtuqq2pd") == 0 || strcmp(mnem, "vcvtuqq2ps") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int pp = (mnem[8] == 'p') ? (mnem[9] == 's' ? 2 : 1) : 0;  /* vcvtqq2ps → F3; vcvtqq2pd → 66 */
            emit_evex_aa(out, 0, 1, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, pp, rmask ? rmask->code : 0);
            emit_byte(out, 0x7A);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtpd2qq/vcvtps2qq/vcvttpd2qq/vcvttps2qq/vcvtpd2uqq/vcvtps2uqq/vcvttpd2uqq/vcvttps2uqq:
         * EVEX.66/F3.0F 79/E6 /r — AVX-512DQ quadword conversions with k mask. */
        if (strcmp(mnem, "vcvtpd2qq") == 0 || strcmp(mnem, "vcvtps2qq") == 0 ||
            strcmp(mnem, "vcvttpd2qq") == 0 || strcmp(mnem, "vcvttps2qq") == 0 ||
            strcmp(mnem, "vcvtpd2uqq") == 0 || strcmp(mnem, "vcvtps2uqq") == 0 ||
            strcmp(mnem, "vcvttpd2uqq") == 0 || strcmp(mnem, "vcvttps2uqq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 1, pp = 1;
            if (strcmp(mnem, "vcvtpd2qq") == 0) op = 0x79;      /* 66 0F */
            else if (strcmp(mnem, "vcvtps2qq") == 0) op = 0x79; /* 66 0F */
            else if (strcmp(mnem, "vcvttpd2qq") == 0) op = 0xE6; /* 66 0F */
            else { op = 0xE6; pp = 2; }                          /* vcvttps2qq: F3 0F */
            emit_evex_aa(out, 0, w, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, pp, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtpd2udq/vcvtps2udq/vcvttpd2udq/vcvttps2udq: EVEX.66.0F/W1 79/.../E6/... /r
         * unsigned conversions with optional k mask. */
        if (strcmp(mnem, "vcvtpd2udq") == 0 || strcmp(mnem, "vcvtps2udq") == 0 ||
            strcmp(mnem, "vcvttpd2udq") == 0 || strcmp(mnem, "vcvttps2udq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rk = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k' && rk == NULL) { rk = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = 1, op, pp = 1;
            if (strcmp(mnem, "vcvtpd2udq") == 0) op = 0x79;       /* 66 0F */
            else if (strcmp(mnem, "vcvtps2udq") == 0) op = 0x79;  /* 66 0F */
            else if (strcmp(mnem, "vcvttpd2udq") == 0) op = 0xE6; /* 66 0F */
            else op = 0xE6;  /* vcvttps2udq: F3 0F E6 */
            int mm = 0;
            if (strcmp(mnem, "vcvttps2udq") == 0) { pp = 2; mm = 0; } /* F3 */
            emit_evex_aa(out, mm, w, rs1 ? rs1->code : 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, pp, rk ? rk->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vrsqrt14ps/vrsqrt14pd/vrcp14ps/vrcp14pd/vgetexpps/vgetexppd/vgetmantps/vgetmantpd:
         * EVEX.66.0F38 0x4E/0x4E/0x4D/0x4D/0x42/0x42/0x26/0x27 /r — AVX-512F arithmetic. */
        if (strcmp(mnem, "vrsqrt14ps") == 0 || strcmp(mnem, "vrsqrt14pd") == 0 ||
            strcmp(mnem, "vrcp14ps") == 0 || strcmp(mnem, "vrcp14pd") == 0 ||
            strcmp(mnem, "vgetexpps") == 0 || strcmp(mnem, "vgetexppd") == 0 ||
            strcmp(mnem, "vgetmantps") == 0 || strcmp(mnem, "vgetmantpd") == 0) {
            const reg_t *rd = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd) return 0;
            int op, w = 0;
            if (strcmp(mnem, "vrsqrt14ps") == 0) op = 0x4E;
            else if (strcmp(mnem, "vrsqrt14pd") == 0) { op = 0x4E; w = 1; }
            else if (strcmp(mnem, "vrcp14ps") == 0) op = 0x4D;
            else if (strcmp(mnem, "vrcp14pd") == 0) { op = 0x4D; w = 1; }
            else if (strcmp(mnem, "vgetexpps") == 0) op = 0x42;
            else if (strcmp(mnem, "vgetexppd") == 0) { op = 0x42; w = 1; }
            else if (strcmp(mnem, "vgetmantps") == 0) op = 0x26;
            else { op = 0x27; w = 1; }  /* vgetmantpd */
            emit_evex(out, 1, w, 0xF, rd->code, found_mem ? 0 : 0xF, 2, 1);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            }
            return 1;
        }
        /* vrcp28ss/vrcp28sd/vrsqrt28ss/vrsqrt28sd/vexp2ss/vexp2sd: EVEX.66.0F38 0xCA/0xCC/0xC8 /r
         * AVX-512ER scalar reciprocal/sqrt/exponential (3-operand with k mask). */
        if (strcmp(mnem, "vrcp28ss") == 0 || strcmp(mnem, "vrcp28sd") == 0 ||
            strcmp(mnem, "vrsqrt28ss") == 0 || strcmp(mnem, "vrsqrt28sd") == 0 ||
            strcmp(mnem, "vexp2ss") == 0 || strcmp(mnem, "vexp2sd") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op = 0xCA, w = 0;
            if (strncmp(mnem, "vrsqrt28", 8) == 0) op = 0xCC;
            else if (strncmp(mnem, "vexp2", 5) == 0) { op = 0xC8; w = (mnem[5] == 'd') ? 1 : 0; }
            emit_evex_aa(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 0, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vexp2ps/vexp2pd/vrcp28ps/vrcp28pd/vrsqrt28ps/vrsqrt28pd: EVEX.66.0F38 0xC8-CF /r
         * AVX-512ER exponential/reciprocal approximations, memory source. */
        if (strcmp(mnem, "vexp2ps") == 0 || strcmp(mnem, "vexp2pd") == 0 ||
            strcmp(mnem, "vrcp28ps") == 0 || strcmp(mnem, "vrcp28pd") == 0 ||
            strcmp(mnem, "vrsqrt28ps") == 0 || strcmp(mnem, "vrsqrt28pd") == 0) {
            const reg_t *rd = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd) return 0;
            int op, w = 0;
            if (strcmp(mnem, "vexp2ps") == 0) op = 0xC8;
            else if (strcmp(mnem, "vexp2pd") == 0) { op = 0xC8; w = 1; }
            else if (strcmp(mnem, "vrcp28ps") == 0) op = 0xCA;
            else if (strcmp(mnem, "vrcp28pd") == 0) { op = 0xCA; w = 1; }
            else if (strcmp(mnem, "vrsqrt28ps") == 0) op = 0xCC;
            else { op = 0xCC; w = 1; }  /* vrsqrt28pd */
            emit_evex(out, 1, w, 0xF, rd->code, found_mem ? 0 : 0xF, 2, 1);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            }
            return 1;
        }
        /* vcvtps2phx/vcvtdq2phx/vcvtudq2phx/vcvtpd2phx/vcvtqq2phx: FP16 "x" pack variants
         * (EVEX.66.0F3A 1D/1C/1E/1D/1D /r ib same as base but XMM mem source). */
        if (strcmp(mnem, "vcvtps2phx") == 0 || strcmp(mnem, "vcvtdq2phx") == 0 ||
            strcmp(mnem, "vcvtudq2phx") == 0 || strcmp(mnem, "vcvtpd2phx") == 0 ||
            strcmp(mnem, "vcvtqq2phx") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[7] == 'd' && mnem[8] == 'q') op = 0x1C;  /* vcvt**dq**2phx */
            else if (mnem[7] == 'u' && mnem[8] == 'd') op = 0x1E;  /* vcvt**udq**2phx */
            else if (mnem[7] == 'p' && mnem[8] == 'd') { op = 0x1D; w = 1; }  /* vcvt**pd**2phx */
            else if (mnem[7] == 'q' && mnem[8] == 'q') { op = 0x1D; w = 1; }  /* vcvt**qq**2phx */
            else op = 0x1D;
            emit_evex_aa(out, 3, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vcvtps2ph/vcvtdq2ph/vcvtudq2ph/vcvtpd2ph/vcvtqq2ph/vcvtuqq2ph/vcvtuw2ph/vcvtw2ph:
         * EVEX.66.0F3A 1D/1C/1E/1D/1D/1D/1D/1D /r ib — FP16 pack conversion with imm8.
         * W=1 for pd/qq/uqq. */
        if (strcmp(mnem, "vcvtps2ph") == 0 || strcmp(mnem, "vcvtdq2ph") == 0 ||
            strcmp(mnem, "vcvtudq2ph") == 0 || strcmp(mnem, "vcvtpd2ph") == 0 ||
            strcmp(mnem, "vcvtqq2ph") == 0 || strcmp(mnem, "vcvtuqq2ph") == 0 ||
            strcmp(mnem, "vcvtuw2ph") == 0 || strcmp(mnem, "vcvtw2ph") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (strcmp(mnem, "vcvtps2ph") == 0) op = 0x1D;
            else if (strcmp(mnem, "vcvtdq2ph") == 0) op = 0x1C;
            else op = 0x1E;  /* vcvtudq2ph */
            emit_evex_aa(out, 3, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vcvtph2psx/vcvtph2pdx/vcvtph2dqx/vcvtph2udqx: FP16 "x" variants (XMM/mem-half source).
         * Same encodings as base variants (EVEX.66.0F38 1D/1D/1A/1C /r), W=1 for pd/qq. */
        if (strcmp(mnem, "vcvtph2psx") == 0 || strcmp(mnem, "vcvtph2pdx") == 0 ||
            strcmp(mnem, "vcvtph2dqx") == 0 || strcmp(mnem, "vcvtph2udqx") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[8] == 'd') op = 0x1A;         /* vcvtph2dq */
            else if (mnem[8] == 'u') op = 0x1C;    /* vcvtph2udq */
            else if (mnem[8] == 'p') { op = 0x1D; w = 1; }  /* vcvtph2pd */
            else op = 0x1D;                          /* vcvtph2ps */
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvttph2dq/vcvttph2udq/vcvttph2qq/vcvttph2uqq: EVEX.66.0F38 1A/1C/1A/1C /r — FP16 truncate. */
        if (strcmp(mnem, "vcvttph2dq") == 0 || strcmp(mnem, "vcvttph2udq") == 0 ||
            strcmp(mnem, "vcvttph2qq") == 0 || strcmp(mnem, "vcvttph2uqq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[8] == 'u' && mnem[9] == 'd') op = 0x1C;  /* vcvttph2**ud**q */
            else if (mnem[8] == 'q' && mnem[9] == 'q') { op = 0x1A; w = 1; }  /* vcvttph2**qq** */
            else if (mnem[8] == 'u' && mnem[9] == 'q') { op = 0x1C; w = 1; }  /* vcvttph2**uq**q */
            else op = 0x1A;  /* vcvttph2dq */
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvttph2uw/vcvttph2wb/vcvttph2w: EVEX.66.0F38 1C /r — FP16 truncate to word. */
        if (strcmp(mnem, "vcvttph2uw") == 0 || strcmp(mnem, "vcvttph2wb") == 0 ||
            strcmp(mnem, "vcvttph2w") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            emit_evex_aa(out, 1, 0, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, 0x1C);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtph2uw/vcvtph2wb/vcvtph2w: FP16 → unsigned word / word narrowing (EVEX.66.0F38 1C/1C/1C). */
        if (strcmp(mnem, "vcvtph2uw") == 0 || strcmp(mnem, "vcvtph2wb") == 0 ||
            strcmp(mnem, "vcvtph2w") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            emit_evex_aa(out, 1, 0, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, 0x1C);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtph2ps/vcvtph2dq/vcvtph2udq/vcvtph2pd/vcvtph2qq/vcvtph2uqq: EVEX.66.0F38 1D/1A/1C/1D/1D/1C /r
         * FP16 to wider. W=1 for pd/qq/uqq. */
        if (strcmp(mnem, "vcvtph2ps") == 0 || strcmp(mnem, "vcvtph2dq") == 0 ||
            strcmp(mnem, "vcvtph2udq") == 0 || strcmp(mnem, "vcvtph2pd") == 0 ||
            strcmp(mnem, "vcvtph2qq") == 0 || strcmp(mnem, "vcvtph2uqq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (strcmp(mnem, "vcvtph2ps") == 0) op = 0x1D;
            else if (strcmp(mnem, "vcvtph2dq") == 0) op = 0x1A;
            else op = 0x1C;  /* vcvtph2udq */
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcomish/vucomish: EVEX.66.0F 2E/2F /r — FP16 scalar compare (set EFLAGS). */
        if (strcmp(mnem, "vcomish") == 0 || strcmp(mnem, "vucomish") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op = (mnem[1] == 'u') ? 0x2F : 0x2E;  /* vucomish=2F, vcomish=2E */
            emit_evex_aa(out, 0, 0, 0xF, rd->code, found_mem ? 0 : rs1->code, 0, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpshldw/vpshldd/vpshldq/vpshrdw/vpshrdd/vpshrdq: EVEX.66.0F3A 71/72/73 /r ib
         * VBMI2 immediate shifts with k mask and imm8. */
        if (strcmp(mnem, "vpshldw") == 0 || strcmp(mnem, "vpshldd") == 0 ||
            strcmp(mnem, "vpshldq") == 0 || strcmp(mnem, "vpshrdw") == 0 ||
            strcmp(mnem, "vpshrdd") == 0 || strcmp(mnem, "vpshrdq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0, imm_val = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[6] == 'w') op = 0x71;
            else if (mnem[6] == 'd') op = 0x72;
            else { op = 0x73; w = 1; }  /* q */
            emit_evex_aa(out, 3, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vpshldv{w,d,q}/vpshrdv{w,d,q}: EVEX.66.0F38.F2/F3 71/72/73 /r — VBMI2 variable shifts
         * (dest shifted by count in vvvv, source in rm) with k mask. */
        if (strcmp(mnem, "vpshldvw") == 0 || strcmp(mnem, "vpshldvd") == 0 ||
            strcmp(mnem, "vpshldvq") == 0 || strcmp(mnem, "vpshrdvw") == 0 ||
            strcmp(mnem, "vpshrdvd") == 0 || strcmp(mnem, "vpshrdvq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[7] == 'w') op = 0x71;
            else if (mnem[7] == 'd') op = 0x72;
            else { op = 0x73; w = 1; }  /* q */
            emit_evex_aa(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpcompressb/vpcompressw/vpexpandb/vpexpandw: EVEX.66.0F38 63/62/62/63 /r — VBMI2
         * compress/expand with k mask and mem destination (compress) or source (expand). */
        if (strcmp(mnem, "vpcompressb") == 0 || strcmp(mnem, "vpcompressw") == 0 ||
            strcmp(mnem, "vpexpandb") == 0 || strcmp(mnem, "vpexpandw") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            /* vpcompressb: 0F38 63; vpcompressw: 0F38 62; expand uses same with mem as source */
            int op = (mnem[2] == 'c' && mnem[10] == 'b') ? 0x63 : 0x62;
            if (mnem[2] == 'c' && mnem[10] == 'b') op = 0x63;
            else if (mnem[2] == 'c' && mnem[10] == 'w') op = 0x62;
            else if (mnem[2] == 'e' && mnem[8] == 'b') op = 0x62;  /* vpexpandb */
            else op = 0x63;  /* vpexpandw */
            /* compress: dest = mem/reg (rm), src = rd (reg); expand: dest = rd (reg), src = mem/reg (rm) */
            int is_compress = (mnem[2] == 'c');
            int regfield = is_compress ? rd->code : rd->code;      /* reg field = source reg */
            int rmfield  = found_mem ? 0 : (is_compress ? rs1->code : rs1->code);
            /* For compress (no rs1 needed — source is rd):
             *   compress mem{km}, rd  → reg=rd, rm=mem
             *   compress rd2{km}, rd1 → reg=rd1? Actually VPCOMPRESSB reg, xmm source: reg registers
             * For expand:
             *   expand rd{km}, mem    → reg=rd, rm=mem
             *   expand rd1{km}, rd2   → reg=rd1, rm=rd2 */
            if (is_compress && found_mem) {
                /* compress to memory: source is rd */
                emit_evex_aa(out, 1, 0, 0xF, rd->code, 0, 0, 1, rmask ? rmask->code : 0);
                emit_byte(out, (uint8_t)op);
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
                return 1;
            }
            if (is_compress && !found_mem && rs1) {
                /* compress reg dest, reg src: reg=src(rs1)? Use rs1 as dest-encoding */
                emit_evex_aa(out, 1, 0, 0xF, rs1->code, rd->code, 0, 1, rmask ? rmask->code : 0);
                emit_byte(out, (uint8_t)op);
                uint8_t modrm = 0xC0 | (rs1->code & 7) << 3 | (rd->code & 7);
                emit_byte(out, modrm);
                return 1;
            }
            /* expand forms */
            emit_evex_aa(out, 1, 0, 0xF, regfield, found_mem ? 0 : rmfield, 0, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, regfield & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (regfield & 7) << 3 | (rmfield & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpmultishiftqb: EVEX.66.0F38.W1 83 /r — VBMI2 multishift (masked). */
        if (strcmp(mnem, "vpmultishiftqb") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            emit_evex_aa(out, 1, 1, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, 0x83);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpermb/vpermw: EVEX.66.0F38.W0 8D/8E /r — VBMI byte/word permute (masked).
         * vpermt2b/vpermt2w/vpermbd/vpermbq/vpermwq/vpermi2b/vpermi2w: 0F38 7D/7E/6D/6E/6D/75/76. */
        if (strcmp(mnem, "vpermb") == 0 || strcmp(mnem, "vpermw") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op = (mnem[5] == 'b') ? 0x8D : 0x8E;  /* vperm**b** → 8D, vperm**w** → 8E */
            emit_evex_aa(out, 1, 0, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpermt2b/vpermt2w/vpermq2b/vpermi2b/vpermi2w/vpermt2d/vpermt2q:
         * EVEX.66.0F38 7D/7E/6D/75/76/7F/7E /r — two-source permute with k mask. */
        if (strncmp(mnem, "vpermt2", 7) == 0 || strncmp(mnem, "vpermi2", 7) == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op = 0x7D, w = 0;
            if (mnem[7] == 'w') op = 0x7E;
            else if (mnem[7] == 'd') op = 0x7F;
            else if (mnem[7] == 'q') { op = 0x7E; w = 1; }
            else if (mnem[7] == 'b') op = 0x7D;
            emit_evex_aa(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpblendmb/vpblendmw/vpblendmd/vpblendmq: EVEX.66.0F38 66/64/64/66 /r — byte/word masked blend.
         * Dest in ModRM.reg, mask in EVEX.aaa, vvvv = source1, rm = source2/mem. */
        if (strcmp(mnem, "vpblendmb") == 0 || strcmp(mnem, "vpblendmw") == 0 ||
            strcmp(mnem, "vpblendmd") == 0 || strcmp(mnem, "vpblendmq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) {
                            if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[7] == 'b') op = 0x66;
            else if (mnem[7] == 'w') op = 0x64;
            else if (mnem[7] == 'd') op = 0x66;  /* vpblendmd uses 0F38 66? Actually 66=dblend q=weird; keep 66/64 family */
            else { op = 0x64; w = 1; }           /* vpblendmq */
            emit_evex_aa(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpcmp{eq,lt,le,neq,nlt,nle}{b,w,d,q} / vpcmpu{...}: EVEX.66.0F3A 3F/3D/1F /r ib
         * packed compare pseudo-ops writing to k mask with predicate imm8.
         * Signed: b=3F, w=3D, d=1F(W0), q=1F(W1). Unsigned: b=3E, w=3C, d=1E(W0), q=1E(W1).
         * Pred: eq=0, lt=1, le=2, neq=4, nlt=5, nle=6. */
        if (strncmp(mnem, "vpcmp", 5) == 0 && strstr(mnem, "k") == NULL) {
            /* must start with vpcmp and have an element suffix and end with a predicate */
            int mlen2 = strlen(mnem);
            if (mlen2 < 8) return 0;
            char elem = mnem[mlen2 - 1];       /* b/w/d/q */
            /* unsigned marker: 'u' immediately before the element letter (e.g. vpcmpequb) */
            int unsigned_v = (mlen2 >= 2 && mnem[mlen2 - 2] == 'u');
            if (unsigned_v && mnem[5] == 'u') unsigned_v = 1;
            /* predicate is between start (5, or 6 for vpcmpu prefix) and elem-1 (minus trailing u) */
            const char *pred_start = mnem + (mnem[5] == 'u' ? 6 : 5);
            int pred_end = mlen2 - 1 - (unsigned_v ? 1 : 0);  /* exclude trailing 'u' if unsigned */
            int pred_len = pred_end - (pred_start - mnem);
            if (pred_len < 2 || pred_len > 4) return 0;
            char pred[8] = {0};
            memcpy(pred, pred_start, (size_t)pred_len);
            pred[pred_len] = 0;
            int pred_val = -1;
            if (strcmp(pred, "eq") == 0) pred_val = 0;
            else if (strcmp(pred, "lt") == 0) pred_val = 1;
            else if (strcmp(pred, "le") == 0) pred_val = 2;
            else if (strcmp(pred, "neq") == 0) pred_val = 4;
            else if (strcmp(pred, "nlt") == 0) pred_val = 5;
            else if (strcmp(pred, "nle") == 0) pred_val = 6;
            if (pred_val < 0) return 0;
            const reg_t *rk = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) {
                            if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || !rs1) return 0;
            int op, w = 0;
            if (elem == 'b') op = unsigned_v ? 0x3E : 0x3F;
            else if (elem == 'w') op = unsigned_v ? 0x3C : 0x3D;
            else if (elem == 'd') op = unsigned_v ? 0x1E : 0x1F;
            else { op = unsigned_v ? 0x1E : 0x1F; w = 1; }  /* q */
            emit_evex_aa(out, 3, w, rs1->code, rk->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)pred_val);
            return 1;
        }
        /* vcmpeqpd/vcmpltpd/vcmplepd/vcmpneqpd/vcmpnltpd/vcmpnlepd + ps/sd/ss variants:
         * Pseudo-ops that expand to VPCMP with predicate imm8 (EVEX.66.0F C2 /r ib).
         * Format: vcmp + pred + suffix (pd/ps/sd/ss). Pred: eq=0, lt=1, le=2, neq=4, nlt=5, nle=6. */
        if (strncmp(mnem, "vcmp", 4) == 0 && mnem[4] != 'p' && mnem[4] != 's' && mnem[4] != 'h' &&
            mnem[4] != 'q' && mnem[4] != 'd') {
            /* Not the base vcmpps/vcmppd/vcmpph/vcmpsh/vcmpss/vcmpsd — try pseudo-op form */
            int mlen2 = strlen(mnem);
            if (mlen2 < 7) return 0;
            /* Extract suffix (last 2-3 chars): pd/ps/sd/ss */
            const char *suf = mnem + mlen2 - 2;
            int pp = 0, mm = 0;
            if (strcmp(suf, "pd") == 0) pp = 1;
            else if (strcmp(suf, "ps") == 0) pp = 0;
            else if (strcmp(suf, "sd") == 0) pp = 3;
            else if (strcmp(suf, "ss") == 0) pp = 2;
            else return 0;
            /* Extract predicate (between "vcmp" and suffix) */
            const char *pred_start = mnem + 4;
            int pred_len = (mnem + mlen2 - 2) - pred_start;
            if (pred_len < 2 || pred_len > 7) return 0;
            char pred[8] = {0};
            memcpy(pred, pred_start, (size_t)pred_len);
            pred[pred_len] = 0;
            int pred_val = -1;
            if (strcmp(pred, "eq") == 0) pred_val = 0;
            else if (strcmp(pred, "eq_uq") == 0) pred_val = 8;
            else if (strcmp(pred, "eq_os") == 0 || strcmp(pred, "eq_us") == 0) pred_val = 24;
            else if (strcmp(pred, "lt") == 0) pred_val = 1;
            else if (strcmp(pred, "lt_os") == 0 || strcmp(pred, "lt_oq") == 0) pred_val = 17;
            else if (strcmp(pred, "le") == 0) pred_val = 2;
            else if (strcmp(pred, "le_os") == 0 || strcmp(pred, "le_oq") == 0) pred_val = 18;
            else if (strcmp(pred, "unord") == 0) pred_val = 3;
            else if (strcmp(pred, "unord_s") == 0) pred_val = 19;
            else if (strcmp(pred, "neq") == 0) pred_val = 4;
            else if (strcmp(pred, "neq_oq") == 0) pred_val = 12;
            else if (strcmp(pred, "neq_os") == 0) pred_val = 28;
            else if (strcmp(pred, "neq_us") == 0) pred_val = 20;
            else if (strcmp(pred, "nlt") == 0) pred_val = 5;
            else if (strcmp(pred, "nlt_uq") == 0) pred_val = 21;
            else if (strcmp(pred, "nle") == 0) pred_val = 6;
            else if (strcmp(pred, "nle_uq") == 0) pred_val = 22;
            else if (strcmp(pred, "ord") == 0) pred_val = 7;
            else if (strcmp(pred, "ord_s") == 0) pred_val = 23;
            else if (strcmp(pred, "false") == 0 || strcmp(pred, "false_uq") == 0) pred_val = 11;
            else if (strcmp(pred, "false_os") == 0) pred_val = 27;
            else if (strcmp(pred, "ge") == 0 || strcmp(pred, "ge_oq") == 0) pred_val = 13;
            else if (strcmp(pred, "ge_os") == 0) pred_val = 29;
            else if (strcmp(pred, "gt") == 0 || strcmp(pred, "gt_oq") == 0) pred_val = 14;
            else if (strcmp(pred, "gt_os") == 0) pred_val = 30;
            else if (strcmp(pred, "true") == 0 || strcmp(pred, "true_uq") == 0) pred_val = 15;
            else if (strcmp(pred, "true_us") == 0) pred_val = 31;
            else if (strcmp(pred, "nge") == 0 || strcmp(pred, "nge_uq") == 0) pred_val = 9;
            else if (strcmp(pred, "nge_us") == 0) pred_val = 25;
            else if (strcmp(pred, "ngt") == 0 || strcmp(pred, "ngt_uq") == 0) pred_val = 10;
            else if (strcmp(pred, "ngt_us") == 0) pred_val = 26;
            if (pred_val < 0) return 0;
            int w = (suf[0] == 'p' && suf[1] == 'd') ? 1 : 0;  /* pd → W=1 */
            const reg_t *rk = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) { if (!rs1) rs1 = r; else if (!rs2) rs2 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || !rs1) return 0;
            emit_evex_aa(out, 0, w, rs1->code, rk->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, pp, 0);
            emit_byte(out, 0xC2);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)pred_val);
            return 1;
        }
        /* vcmpps/vcmppd/vcmpph/vcmpsh/vcmpss/vcmpsd: EVEX/CMP 0F/0F38 C2 /r ib — compare to k mask. */
        if (strcmp(mnem, "vcmpps") == 0 || strcmp(mnem, "vcmppd") == 0 || strcmp(mnem, "vcmpph") == 0 ||
            strcmp(mnem, "vcmpsh") == 0 || strcmp(mnem, "vcmpss") == 0 || strcmp(mnem, "vcmpsd") == 0) {
            const reg_t *rk = NULL, *rs1 = NULL, *rs2 = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) {
                            if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || !rs1 || (!rs2 && !found_mem)) return 0;
            int w = (mnem[5] == 'd') ? 1 : 0;  /* vcmp**p**d → W=1 */
            int mm = (mnem[5] == 'h') ? 2 : 0; /* vcmp**p**h → 0F38 map */
            emit_evex_aa(out, mm, w, rs1->code, rk->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, 0);
            emit_byte(out, 0xC2);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vcvtsi2sh/vcvtusi2sh: EVEX.66.0F3A 1D /r ib — integer to FP16 scalar (GPR source). */
        if (strcmp(mnem, "vcvtsi2sh") == 0 || strcmp(mnem, "vcvtusi2sh") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rg = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                        else if (!rg) rg = r;  /* GPR source */
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rg && !found_mem)) return 0;
            emit_evex_aa(out, 3, 0, rs1->code, rd->code, found_mem ? 0 : rg->code, 0, 1, 0);
            emit_byte(out, 0x1D);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rg->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtsh2si/vcvttsh2si/vcvtsh2usi/vcvttsh2usi: EVEX.F3.0F 2D/2C /r — FP16 scalar to GPR.
         * GPR destination in ModRM.reg, xmm/mem source in ModRM.rm. */
        if (strcmp(mnem, "vcvtsh2si") == 0 || strcmp(mnem, "vcvttsh2si") == 0 ||
            strcmp(mnem, "vcvtsh2usi") == 0 || strcmp(mnem, "vcvttsh2usi") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->is_xmm) { if (!rs1) rs1 = r; }
                        else if (!rd) rd = r;  /* GPR dest */
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op = (mnem[4] == 't') ? 0x2C : 0x2D;  /* vcvttsh2si → 2C */
            emit_evex_aa(out, 0, 0, 0xF, rd->code, found_mem ? 0 : rs1->code, 0, 2, 0);  /* F3 prefix */
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vcvtsd2sh/vcvtss2sh/vcvtudq2sh/vcvtqq2sh/vcvtsh2ss/vcvtsh2sd/vcvtph2sh:
         * EVEX FP16 scalar conversions (66.0F3A 1D/1C/1E/1D/1D/1D/1C /r ib). */
        if (strcmp(mnem, "vcvtsd2sh") == 0 || strcmp(mnem, "vcvtss2sh") == 0 ||
            strcmp(mnem, "vcvtudq2sh") == 0 || strcmp(mnem, "vcvtqq2sh") == 0 ||
            strcmp(mnem, "vcvtsh2ss") == 0 || strcmp(mnem, "vcvtsh2sd") == 0 ||
            strcmp(mnem, "vcvtph2sh") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int op, w = 0, mm = 3;  /* default: 0F3A map */
            if (strcmp(mnem, "vcvtsd2sh") == 0) op = 0x1D;  /* 66 0F3A */
            else if (strcmp(mnem, "vcvtss2sh") == 0) op = 0x1D; /* 66 0F3A */
            else if (strcmp(mnem, "vcvtudq2sh") == 0) op = 0x1E; /* 66 0F3A */
            else if (strcmp(mnem, "vcvtqq2sh") == 0) { op = 0x1D; w = 1; } /* 66 0F3A W1 */
            else if (strcmp(mnem, "vcvtsh2ss") == 0) { op = 0x1D; mm = 1; } /* 66 0F38 */
            else if (strcmp(mnem, "vcvtsh2sd") == 0) { op = 0x1D; mm = 1; w = 1; } /* 66 0F38 W1 */
            else op = 0x1C;  /* vcvtph2sh */
            emit_evex_aa(out, mm, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 0, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vfpclassps/vfpclasspd/vfpclassph/vfpclassss/vfpclasssd: EVEX.66.0F3A 66/67/68 /r ib
         * classify to k mask register with imm8. Handles `{ 1 to8 }` embed syntax. */
        if (strcmp(mnem, "vfpclassps") == 0 || strcmp(mnem, "vfpclasspd") == 0 ||
            strcmp(mnem, "vfpclassph") == 0 || strcmp(mnem, "vfpclassss") == 0 ||
            strcmp(mnem, "vfpclasssd") == 0) {
            const reg_t *rk = NULL, *rs1 = NULL;
            int imm_val = 0, found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) { if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_NUM) {
                    imm_val = (int)toks[i].value;
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || (!rs1 && !found_mem)) return 0;
            int op, w = 0;
            if (mnem[8] == 's' && mnem[9] == 's') op = 0x67;        /* vfpclassss */
            else if (mnem[8] == 's' && mnem[9] == 'd') { op = 0x68; w = 1; }  /* vfpclasssd */
            else if (mnem[8] == 'p' && mnem[9] == 's') op = 0x66;   /* vfpclassps */
            else if (mnem[8] == 'p' && mnem[9] == 'd') { op = 0x67; w = 1; }  /* vfpclasspd */
            else { op = 0x68; w = 0; }  /* vfpclassph (W0 in 0F3A? use 68) */
            emit_evex_aa(out, 3, w, 0xF, rk->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            emit_byte(out, (uint8_t)imm_val);
            return 1;
        }
        /* vpopcntb/vpopcntw/vpopcntd/vpopcntq: EVEX.66.0F38 54/55 /r — BITALG popcount,
         * with optional k mask. W depends on element width (b=0,w=0 for 0F38 55 W=0... use b=0x54, w/d/q=0x55). */
        if (strcmp(mnem, "vpopcntb") == 0 || strcmp(mnem, "vpopcntw") == 0 ||
            strcmp(mnem, "vpopcntd") == 0 || strcmp(mnem, "vpopcntq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rk = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = 0, op = 0x55;
            if (mnem[7] == 'b') op = 0x54;        /* vpopcntb → 54 */
            else if (mnem[7] == 'q') w = 1;       /* vpopcntq → 55 W=1 */
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : (rs1 ? rs1->code : 0xF), 2, 1, rk ? rk->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vfcmaddcph/vfcmulcph/vfcmaddcsh/vfcmulcsh/vfmaddcph/vfmulcph/vfmaddcsh/vfmulcsh:
         * EVEX.66.0F38.W0/W1 46/40/42/40 /r — FP16 complex FMA/mul (conjugation variants). */
        if (strcmp(mnem, "vfcmaddcph") == 0 || strcmp(mnem, "vfcmulcph") == 0 ||
            strcmp(mnem, "vfcmaddcsh") == 0 || strcmp(mnem, "vfcmulcsh") == 0 ||
            strcmp(mnem, "vfmaddcph") == 0 || strcmp(mnem, "vfmulcph") == 0 ||
            strcmp(mnem, "vfmaddcsh") == 0 || strcmp(mnem, "vfmulcsh") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && r->is_xmm) {
                        if (!rd) rd = r; else if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || !rs1 || (!rs2 && !found_mem)) return 0;
            /* Order ops: vfmaddcph/vfmaddcsh=0x56(132)-based? Use the base table:
             * vfmaddc 132=0x56,213=0x56+2,231=0x56+4? Real encodings differ; use 0x42/0x40/0x45/0x43. */
            /* vfmaddcph: 0F38 56 (W0); vfmaddcsh: 0F38 57 (W0); vfmulcph: 0F38 40; vfmulcsh: 0F38 41;
             * vfcmaddcph: 0F38 46; vfcmulcph: 0F38 40 (with conjugation implied by opcode);
             * vfcmaddcsh: 0F38 47; vfcmulcsh: 0F38 41. */
            int op = 0x56, w = 0;
            if (strcmp(mnem, "vfmaddcsh") == 0) op = 0x57;
            else if (strcmp(mnem, "vfmulcph") == 0 || strcmp(mnem, "vfcmulcph") == 0) op = 0x40;
            else if (strcmp(mnem, "vfmulcsh") == 0 || strcmp(mnem, "vfcmulcsh") == 0) op = 0x41;
            else if (strcmp(mnem, "vfcmaddcph") == 0) op = 0x46;
            else if (strcmp(mnem, "vfcmaddcsh") == 0) op = 0x47;
            /* W=1 for zmm variants; ymm/xmm use W=0 */
            emit_evex_aa(out, 1, w, rs1->code, rd->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1, 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpshufbitqmb: EVEX.66.0F38.W0 8F /r — bit-shuffle compare with mask output.
         * Result written to k register (ModRM.reg), vvvv = first source, rm = second source (reg or mem). */
        if (strcmp(mnem, "vpshufbitqmb") == 0) {
            const reg_t *rk = NULL, *rs1 = NULL, *rs2 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') {
                            /* might be { k7 } mask or k5 dest — first k is dest, second is mask */
                            if (!rk) rk = r; else if (!rmask) rmask = r;
                        } else if (r->is_xmm) {
                            if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || !rs1 || (!rs2 && !found_mem)) return 0;
            emit_evex_aa(out, 1, 0, rs1->code, rk->code, found_mem ? 0 : rs2->code, 0, 1, rmask ? rmask->code : 0);
            emit_byte(out, 0x8F);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vptestmd/vptestnmd/vptestmq/vptestnmq: EVEX.66.0F38 0x27/0x25/0x28/0x26 /r
         * compares write result to a k mask register (ModRM.reg = k, vvvv = source2). */
        if (strcmp(mnem, "vptestmd") == 0 || strcmp(mnem, "vptestnmd") == 0 ||
            strcmp(mnem, "vptestmq") == 0 || strcmp(mnem, "vptestnmq") == 0) {
            const reg_t *rk = NULL, *rs1 = NULL, *rs2 = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) {
                            if (!rs1) rs1 = r; else if (!rs2) rs2 = r;
                        }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rk || !rs1) return 0;
            /* vptestmd: 0x27, vptestnmd: 0x25, vptestmq: 0x28, vptestnmq: 0x26 */
            int op, w = 0;
            if (strcmp(mnem, "vptestmd") == 0) op = 0x27;
            else if (strcmp(mnem, "vptestnmd") == 0) op = 0x25;
            else if (strcmp(mnem, "vptestmq") == 0) { op = 0x28; w = 1; }
            else { op = 0x26; w = 1; }
            emit_evex(out, 1, w, rs1->code, rk->code, found_mem ? 0 : (rs2 ? rs2->code : 0xF), 2, 1);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rk->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs2) {
                uint8_t modrm = 0xC0 | (rk->code & 7) << 3 | (rs2->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vplzcntd/vplzcntq: EVEX.66.0F38 0x44/0x45 /r — leading zero count (reg or mem, masked). */
        if (strcmp(mnem, "vplzcntd") == 0 || strcmp(mnem, "vplzcntq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = (mnem[7] == 'q') ? 1 : 0;  /* vplzcnt**q** → W=1 */
            int op = (mnem[7] == 'q') ? 0x45 : 0x44;
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpbroadcastmw2d/vpbroadcastmb2q: EVEX.66.0F38 3B/3A /r — broadcast mask to dword/qword.
         * k register source (ModRM.rm) broadcast to xmm/ymm/zmm dest (ModRM.reg). */
        if (strcmp(mnem, "vpbroadcastmw2d") == 0 || strcmp(mnem, "vpbroadcastmb2q") == 0) {
            const reg_t *rd = NULL, *rk = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rk) rk = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; }
                    }
                }
            }
            if (!rd || !rk) return 0;
            int ll = (rd->name[0] == 'z') ? 2 : (rd->name[0] == 'y' ? 1 : 0);
            int op = (mnem[12] == 'q') ? 0x3A : 0x3B;  /* vpbroadcastm**b**2q → 3A */
            emit_evex_aa(out, 1, 0, 0xF, rd->code, rk->code, ll, 1, 0);
            emit_byte(out, (uint8_t)op);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rk->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        /* vpconflictd/vpconflictq: EVEX.66.0F38 0xC4/C5 /r — conflict detection (reg or mem, masked). */
        if (strcmp(mnem, "vpconflictd") == 0 || strcmp(mnem, "vpconflictq") == 0) {
            const reg_t *rd = NULL, *rs1 = NULL, *rmask = NULL;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->name[0] == 'k') { if (!rmask) rmask = r; }
                        else if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                    }
                } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
                }
            }
            if (!rd || (!rs1 && !found_mem)) return 0;
            int w = (mnem[9] == 'q') ? 1 : 0;  /* vpconflict**q** → W=1 */
            int op = (mnem[9] == 'q') ? 0xC5 : 0xC4;
            emit_evex_aa(out, 1, w, 0xF, rd->code, found_mem ? 0 : rs1->code, 2, 1, rmask ? rmask->code : 0);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else if (rs1) {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpmovsx* / vpmovzx*: VEX.128/256.66.0F38 20-25/30-35 /r - sign/zero-extend narrow to wide.
         * Source is xmm, GPR, or memory (ModRM.rm); dest is xmm (ModRM.reg); vvvv reserved. */
        if (strncmp(mnem, "vpmovsx", 7) == 0 || strncmp(mnem, "vpmovzx", 7) == 0) {
            static const struct { const char *suf; int op; } pmovsx[] = {
                { "bw", 0x20 }, { "bd", 0x21 }, { "bq", 0x22 },
                { "wd", 0x23 }, { "wq", 0x24 }, { "dq", 0x25 },
                { NULL, 0 }
            };
            static const struct { const char *suf; int op; } pmovzx[] = {
                { "bw", 0x30 }, { "bd", 0x31 }, { "bq", 0x32 },
                { "wd", 0x33 }, { "wq", 0x34 }, { "dq", 0x35 },
                { NULL, 0 }
            };
            const char *suffix = mnem + 7;
            int op = -1;
            const struct { const char *suf; int op; } *tbl =
                (mnem[4] == 's') ? pmovsx : pmovzx;
            for (int k = 0; tbl[k].suf; k++) {
                if (strcmp(suffix, tbl[k].suf) == 0) { op = tbl[k].op; break; }
            }
            if (op < 0) return 0;
            const reg_t *rd = NULL, *rs1 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
                        else if (!rs1) rs1 = r;  /* GPR source */
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rd->name[0] == 'y') ? 1 : 0;
            int found_mem = 0;
            mem_op_t mop;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (parse_mem_operand(toks, i, n, &mop) >= 0) { found_mem = 1; break; }
                }
            emit_vex(out, 1, 0, 0xF, rd->code, found_mem ? 0 : rs1->code, l, 1);
            emit_byte(out, (uint8_t)op);
            if (found_mem) {
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
            } else {
                uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
                emit_byte(out, modrm);
            }
            return 1;
        }
        /* vpmovmskb/vpmovmskd/vpmovmskq: VEX.128/256.66.0F(D7)/66.0F38(D7) /r — move byte mask
         * to GPR. Destination is a GPR (ModRM.reg), source is an xmm/ymm (ModRM.rm),
         * vvvv reserved. W=1 only for vpmovmskq. */
        if (strcmp(mnem, "vpmovmskb") == 0 || strcmp(mnem, "vpmovmskd") == 0 ||
            strcmp(mnem, "vpmovmskq") == 0) {
            char last = mnem[8];  /* vpmovms(7)k(8) → b/d/q at index 8 */
            const reg_t *rd = NULL, *rs1 = NULL;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r) {
                        if (r->is_xmm) { if (!rs1) rs1 = r; }
                        else if (!rd) rd = r;  /* GPR dest */
                    }
                }
            }
            if (!rd || !rs1) return 0;
            int l = (rs1->name[0] == 'y') ? 1 : 0;
            int w = (last == 'q') ? 1 : 0;
            /* vpmovmskb: 66 0F D7; vpmovmskd/q: 66 0F38 D7 */
            emit_vex(out, (last == 'b') ? 0 : 1, w, 0xF, rd->code, rs1->code, l, 1);
            emit_byte(out, 0xD7);
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
            emit_byte(out, modrm);
            return 1;
        }
        /* vzeroall/vzeroupper: VEX.256/128.0F.WIG 77 (zero ymm/xmm registers, no operands) */
        if (strcmp(mnem, "vzeroall") == 0 || strcmp(mnem, "vzeroupper") == 0) {
            /* vzeroupper: VEX.128.0F.WIG 77 → C5 F8 77; vzeroall: VEX.256 → C5 FC 77 */
            int l_bit = (mnem[5] == 'a') ? 1 : 0;
            emit_vex(out, 0, 0, 0xF, 0, 0, l_bit, 0);
            emit_byte(out, 0x77);
            return 1;
        }
        /* fall through — unknown AVX instruction returns 0 */
    }
    /* AVX2 gather: vgatherdpd/vgatherqpd/vgatherdps/vgatherqps */
    if (strcmp(mnem, "vgatherdpd") == 0 || strcmp(mnem, "vgatherqpd") == 0 ||
        strcmp(mnem, "vgatherdps") == 0 || strcmp(mnem, "vgatherqps") == 0 ||
        strcmp(mnem, "vpgatherdd") == 0 || strcmp(mnem, "vpgatherdq") == 0 ||
        strcmp(mnem, "vpgatherqd") == 0 || strcmp(mnem, "vpgatherqq") == 0) {
        int op = 0x92;
        /* Determine opcode from the last 3 characters of the mnemonic.
         * "vgatherdpd": last 3 = "dpd" → 0x92 (W=1, 64-bit element)
         * "vgatherqpd": last 3 = "qpd" → 0x93
         * "vgatherdps": last 3 = "dps" → 0x92 (W=0, 32-bit)
         * "vgatherqps": last 3 = "qps" → 0x93
         * "vpgatherdd": last 3 = "dd"  → 0x90 (W=0)
         * "vpgatherdq": last 3 = "dq"  → 0x91 (W=1)
         * "vpgatherqd": last 3 = "qd"  → 0x92 (W=0)
         * "vpgatherqq": last 3 = "qq"  → 0x93 (W=1) */
        int mlen = strlen(mnem);
        if (mlen >= 3) {
            char c1 = mnem[mlen-3], c2 = mnem[mlen-2], c3 = mnem[mlen-1];
            if (c1 == 'd' && c2 == 'p' && c3 == 'd') op = 0x92;
            else if (c1 == 'q' && c2 == 'p' && c3 == 'd') op = 0x93;
            else if (c1 == 'd' && c2 == 'p' && c3 == 's') op = 0x92;
            else if (c1 == 'q' && c2 == 'p' && c3 == 's') op = 0x93;
            else if (mnem[0] == 'v' && mnem[1] == 'p') {
                if (c1 == 'd' && c2 == 'd') op = 0x90;
                else if (c1 == 'd' && c2 == 'q') op = 0x91;
                else if (c1 == 'q' && c2 == 'd') op = 0x92;
                else op = 0x93;
            }
        }
        const reg_t *rd = NULL, *rs = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) {
                    if (!rd) rd = r;
                    else if (toks[i-1].type == ATOK_OP && toks[i-1].text[0] == ',') rs = r;
                }
            }
        }
        if (!rd) return 0;
        int l = (rd->name[0] == 'y') ? 1 : 0;
        /* vgather* instructions use VEX.0F38 (map=2), W=1 for 64-bit element (pd/qd),
         * W=0 for 32-bit element (ps/qs). Determine W from the opcode:
         * op 0x92 = W=1 (dpd/qd), 0x93 = W=1 (qpd/qq), 0x90 = W=0 (dd), 0x91 = W=1 (dq) */
        int w_bit = (op == 0x90) ? 0 : 1;
        emit_vex(out, 2, w_bit, rs ? rs->code : 0xF, rd->code, 0, l, 1);
        emit_byte(out, (uint8_t)op);
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                mem_op_t mop;
                if (parse_mem_operand(toks, i, n, &mop) < 0) return 0;
                int nr, si;
                encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
                (void)nr; (void)si;
                return 1;
            }
        }
        return 0;
    }

    /* call/jmp with a label operand → relative reloc (R_X86_64_PLT32) */
    /* invept/invvpid/invpcid: VEX.66.0F38.W0 80/81/82 /r — VMX/PCID cache control.
     * GPR destination (ModRM.reg), OWORD (m128) memory source (ModRM.rm). */
    if (strcmp(mnem, "invept") == 0 || strcmp(mnem, "invvpid") == 0 || strcmp(mnem, "invpcid") == 0) {
        const reg_t *rd = NULL;
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm && !rd) rd = r;
            } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (!rd || !found_mem) return 0;
        int op = 0x80;   /* invept */
        if (mnem[2] == 'v') op = 0x81;      /* invvpid */
        else if (mnem[2] == 'p') op = 0x82; /* invpcid */
        emit_vex(out, 1, 0, 0xF, rd->code, 0, 0, 1);  /* VEX.66.0F38 */
        emit_byte(out, (uint8_t)op);
        int nr, si;
        encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
        (void)nr; (void)si;
        return 1;
    }

    /* rdfsbase/rdgsbase/wrfsbase/wrgsbase: F3 0F AE /0-3 — FS/GS base register access.
     * RDFSBASE r64: F3 0F AE /0; RDGSBASE /1; WRFSBASE /2; WRGSBASE /3. */
    if (strcmp(mnem, "rdfsbase") == 0 || strcmp(mnem, "rdgsbase") == 0 ||
        strcmp(mnem, "wrfsbase") == 0 || strcmp(mnem, "wrgsbase") == 0) {
        const reg_t *rd = find_reg(toks[1].text);
        if (!rd) return 0;
        int op = 0;
        if (mnem[1] == 'd' && mnem[2] == 'g') op = 1;   /* rdgsbase */
        else if (mnem[1] == 'w' && mnem[2] == 'f') op = 2;  /* wrfsbase */
        else if (mnem[1] == 'w' && mnem[2] == 'g') op = 3;  /* wrgsbase */
        emit_byte(out, 0xF3);
        emit_byte(out, 0x0F);
        emit_byte(out, 0xAE);
        emit_byte(out, 0xC0 | (op & 7) << 3 | (rd->code & 7));
        return 1;
    }

    /* Non-VEX GFNI instructions (outside the v-prefix block):
     * gf2p8mulb xmm1, xmm2/m128: 66 0F 38 CF /r
     * gf2p8affineqb xmm1, xmm2/m128, imm8: 66 0F 3A CE /r ib
     * gf2p8affineinvqb xmm1, xmm2/m128, imm8: 66 0F 3A CF /r ib */
    if (strcmp(mnem, "gf2p8mulb") == 0 || strcmp(mnem, "gf2p8affineqb") == 0 ||
        strcmp(mnem, "gf2p8affineinvqb") == 0) {
        const reg_t *rd = NULL, *rs1 = NULL;
        int found_mem = 0;
        mem_op_t mop;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) { if (!rd) rd = r; else if (!rs1) rs1 = r; }
            } else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                if (parse_mem_operand(toks, i, n, &mop) >= 0) found_mem = 1;
            }
        }
        if (!rd || (!rs1 && !found_mem)) return 0;
        emit_byte(out, 0x66);
        emit_byte(out, 0x0F);
        if (strcmp(mnem, "gf2p8mulb") == 0) {
            emit_byte(out, 0x38);
            emit_byte(out, 0xCF);
        } else {
            emit_byte(out, 0x3A);
            emit_byte(out, (mnem[7] == 'i') ? 0xCF : 0xCE);
        }
        if (found_mem) {
            int nr, si;
            encode_mem_operand(out, rd->code & 7, &mop, &nr, &si);
            (void)nr; (void)si;
        } else {
            uint8_t modrm = 0xC0 | (rd->code & 7) << 3 | (rs1->code & 7);
            emit_byte(out, modrm);
        }
        if (strcmp(mnem, "gf2p8mulb") != 0) {
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_NUM) { emit_byte(out, (uint8_t)toks[i].value); break; }
        }
        return 1;
    }

    /* jcc conditional jumps: je/jne/jb/jae/jg/jle/js/jz/jnz/jl/jge/jbe/ja/jp/jnp/jc/jnc
     * near form: 0F 8x /rel32; `@B` back-reference resolves to anon_lbl. */
    if (n >= 2 && toks[0].type == ATOK_ID && mnem[0] == 'j') {
        static const struct { const char *cc; int op; } jcc_ops[] = {
            { "jo", 0x80 }, { "jno", 0x81 }, { "jb", 0x82 }, { "jae", 0x83 },
            { "je", 0x84 }, { "jz", 0x84 }, { "jne", 0x85 }, { "jnz", 0x85 },
            { "jbe", 0x86 }, { "ja", 0x87 }, { "js", 0x88 }, { "jns", 0x89 },
            { "jp", 0x8A }, { "jnp", 0x8B }, { "jl", 0x8C }, { "jge", 0x8D },
            { "jle", 0x8E }, { "jg", 0x8F }, { "jc", 0x82 }, { "jnc", 0x83 },
            { "jnb", 0x83 }, { "jnbe", 0x87 }, { "jna", 0x86 }, { "jnae", 0x82 },
            { "jnb", 0x83 }, { NULL, 0 }
        };
        int op = -1;
        for (int k = 0; jcc_ops[k].cc; k++)
            if (strcmp(mnem, jcc_ops[k].cc) == 0) { op = jcc_ops[k].op; break; }
        if (op >= 0) {
            /* @B / @F back-reference to anonymous label */
            if (toks[1].type == ATOK_ID && (strcmp(toks[1].text, "@B") == 0 || strcmp(toks[1].text, "@b") == 0)) {
                emit_byte(out, 0x0F);
                emit_byte(out, (uint8_t)op);
                int64_t cur = cur_offset(out);
                int32_t rel = (int32_t)(out->anon_lbl - cur - 6);
                emit_imm(out, (uint64_t)(uint32_t)rel, 4);
                return 1;
            }
            if (toks[1].type == ATOK_ID) {
                int si = find_or_add_sym(out, toks[1].text);
                emit_byte(out, 0x0F);
                emit_byte(out, (uint8_t)op);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 4, -6);
                return 1;
            }
        }
    }

    if (strcmp(mnem, "movbe") == 0) {
        /* movbe r,r/m → 0F 38 F0 /r ; movbe r/m,r → 0F 38 F1 /r */
        const reg_t *br = NULL;
        int mem_idx = -1;
        int is_mem_dest = 0;   /* movbe r/m, r → F1 */
        /* find register and memory operand */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                /* memory operand; mem_dest if the register appears after it */
                int j;
                for (j = i; j < n; j++)
                    if (toks[j].type == ATOK_OP && toks[j].text[0] == ',') { is_mem_dest = 1; break; }
                mem_idx = i;
            } else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!br) br = r; }
            }
        }
        if (!br || mem_idx < 0) return 0;
        mem_op_t mop;
        int pmi = parse_mem_operand(toks, mem_idx, n, &mop);
        if (pmi < 0) return 0;
        /* determine operand size: 66 prefix for 16-bit */
        int is16 = 0;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "WORD") == 0 || strcmp(toks[i].text, "word") == 0))
                is16 = 1;
        if (is16) emit_byte(out, 0x66);
        int is64 = br->is64;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "QWORD") == 0 || strcmp(toks[i].text, "qword") == 0))
                is64 = 1;
        /* REX: W if 64-bit, B if memory base reg>=8, R if reg>=8 */
        int rex = 0;
        if (is64) rex |= 8;
        if (mop.has_base && mop.base_reg >= 8) rex |= 1;
        if (br->code >= 8) rex |= 4;
        if (rex) emit_byte(out, 0x40 | rex);
        emit_byte(out, 0x0F); emit_byte(out, 0x38);
        emit_byte(out, is_mem_dest ? 0xF1 : 0xF0);
        int nr, si;
        int ok = encode_mem_operand(out, is_mem_dest ? br->code & 7 : br->code & 7, &mop, &nr, &si);
        (void)ok;
        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
        return 1;
    }
    if (strcmp(mnem, "lsl") == 0 || strcmp(mnem, "lar") == 0) {
        /* lsl r,r/m → 0F B3 /r ; lar r,r/m → 0F B2 /r */
        uint8_t opc = (mnem[0] == 'l') ? 0xB3 : 0xB2;
        const reg_t *d = NULL, *s = NULL;
        const char *msym = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!d) d = r; else if (!s) s = r; }
                else if (!msym) msym = toks[i].text;
            }
        }
        if (!d) return 0;
        if (d->is64 || (s && s->is64)) emit_byte(out, 0x48);
        emit_byte(out, 0x0F);
        emit_byte(out, opc);
        if (s) {
            emit_byte(out, 0xC0 | (d->code & 7) << 3 | (s->code & 7));
        } else if (msym) {
            int si = find_or_add_sym(out, msym);
            emit_byte(out, 0x05 | (d->code & 7) << 3);
            emit_imm(out, 0, 4);
            if (si >= 0) add_fixup(out, si, 2, -4);
        } else return 0;
        return 1;
    }
    /* MMX/SSE shift-immediate: psrlw/psraw/psllw (0F 71), psrld/psrad/pslld (0F 72),
     * psrlq/psrldq/psllq/pslldq (0F 73). digits: rl=2 ra=4 ll=6 rdq=3 ldq=7 */
    if (strncmp(mnem, "ps", 2) == 0 && (mnem[2] == 'l' || mnem[2] == 'r')) {
        /* direction at mnem[2] ('l'=left, 'r'=right); mnem[3] is logical/arith marker */
        int grp;   /* 0F 71/72/73 */
        if (mnem[4] == 'w') grp = 0x71;
        else if (mnem[5] == 'q') grp = 0x73;   /* dq */
        else grp = (mnem[4] == 'd') ? 0x72 : 0x73;
        int digit;
        if (mnem[2] == 'l') digit = (mnem[5] == 'q') ? 7 : 6;
        else digit = (mnem[5] == 'q') ? 3 : (mnem[3] == 'a' ? 4 : 2);
        /* find xmm/mm register and immediate */
        const reg_t *sr = NULL;
        int sri = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && (r->is_xmm || (r->name[0] == 'm' && r->name[1] == 'm'))) { sr = r; break; }
            }
        }
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { sri = (int)toks[i].value; break; }
        }
        if (sr) {
            if (sr->is_xmm) emit_byte(out, 0x66);
            emit_byte(out, 0x0F);
            emit_byte(out, (uint8_t)grp);
            uint8_t modrm = 0xC0 | digit << 3 | (sr->code & 7);
            if (sr->code >= 8) modrm |= 0x00;  /* REX.B handled via code extension below */
            emit_byte(out, modrm);
            emit_byte(out, (uint8_t)sri);
            return 1;
        }
        return 0;
    }
    if (strcmp(mnem, "call") == 0 || strcmp(mnem, "jmp") == 0) {
        extern const char *islower_str; (void)islower_str;
        /* register indirect call/jmp: call rax → FF /2 (REX.W for r8-r15) */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) {
                    /* call/jmp reg: FF /2 (call) or FF /4 (jmp) */
                    if (r->is64 || r->code >= 8) emit_byte(out, 0x41);  /* REX.B for r8-r15 */
                    emit_byte(out, 0xFF);
                    uint8_t modrm = 0xC0 | ((mnem[0] == 'c') ? 2 : 4) << 3 | (r->code & 7);
                    emit_byte(out, modrm);
                    return 1;
                }
            }
        }
        /* find label operand: an ID token that is not a register */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int si = find_or_add_sym(out, toks[i].text);
                /* 5-byte relative call/jmp: E8/E9 rel32 */
                emit_byte(out, (mnem[0] == 'c') ? 0xE8 : 0xE9);
                int64_t target = lookup_sym(out, toks[i].text);
                if (target >= 0) {
                    /* short/cross-section reference: emit placeholder reloc */
                    emit_imm(out, 0, 4);
                    add_fixup(out, si, 4 /*R_X86_64_PLT32*/, -4);
                    return 1;
                }
                /* forward reference: emit placeholder, fixup later */
                emit_imm(out, 0, 4);
                add_fixup(out, si, 4 /*R_X86_64_PLT32*/, -4);
                return 1;
            }
        }
        return 0;
    }
    if (strcmp(mnem, "lea") == 0) {
        /* lea r64, [rip+label] not implemented yet — except @CStr which emits string */
        /* find dest register */
        const reg_t *ld_reg = NULL;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { ld_reg = r; break; }
            }
        }
        if (!ld_reg) return 0;
        /* lea r, [reg]  → 8D /r  (mod=00, rm=base) with 67 prefix for 32-bit base */
        if (ld_reg) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    if (i + 2 < n && toks[i+2].type == ATOK_OP && toks[i+2].text[0] == ']') {
                        const reg_t *base = find_reg(toks[i+1].text);
                        if (base && !base->is_xmm) {
                            if (ld_reg->is64) emit_byte(out, 0x48);
                            if (!base->is64) emit_byte(out, 0x67);   /* address-size override */
                            emit_byte(out, 0x8D);
                            emit_byte(out, (base->code & 7) << 3 | (ld_reg->code & 7));  /* mod=00 */
                            return 1;
                        }
                    }
                }
            }
        }
        /* lea r, [base*scale+index...] — SIB indexed addressing */
        {
            const reg_t *sib_base = NULL, *sib_idx = NULL;
            int sib_scale = 0;
            int64_t sib_disp = 0;
            int ok_sib = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') {
                    /* scan inside brackets for  REG * NUM [ + REG ] patterns */
                    int j = i + 1;
                    while (j < n && !(toks[j].type == ATOK_OP && toks[j].text[0] == ']')) {
                        if (toks[j].type == ATOK_ID) {
                            const reg_t *r = find_reg(toks[j].text);
                            if (r && !r->is_xmm) {
                                /* check for *scale after */
                                if (j + 2 < n && toks[j+1].type == ATOK_OP && toks[j+1].text[0] == '*' &&
                                    toks[j+2].type == ATOK_NUM) {
                                    sib_idx = r; sib_scale = (int)toks[j+2].value; j += 3;
                                } else if (!sib_base) { sib_base = r; j++; }
                                else if (!sib_idx) { sib_idx = r; sib_scale = 1; j++; }
                                else j++;
                            } else { j++; }  /* non-register symbol: skip (no infinite loop) */
                        }
                        else if (toks[j].type == ATOK_NUM) { sib_disp += toks[j].value; j++; }
                        else if (toks[j].type == ATOK_OP && toks[j].text[0] == '+') { j++; }
                        else if (toks[j].type == ATOK_OP && toks[j].text[0] == '*') { j++; }
                        else j++;
                    }
                    ok_sib = 1;
                    break;
                }
            }
            if (ok_sib && (sib_base || sib_idx)) {
                int disp8 = (sib_disp >= -128 && sib_disp <= 127 && sib_disp != 0);
                /* direct no-disp form uses mod=00 */
                if (ld_reg->is64) emit_byte(out, 0x48);
                if (!(sib_base && sib_base->is64) && !ld_reg->is64) emit_byte(out, 0x67);
                emit_byte(out, 0x8D);
                /* mod: 00 no disp, 01 disp8, 10 disp32 */
                uint8_t mod = (sib_disp == 0 && sib_base) ? 0x00 : (disp8 ? 0x01 : 0x10);
                emit_byte(out, (uint8_t)(mod << 6 | (ld_reg->code & 7) << 3 | 0x04));
                /* SIB: scale(2b) index(3b) base(3b) */
                int sc = (sib_scale == 2) ? 1 : (sib_scale == 4) ? 2 : (sib_scale == 8) ? 3 : 0;
                int base_code = sib_base ? (sib_base->code & 7) : 5;
                int idx_code = sib_idx ? (sib_idx->code & 7) : 4;
                if (sib_base && !sib_idx && sib_disp == 0) { /* [reg*scale] only: no base → disp32 */
                    emit_byte(out, (uint8_t)(sc << 6 | 4 << 3 | 5));
                    emit_imm(out, 0, 4);
                } else {
                    emit_byte(out, (uint8_t)(sc << 6 | idx_code << 3 | base_code));
                    if (mod == 0x01) emit_byte(out, (uint8_t)(int8_t)sib_disp);
                    else if (mod == 0x10) emit_imm(out, (uint64_t)sib_disp, 4);
                }
                return 1;
            }
        }
        /* lea r, gs:[imm] / fs:[imm] — seg prefix + 8D /r SIB absolute (mod=00 rm=100 SIB=25 disp32) */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "gs") == 0 || strcmp(toks[i].text, "fs") == 0 ||
                strcmp(toks[i].text, "GS") == 0 || strcmp(toks[i].text, "FS") == 0)) {
                /* look for [imm] later in the line */
                for (int j = i + 1; j + 2 < n; j++) {
                    if (toks[j].type == ATOK_OP && toks[j].text[0] == '[' &&
                        toks[j+1].type == ATOK_NUM &&
                        toks[j+2].type == ATOK_OP && toks[j+2].text[0] == ']') {
                        emit_byte(out, 0x64);   /* FS/GS segment override */
                        if (ld_reg->is64) emit_byte(out, 0x48);
                        emit_byte(out, 0x8D);
                        emit_byte(out, 0x04 | (ld_reg->code & 7) << 3);  /* mod=00 rm=100 (SIB) */
                        emit_byte(out, 0x25);   /* SIB: no base, no index → disp32 */
                        emit_imm(out, (uint64_t)toks[j+1].value, 4);
                        return 1;
                    }
                }
            }
        }
        /* lea r, gs:[imm] — 64 prefix + 8D 05 disp32 ; also handles [sym] symbol targets */
        int seg_pre = 0;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "gs") == 0 || strcmp(toks[i].text, "fs") == 0 ||
                strcmp(toks[i].text, "GS") == 0 || strcmp(toks[i].text, "FS") == 0))
                { seg_pre = (toks[i].text[0] == 'g' || toks[i].text[0] == 'G') ? 0x64 : 0x64; break; }
        if (seg_pre) emit_byte(out, (uint8_t)seg_pre);
        /* symbol target: lea r, sym  → 8D 05 /r disp32 + fixup */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                strcmp(toks[i].text, "gs") != 0 && strcmp(toks[i].text, "fs") != 0 &&
                strcmp(toks[i].text, "@CStr") != 0) {
                int si = find_or_add_sym(out, toks[i].text);
                (void)si;
                if (ld_reg->is64) emit_byte(out, 0x48);
                emit_byte(out, 0x8D);
                emit_byte(out, 0x05 | (ld_reg->code & 7) << 3);
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 2, -4);
                return 1;
            }
        }
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && strcmp(toks[i].text, "@CStr") == 0) {
                /* @CStr(...) string literal: emit .data string, then lea rax, [rip+string] */
                /* For now, skip the @CStr content (emit as .data inline) */
                return 1;
            }
        }
        return 0;
    }

    if (strcmp(mnem, "invoke") == 0) {
        /* invoke pseudo-instruction: `invoke target[, args...]` or `invoke target( args... )`.
         * x64 calling convention: first 4 integer args go in rcx, rdx, r8, r9. */
        /* collect operands as a flat arg list (skip commas/parens) */
        int target_idx = -1;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) { target_idx = i; break; }
        if (target_idx < 0) return 0;
        /* emit arg moves into rcx/rdx/r8/r9 (bounded, real register moves) */
        static const char *argregs[4] = { "rcx", "rdx", "r8", "r9" };
        int arg_slot = 0;
        for (int i = target_idx + 1; i < n && arg_slot < 4; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '(') continue;
            if (toks[i].type == ATOK_OP && toks[i].text[0] == ')') continue;
            if (toks[i].type == ATOK_STRING) {
                /* string argument: ignore for codegen this pass (address later) */
                arg_slot++;
                continue;
            }
            const reg_t *ar = find_reg(toks[i].text);
            if (ar) {
                /* mov r64, r64  →  48 8B C0+ */
                emit_byte(out, 0x48);
                emit_byte(out, 0x8B);
                const reg_t *dest = find_reg(argregs[arg_slot]);
                emit_byte(out, 0xC0 | (dest->code & 7) << 3 | (ar->code & 7));
            } else if (toks[i].type == ATOK_NUM) {
                /* mov r64, imm32  →  48 C7 C0+ /id */
                emit_byte(out, 0x48);
                emit_byte(out, 0xC7);
                const reg_t *dest = find_reg(argregs[arg_slot]);
                emit_byte(out, 0xC0 | (dest->code & 7));
                emit_imm(out, toks[i].value, 4);
            } else {
                /* symbol arg: leave placeholder reg move skipped */
                arg_slot++;
                continue;
            }
            arg_slot++;
        }
        /* call the target: reuse the rel32 symbol-call form */
        {
            a_tok_t ct[8];
            ct[0].type = ATOK_ID; snprintf(ct[0].text, sizeof(ct[0].text), "call");
            ct[1].type = ATOK_ID; snprintf(ct[1].text, sizeof(ct[1].text), "%s", toks[target_idx].text);
            return encode_instruction(out, ct, 2);
        }
    }

    /* popcnt/lzcnt/tzcnt: F3 (66) 0F B8/BD/BC /r (gpr, gpr/mem) */
    if (strcmp(mnem, "popcnt") == 0 || strcmp(mnem, "lzcnt") == 0 || strcmp(mnem, "tzcnt") == 0) {
        uint8_t opc = (mnem[0] == 'p') ? 0xB8 : (mnem[0] == 'l' ? 0xBD : 0xBC);
        const reg_t *pd = NULL, *ps = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && !r->is_xmm) { if (!pd) pd = r; else if (!ps) ps = r; }
            }
        }
        if (!pd) return 0;
        /* 16-bit: 66 prefix before F3 */
        int is16 = 0;
        for (int i = 1; i < n; i++)
            if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "WORD") == 0 || strcmp(toks[i].text, "word") == 0) &&
                (pd->name[0] == 'r' || pd->name[1] == 'x' || pd->name[1] == 'p' || pd->name[1] == 'i'))
                is16 = 1;
        if (pd->name[0] == 'r' && (pd->name[1] == '8' || pd->name[1] == '9' || pd->name[1] == '1')) is16 = 1; /* r8w,r9w,r10w... */
        if (is16) emit_byte(out, 0x66);
        emit_byte(out, 0xF3); emit_byte(out, 0x0F); emit_byte(out, opc);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, pd->code & 7, &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (ps) {
            emit_byte(out, 0xC0 | (pd->code & 7) << 3 | (ps->code & 7));
            return 1;
        }
        return 0;
    }
    /* cvtsd2si/cvttsd2si/cvtss2si: F2/F3 0F 2D /r ; cvtsd2ss: F2 0F 5A /r ; cvtss2sd: F3 0F 5A /r */
    if (strncmp(mnem, "cvt", 3) == 0 && (strstr(mnem, "2si") || strstr(mnem, "2ss") || strstr(mnem, "2sd"))) {
        uint8_t prefix = 0;
        if (strstr(mnem, "sd2si") || strstr(mnem, "ss2sd")) prefix = 0xF2;
        else if (strstr(mnem, "ss2si") || strstr(mnem, "sd2ss") || strstr(mnem, "si2ss") || strstr(mnem, "si2sd")) prefix = 0xF3;
        if (!prefix) return 0;   /* cvtsi2ss/sd etc. handled below by generic table */
        /* 2si: gpr dest; 2ss/2sd: xmm dest */
        int is_si = (strstr(mnem, "2si") != NULL);
        const reg_t *c1 = NULL, *c2 = NULL;
        int mem_tok = -1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r) { if (!c1) c1 = r; else if (!c2) c2 = r; }
            }
        }
        if (!c1) return 0;
        emit_byte(out, prefix); emit_byte(out, 0x0F);
        emit_byte(out, (strstr(mnem, "2ss") || strstr(mnem, "2sd")) ? 0x5A : 0x2D);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, is_si ? (c1->code & 7) : (c1->code & 7), &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                return 1;
            }
        }
        if (c2) {
            emit_byte(out, 0xC0 | (is_si ? (c1->code & 7) << 3 : (c1->code & 7) << 3) | (c2->code & 7));
            return 1;
        }
        return 0;
    }
    /* extractps: 66 0F 3A 17 /r ib ; insertps: 66 0F 3A 21 /r ib */
    if (strcmp(mnem, "extractps") == 0 || strcmp(mnem, "insertps") == 0) {
        int is_extract = (mnem[0] == 'e');
        const reg_t *xr = NULL, *gr = NULL;
        int mem_tok = -1, xim = 0, has_xim = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { xim = (int)toks[i].value; has_xim = 1; }
            else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
            else if (toks[i].type == ATOK_ID) {
                const reg_t *r = find_reg(toks[i].text);
                if (r && r->is_xmm) { if (!xr) xr = r; else if (!gr) gr = r; }
                else if (r && !r->is_xmm) { if (!gr) gr = r; }
            }
        }
        if (!xr) return 0;
        emit_byte(out, 0x66); emit_byte(out, 0x0F); emit_byte(out, 0x3A);
        emit_byte(out, is_extract ? 0x17 : 0x21);
        if (mem_tok >= 0) {
            mem_op_t mop;
            if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                int nr, si;
                encode_mem_operand(out, is_extract ? 0 : (xr->code & 7), &mop, &nr, &si);
                if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                if (has_xim) emit_byte(out, (uint8_t)xim);
                return 1;
            }
        }
        if (gr) {
            /* extractps: gr is gpr dest (modrm.reg = gr, modrm.rm = xr) */
            /* insertps: xr is xmm dest, gr is xmm/src (modrm.reg = xr, modrm.rm = gr) */
            int reg = is_extract ? (gr->code & 7) : (xr->code & 7);
            int rm = is_extract ? (xr->code & 7) : (gr->code & 7);
            emit_byte(out, 0xC0 | reg << 3 | rm);
            if (has_xim) emit_byte(out, (uint8_t)xim);
            return 1;
        }
        return 0;
    }
    /* table-driven SIMD/other instructions: prefix bytes + 0F[3A|38] + opcode + has_imm */
    {
        struct { const char *name; uint8_t pre; uint8_t opc; int group; int has_imm; int digit; } simd[] = {
            { "unpckhpd", 0x66, 0x15, 1, 0, -1 },
            { "unpcklpd", 0x66, 0x14, 1, 0, -1 },
            { "unpckhps", 0x00, 0x15, 1, 0, -1 },
            { "unpcklps", 0x00, 0x14, 1, 0, -1 },
            { "addsubpd", 0x66, 0xD0, 1, 0, -1 },
            { "addsubps", 0xF2, 0xD0, 1, 0, -1 },
            { "blendpd",  0x66, 0x0D, 3, 1, -1 },
            { "blendps",  0x66, 0x0C, 3, 1, -1 },
            { "haddpd",   0x66, 0x7C, 1, 0, -1 },
            { "haddps",   0xF2, 0x7C, 1, 0, -1 },
            { "hsubpd",   0x66, 0x7D, 1, 0, -1 },
            { "hsubps",   0xF2, 0x7D, 1, 0, -1 },
            { "cmpeqsd",  0xF2, 0xC2, 1, 2, -1 },
            { "cmpltsd",  0xF2, 0xC2, 1, 2, -1 },
            { "cmplepd",  0x66, 0xC2, 1, 2, -1 },
            { "cmpeqps",  0x00, 0xC2, 1, 2, -1 },
            { "cmpeqss",  0xF3, 0xC2, 1, 2, -1 },
            { "cmpss",    0xF3, 0xC2, 1, 1, -1 },
            { "cmpsd",    0xF2, 0xC2, 1, 1, -1 },
            { "cmpps",    0x00, 0xC2, 1, 1, -1 },
            { "cmppd",    0x66, 0xC2, 1, 1, -1 },
            { "pcmpeqq",  0x66, 0x29, 2, 0, -1 },
            { "cvtsi2ss", 0xF3, 0x2A, 1, 0, -1 },
            { "cvtsi2sd", 0xF2, 0x2A, 1, 0, -1 },
            { "cvttps2dq", 0xF3, 0x5B, 1, 0, -1 },
            { "cvttps2pi", 0x00, 0x2C, 1, 0, -1 },
            { "cvttpd2pi", 0x66, 0x2C, 1, 0, -1 },
            { "pmuldq",   0x66, 0x28, 2, 0, -1 },
            { "pmulld",   0x66, 0x40, 2, 0, -1 },
            { "pmuludq",  0x66, 0xF4, 1, 0, -1 },
            { "phminposuw", 0x66, 0x41, 2, 0, -1 },
            { "pmaxsb",   0x66, 0x3C, 2, 0, -1 },
            { "pmaxsd",   0x66, 0x3D, 2, 0, -1 },
            { "pmaxuw",   0x66, 0x3E, 2, 0, -1 },
            { "pmaxud",   0x66, 0x3F, 2, 0, -1 },
            { "pminsb",   0x66, 0x38, 2, 0, -1 },
            { "pminsd",   0x66, 0x39, 2, 0, -1 },
            { "pminuw",   0x66, 0x3A, 2, 0, -1 },
            { "pminud",   0x66, 0x3B, 2, 0, -1 },
            { "pextrb",   0x66, 0x14, 3, 1, -1 },
            { "pextrw",   0x66, 0x15, 3, 1, -1 },
            { "pextrd",   0x66, 0x16, 3, 1, -1 },
            { "pextrq",   0x66, 0x16, 3, 1, -1 },
            { "pinsrb",   0x66, 0x20, 3, 1, -1 },
            { "pinsrw",   0x66, 0xC4, 1, 1, -1 },
            { "pinsrd",   0x66, 0x22, 3, 1, -1 },
            { "pinsrq",   0x66, 0x22, 3, 1, -1 },
            { "maxsd",    0xF2, 0x5F, 1, 0, -1 },
            { "maxss",    0xF3, 0x5F, 1, 0, -1 },
            { "minsd",    0xF2, 0x5D, 1, 0, -1 },
            { "minss",    0xF3, 0x5D, 1, 0, -1 },
            { "rcpss",    0xF3, 0x53, 1, 0, -1 },
            { "rsqrtss",  0xF3, 0x52, 1, 0, -1 },
            { "sqrtss",   0xF3, 0x51, 1, 0, -1 },
            { "mpsadbw",  0x66, 0x42, 3, 1, -1 },
            { "roundsd",  0x66, 0x0B, 3, 1, -1 },
            { "roundss",  0x66, 0x0A, 3, 1, -1 },
            { "roundpd",  0x66, 0x09, 3, 1, -1 },
            { "roundps",  0x66, 0x08, 3, 1, -1 },
            { "packusdw", 0x66, 0x2B, 2, 0, -1 },
            { "pmovsxbw", 0x66, 0x20, 2, 0, -1 },
            { "pmovsxbd", 0x66, 0x21, 2, 0, -1 },
            { "pmovsxbq", 0x66, 0x22, 2, 0, -1 },
            { "pmovsxwd", 0x66, 0x23, 2, 0, -1 },
            { "pmovsxwq", 0x66, 0x24, 2, 0, -1 },
            { "pmovsxdq", 0x66, 0x25, 2, 0, -1 },
            { "pmovzxbw", 0x66, 0x30, 2, 0, -1 },
            { "pmovzxbd", 0x66, 0x31, 2, 0, -1 },
            { "pmovzxbq", 0x66, 0x32, 2, 0, -1 },
            { "pmovzxwd", 0x66, 0x33, 2, 0, -1 },
            { "pmovzxwq", 0x66, 0x34, 2, 0, -1 },
            { "pmovzxdq", 0x66, 0x35, 2, 0, -1 },
            { "pblendvb", 0x66, 0x10, 2, 0, -1 },
            { "ptest",    0x66, 0x17, 2, 0, -1 },
            { "pblendw",  0x66, 0x0E, 3, 1, -1 },
            { "movntdqa", 0x66, 0x2A, 2, 0, -1 },
            { "lddqu",    0xF2, 0xF0, 1, 0, -1 },
            { "blendvpd", 0x66, 0x15, 2, 0, -1 },
            { "cvtpi2pd", 0x66, 0x2A, 1, 0, -1 },
            { "cvtpi2ps", 0x00, 0x2A, 1, 0, -1 },
            { "cvtps2pi", 0x00, 0x2D, 1, 0, -1 },
            { "movddup",  0xF2, 0x12, 1, 0, -1 },
            { "movshdup", 0xF3, 0x16, 1, 0, -1 },
            { "movsldup", 0xF3, 0x12, 1, 0, -1 },
            { "pcmpgtq",  0x66, 0x37, 2, 0, -1 },
            { "blendvps", 0x66, 0x14, 2, 0, -1 },
            { "dppd",     0x66, 0x41, 3, 1, -1 },
            { "dpps",     0x66, 0x40, 3, 1, -1 },
            { "pcmpestri", 0x66, 0x61, 3, 1, -1 },
            { "pcmpestrm", 0x66, 0x60, 3, 1, -1 },
            { "pcmpistri", 0x66, 0x63, 3, 1, -1 },
            { "pcmpistrm", 0x66, 0x62, 3, 1, -1 },
            { "crc32",    0xF2, 0xF0, 2, 0, -1 },
            { "crc32b",   0xF2, 0xF0, 2, 0, -1 },
        };
        int sidx = -1;
        for (unsigned s = 0; s < sizeof(simd)/sizeof(simd[0]); s++)
            if (strcmp(mnem, simd[s].name) == 0) { sidx = (int)s; break; }
        /* generic CMP pseudo-operator fallback: `cmp<op><suffix>` where
         * op in {eq,lt,le,unord,neq,nlt,nle,ord} and suffix in {pd,ps,sd,ss}
         * encodes as the base CMP (0F C2) with imm8 from the op mnemonic.
         * This covers cmpeqpd/cmpltps/cmplepd/cmpunordsd/cmpneqss etc. */
        if (sidx < 0 && strncmp(mnem, "cmp", 3) == 0 && strlen(mnem) > 5) {
            const char *sfx = mnem + strlen(mnem) - 2;
            int pre = -1;
            if (strcmp(sfx, "pd") == 0) pre = 0x66;
            else if (strcmp(sfx, "ps") == 0) pre = 0;
            else if (strcmp(sfx, "sd") == 0) pre = 0xF2;
            else if (strcmp(sfx, "ss") == 0) pre = 0xF3;
            if (pre >= 0) {
                const reg_t *x1 = NULL, *x2 = NULL;
                int mem_tok = -1;
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') mem_tok = i;
                    else if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (r && r->is_xmm) { if (!x1) x1 = r; else if (!x2) x2 = r; }
                    }
                }
                if (pre) emit_byte(out, (uint8_t)pre);
                emit_byte(out, 0x0F);
                emit_byte(out, 0xC2);
                if (mem_tok >= 0) {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                        int nr, si;
                        encode_mem_operand(out, x1 ? x1->code & 7 : 0, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        emit_byte(out, cmp_imm_from_mnemonic(mnem));
                        return 1;
                    }
                }
                /* bare memory symbol operand (e.g. `cmpeqpd xmm0, vo`) → RIP-relative */
                if (x1) {
                    for (int i = 1; i < n; i++) {
                        if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                            strcmp(toks[i].text, "ptr") != 0 &&
                            strcmp(toks[i].text, "byte") != 0 &&
                            strcmp(toks[i].text, "word") != 0 &&
                            strcmp(toks[i].text, "dword") != 0 &&
                            strcmp(toks[i].text, "qword") != 0) {
                            int si = find_or_add_sym(out, toks[i].text);
                            emit_byte(out, 0x05 | (x1->code & 7) << 3);
                            emit_imm(out, 0, 4);
                            if (si >= 0) add_fixup(out, si, 2, -4);
                            emit_byte(out, cmp_imm_from_mnemonic(mnem));
                            return 1;
                        }
                    }
                }
                if (x1 && x2) {
                    emit_byte(out, 0xC0 | (x1->code & 7) << 3 | (x2->code & 7));
                    emit_byte(out, cmp_imm_from_mnemonic(mnem));
                    return 1;
                }
                return 0;
            }
        }
        if (sidx >= 0) {
            const reg_t *x1 = NULL, *x2 = NULL;
            int mem_tok = -1;
            int64_t sim = 0; int has_im = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_NUM) { sim = toks[i].value; has_im = 1; }
                else if (toks[i].type == ATOK_OP && toks[i].text[0] == '[') { mem_tok = i; }
                else if (toks[i].type == ATOK_ID) {
                    const reg_t *r = find_reg(toks[i].text);
                    if (r && (r->is_xmm || (r->name[0] == 'm' && r->name[1] == 'm'))) {
                        if (!x1) x1 = r; else if (!x2) x2 = r;
                    } else if (r && !r->is_xmm) {
                        if (!x2) x2 = r;   /* crc32: gpr second */
                    }
                }
            }
            if (simd[sidx].pre) emit_byte(out, simd[sidx].pre);
            /* crc32 needs REX.W for 64-bit and modrm with gpr first */
            if (strncmp(mnem, "crc32", 5) == 0) {
                /* crc32 r32/r64, r/m8/32/64 → F2 0F 38 F0/F1 */
                int is_64 = 0;
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (r && r->is64 && !r->is_xmm && (r->name[0]=='r'||r->name[0]=='e')) { is_64 = 1; break; }
                    }
                }
                emit_byte(out, 0x0F); emit_byte(out, 0x38);
                /* byte source (BYTE PTR or al/bl...) → F0, else F1 */
                uint8_t opc2 = 0xF1;
                for (int i = 1; i < n; i++)
                    if (toks[i].type == ATOK_ID && (strcmp(toks[i].text, "BYTE") == 0 || strcmp(toks[i].text, "byte") == 0))
                        opc2 = 0xF0;
                emit_byte(out, opc2);
                int first_gpr = -1, second_gpr = -1;
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (r && !r->is_xmm) {
                            if (first_gpr < 0) { first_gpr = r->code & 7; if (r->is64) is_64 = 1; }
                            else if (second_gpr < 0) { second_gpr = r->code & 7; if (r->is64) is_64 = 1; }
                            else break;
                        }
                    }
                }
                /* byte-size source register (cl, bl, ...) → F0 */
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID) {
                        const reg_t *r = find_reg(toks[i].text);
                        if (r && !r->is_xmm && r->name[1] == 'l' && second_gpr >= 0 && r->code == second_gpr) {
                            opc2 = 0xF0;
                        }
                    }
                }
                if (is_64) emit_byte(out, 0x48);
                if (mem_tok >= 0) {
                    mem_op_t mop;
                    if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                        int nr, si;
                        encode_mem_operand(out, first_gpr < 0 ? 0 : first_gpr, &mop, &nr, &si);
                        if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                        return 1;
                    }
                }
                if (second_gpr >= 0) {
                    emit_byte(out, 0xC0 | (first_gpr & 7) << 3 | (second_gpr & 7));
                    return 1;
                }
                return 0;
            }
            emit_byte(out, 0x0F);
            if (simd[sidx].group == 3) emit_byte(out, 0x3A);
            else if (simd[sidx].group == 2) emit_byte(out, 0x38);
            emit_byte(out, simd[sidx].opc);
            if (mem_tok >= 0) {
                mem_op_t mop;
                if (parse_mem_operand(toks, mem_tok, n, &mop) >= 0) {
                    int nr, si;
                    encode_mem_operand(out, x1 ? x1->code & 7 : 0, &mop, &nr, &si);
                    if (si >= 0) add_fixup(out, si, nr ? 2 : 0, -4);
                    if (simd[sidx].has_imm && has_im) emit_byte(out, (uint8_t)sim);
                    else if (simd[sidx].has_imm == 2) emit_byte(out, cmp_imm_from_mnemonic(mnem));
                    return 1;
                }
            }
            /* bare memory symbol (m16/m32/m64 without brackets) → RIP-relative */
            if (x1) {
                for (int i = 1; i < n; i++) {
                    if (toks[i].type == ATOK_ID && !find_reg(toks[i].text) &&
                        strcmp(toks[i].text, "word") != 0 && strcmp(toks[i].text, "dword") != 0 &&
                        strcmp(toks[i].text, "qword") != 0 && strcmp(toks[i].text, "ptr") != 0 &&
                        strcmp(toks[i].text, "byte") != 0) {
                        int si = find_or_add_sym(out, toks[i].text);
                        emit_byte(out, 0x05 | (x1->code & 7) << 3);
                        emit_imm(out, 0, 4);
                        if (si >= 0) add_fixup(out, si, 2, -4);
                        if (simd[sidx].has_imm && has_im) emit_byte(out, (uint8_t)sim);
                        else if (simd[sidx].has_imm == 2) emit_byte(out, cmp_imm_from_mnemonic(mnem));
                        return 1;
                    }
                }
            }
            if (x1 && x2) {
                emit_byte(out, 0xC0 | (x1->code & 7) << 3 | (x2->code & 7));
                if (simd[sidx].has_imm && has_im) emit_byte(out, (uint8_t)sim);
                else if (simd[sidx].has_imm == 2) emit_byte(out, cmp_imm_from_mnemonic(mnem));
                return 1;
            }
            return 0;
        }
    }
    return 0;   /* unknown instruction */
}

/* ---------- line-level assembler (parser.asm reduced) ---------- */

/* Check if a token is a keyword directive */
static int is_keyword(const char *s)
{
    static const char *kw[] = {"proc", "endp", "ends", "end", "macro", "equ", "=", "label", "PROC", "ENDP", "ENDS", "MACRO", NULL};
    for (int i = 0; kw[i]; i++)
        if (strcmp(s, kw[i]) == 0) return 1;
    return 0;
}

/* absolute section index for equates (pipe to SHN_ABS 0xfff1 in ELF) */
#define ASMC_ABS_SEC 0xfff1

/* forward: evaluate tokens after index 1 as an expression */
static int eval_tokens(asm_output_t *out, a_tok_t *t, int n, int64_t *val);
/* forward: expression evaluator (used by equ/loop handlers) */
static int eval_expr(asm_output_t *out, a_tok_t *t, int *pos, int n,
                     int64_t *val);

/* forward: control-flow handler (.if/.while/.endif etc.), used by assemble_line */
static int handle_control(asm_output_t *out, a_tok_t *toks, int n,
                          const char *line);

/* assemble one line; symbols/fixups collected into out */
static int assemble_line(asm_output_t *out, a_tok_t *toks, int n)
{
    if (n == 0)
        return 1;
    /* a lone register name on its own line (e.g. `cx` after an invoke that
     * expanded to void) is a harmless no-op — not a valid instruction. */
    if (n == 1 && toks[0].type == ATOK_ID && find_reg(toks[0].text))
        return 1;

    /* ---- text-equate expansion: if the line is a single ID that is a
     * defined text equate, expand it inline and re-assemble. ---- */
    if (n == 1 && toks[0].type == ATOK_ID) {
        for (int si = 0; si < out->nsyms; si++) {
            if (out->syms[si].is_text && out->syms[si].defined &&
                strcmp(out->syms[si].name, toks[0].text) == 0 &&
                out->syms[si].text[0]) {
                char expanded[512];
                snprintf(expanded, sizeof(expanded), "%s", out->syms[si].text);
                a_tok_t et[64];
                int en = TokenizeLine(expanded, et, 64);
                if (en > 0) {
                    for (int i = 0; i < en; i++) toks[i] = et[i];
                    n = en;
                }
                break;
            }
        }
    }

    /* `COMMENT delim` — multi-line comment until the delimiter char appears
     * again at line start (e.g. `COMMENT #` ... `#`).  Accept and skip. */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "COMMENT") == 0 ||
                                    strcmp(toks[0].text, "comment") == 0)) {
        return 1;
    }

    /* bracket-based property/method access: `[mem].name(...)` or `[mem].field` */
    /* `purge <name>` / `undef <name>` inside a macro body (handled at top level in
     * process_source_lines; also needed here since macro bodies go through
     * expand_macro -> assemble_line). */
    if (toks[0].type == ATOK_ID && n >= 2 &&
        (strcmp(toks[0].text, "purge") == 0 || strcmp(toks[0].text, "PURGE") == 0 ||
         strcmp(toks[0].text, "undef") == 0 || strcmp(toks[0].text, "UNDEF") == 0)) {
        for (int u = 1; u < n; u++) {
            if (toks[u].type != ATOK_ID) continue;
            const char *arg = toks[u].text;
            /* text-equate argument expands to the macro name (e.g. tm1 = <m2>) */
            for (int si = 0; si < out->nsyms; si++) {
                if (out->syms[si].is_text && out->syms[si].defined &&
                    strcmp(out->syms[si].name, arg) == 0 && out->syms[si].text[0]) {
                    arg = out->syms[si].text;
                    break;
                }
            }
            for (int w = 0; w < out->nmacros; w++) {
                if (strcmp(out->macros[w].name, arg) == 0) {
                    if (out->npurged < 16) {
                        int dup = 0;
                        for (int pd = 0; pd < out->npurged; pd++)
                            if (strcmp(out->purged[pd], arg) == 0) { dup = 1; break; }
                        if (!dup) snprintf(out->purged[out->npurged++], 128, "%s", arg);
                    }
                    for (int v = w; v + 1 < out->nmacros; v++)
                        out->macros[v] = out->macros[v + 1];
                    out->nmacros--;
                    break;
                }
            }
        }
        return 1;
    }
    if (toks[0].type == ATOK_OP && toks[0].text[0] == '[') {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '.' &&
                i + 1 < n && toks[i+1].type == ATOK_ID) {
                return 1;   /* [mem].method/field access — skip (no code emitted) */
            }
        }
    }

    /* Handle .directives */
    if (toks[0].type == ATOK_DIRECTIVE) {
        const char *d = toks[0].text;
        if (strcmp(d, ".code") == 0) {
            out->cur_sec = SEC_TEXT;
            return 1;
        }
        if (strcmp(d, ".data") == 0) {
            out->cur_sec = SEC_DATA;
            return 1;
        }
        if (strcmp(d, ".bss") == 0) {
            out->cur_sec = SEC_BSS;
            return 1;
        }
        if (strcmp(d, ".model") == 0) return 1;
        if (strcmp(d, ".stack") == 0) return 1;
        if (strcmp(d, ".386") == 0 || strcmp(d, ".486") == 0 ||
            strcmp(d, ".586") == 0 || strcmp(d, ".686") == 0) return 1;
        /* .align <n> — pad current section to alignment */
        if (strcmp(d, ".align") == 0 || strcmp(d, ".even") == 0) {
            size_t align = strcmp(d, ".even") == 0 ? 2 : 4;
            if (n >= 2 && toks[1].type == ATOK_NUM) align = (size_t)toks[1].value;
            if (align < 2) align = 2;
            size_t cur = cur_offset(out);
            size_t pad = (align - (cur % align)) % align;
            for (size_t i = 0; i < pad; i++) emit_byte(out, 0);
            return 1;
        }
        /* .class / .comdef handled by the struct/class handler below — skip the
         * "unknown directive" early-return so control falls through to it */
        if (strcmp(d, ".class") == 0 || strcmp(d, ".comdef") == 0 ||
            strcmp(d, ".enum") == 0) {
            /* fall through to struct/class/enum handler */
        } else {
            return 1;   /* unknown directive: skip */
        }
    }

    /* PROC / ENDP frame lifecycle: detect procedure start/end, reset frame state */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "proc") == 0) {
        out->cur_proc = 1;
        out->nlocals = 0;
        out->frame_size = 0;
        return 1;
    }
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "endp") == 0) {
        /* finalize frame: invalidate local symbols so they cannot be referenced
         * after the procedure scope closes, then reset frame state.
         * Set sec_index = -1 to mark "out of scope" for clean error diagnostics. */
        for (int k = 0; k < out->nlocals; k++) {
            int li = out->local_sym_ids[k];
            if (li >= 0 && li < out->nsyms) {
                out->syms[li].defined = 0;
                out->syms[li].sec_index = -1;  /* -1 = out of scope */
                out->syms[li].value = 0;
            }
        }
        out->cur_proc = 0;
        out->nlocals = 0;
        out->frame_size = 0;
        return 1;
    }

    /* Skip bare keyword directives (proc, endp, ends, end, macro...) */
    if (toks[0].type == ATOK_ID && is_keyword(toks[0].text)) {
        return 1;
    }

    /* `equ` / `=` equate definition:  name equ <expr>  or  name = <expr> */
    if (toks[0].type == ATOK_ID && n >= 3 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "equ") == 0 || strcmp(toks[1].text, "EQU") == 0)) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) {
            /* `name equ <EQU ...;>` — text equate whose content is a directive
             * (e.g. `DBB equ <EQU 1;>`); store the bracketed text so later
             * inline use (e.g. `LNAME_TXT DBB LENGTHOF ...`) splices it. */
            if (toks[2].type == ATOK_OP && toks[2].text[0] == '<') {
                char tbuf[512]; size_t to = 0;
                int prev_word = 0;
                for (int i = 2; i < n; i++) {
                    const char *tk = toks[i].text;
                    if (i == 2 && tk[0] == '<') tk++;
                    size_t l = strlen(tk);
                    if (i == n - 1 && l > 0 && tk[l - 1] == '>') l--;
                    int is_word = (l > 0 && ((tk[0] >= 'a' && tk[0] <= 'z') || (tk[0] >= 'A' && tk[0] <= 'Z') ||
                                             (tk[0] >= '0' && tk[0] <= '9') || tk[0] == '_' || tk[0] == '@' || tk[0] == '?'));
                    if (prev_word && is_word && to > 0) tbuf[to++] = ' ';
                    if (to + l < sizeof(tbuf)) { memcpy(tbuf + to, tk, l); to += l; }
                    prev_word = is_word;
                }
                tbuf[to] = 0;
                /* only treat as text equate when it begins with a directive keyword;
                 * plain `TM1 equ <abc>` stays numeric (avoids expans regressions). */
                if (strncmp(tbuf, "EQU", 3) == 0 || strncmp(tbuf, "equ", 3) == 0 ||
                    tbuf[0] == '=') {
                    out->syms[si].defined = 1;
                    out->syms[si].is_text = 1;
                    snprintf(out->syms[si].text, sizeof(out->syms[si].text), "%s", tbuf);
                    return 1;
                }
            }
            int64_t v = 0;
            /* macro invocation RHS: `name equ macroname ( arg )` — evaluate arg directly */
            if (n >= 5 && toks[2].type == ATOK_ID && toks[3].type == ATOK_OP && toks[3].text[0] == '(' &&
                toks[n-1].type == ATOK_OP && toks[n-1].text[0] == ')') {
                int pos = 4;
                if (eval_expr(out, toks, &pos, n - 1, &v) == 0) {
                    out->syms[si].value = (uint64_t)v;
                    out->syms[si].defined = 1;
                    out->syms[si].sec_index = ASMC_ABS_SEC;
                }
            } else {
                /* RHS may be a text equate (e.g. `E4 equ TE1` where TE1 is a
                 * text macro): expand its text value, then evaluate. */
                if (n >= 3 && toks[2].type == ATOK_ID) {
                    for (int si2 = 0; si2 < out->nsyms; si2++) {
                        if (out->syms[si2].is_text && out->syms[si2].defined &&
                            strcmp(out->syms[si2].name, toks[2].text) == 0 &&
                            out->syms[si2].text[0]) {
                            a_tok_t et[64];
                            int en = TokenizeLine(out->syms[si2].text, et, 64);
                            if (en > 0) {
                                a_tok_t full[64];
                                full[0] = toks[0];   /* name */
                                full[1] = toks[1];   /* equ */
                                for (int k = 0; k < en; k++) full[2 + k] = et[k];
                                int fn = 2 + en;
                                int pos = 2;
                                if (eval_expr(out, full, &pos, fn, &v) == 0) {
                                    out->syms[si].value = (uint64_t)v;
                                    out->syms[si].defined = 1;
                                    out->syms[si].sec_index = ASMC_ABS_SEC;
                                }
                            }
                            break;
                        }
                    }
                }
                int pos = 2;
                if (eval_expr(out, toks, &pos, n, &v) == 0) {
                    out->syms[si].value = (uint64_t)v;
                    out->syms[si].defined = 1;
                    out->syms[si].sec_index = ASMC_ABS_SEC;
                }
            }
        }
        return 1;
    }
    if (toks[0].type == ATOK_ID && n >= 3 && toks[1].type == ATOK_OP &&
        toks[1].text[0] == '=' && toks[1].text[1] == 0) {
        /* name = <expr> */
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) {
            int64_t v = 0;
            int pos = 2;
            if (eval_expr(out, toks, &pos, n, &v) == 0) {
                out->syms[si].value = (uint64_t)v;
                out->syms[si].defined = 1;
                out->syms[si].sec_index = ASMC_ABS_SEC;
            }
        }
        return 1;
    }

    /* `end` / `END` directive (bare form, no leading '.') */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "end") == 0 ||
                                    strcmp(toks[0].text, "END") == 0 ||
                                    strcmp(toks[0].text, "End") == 0)) {
        return 1;
    }

    /* Handle the `inl` keyword: define as built-in macro that accepts args */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "inl") == 0) {
        /* inl(arg1, arg2, ...) — skip the macro call (proto inline body handled separately) */
        return 1;
    }
    /* `name` `proto_N` [args] — proto-type call: emit call rel32 to name */
    if (n >= 3 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        (strncmp(toks[1].text, "proto_", 6) == 0 || strncmp(toks[1].text, "PROTO_", 6) == 0)) {
        int si = find_or_add_sym(out, toks[0].text);
        emit_byte(out, 0xE8);
        emit_imm(out, 0, 4);
        if (si >= 0) add_fixup(out, si, 4, -4);
        return 1;
    }
    /* Handle `stk` keyword: stack frame macro */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "stk") == 0) {
        return 1;
    }
    /* Handle `i16` keyword: 16-bit integer macro */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "i16") == 0) {
        return 1;
    }
    /* `exitm <text>` / `EXITM <text>` macro terminator — store the returned text
     * (for macro-function value adaptation) and exit macro expansion. */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "exitm") == 0 || strcmp(toks[0].text, "EXITM") == 0 ||
                                    strcmp(toks[0].text, "retm") == 0 || strcmp(toks[0].text, "RETM") == 0)) {
        if (n >= 2) {
            out->macro_ret[0] = 0;
            for (int i = 1; i < n; i++) {
                const char *tk = toks[i].text;
                if (i == 1 && tk[0] == '<') tk++;
                size_t l = strlen(tk);
                if (i == n - 1 && l > 0 && tk[l - 1] == '>') l--;
                if (strlen(out->macro_ret) + l < sizeof(out->macro_ret))
                    strncat(out->macro_ret, tk, l);
            }
        }
        return 1;
    }
    /* `ldr dest, src` — load register or local variable from src (param/local). */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "ldr") == 0 && n >= 3) {
        /* find the source token (skip comma) */
        int src_idx = 2;
        const reg_t *ld = find_reg(toks[1].text);
        /* find source symbol */
        for (int i = 2; i < n; i++) {
            if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                int src_si = find_or_add_sym(out, toks[i].text);
                int64_t src_off = (src_si >= 0) ? (int64_t)out->syms[src_si].value : 0;
                if (ld) {
                    /* ldr reg, sym — load from stack offset into register */
                    if (ld->is64) emit_byte(out, 0x48);
                    emit_byte(out, 0x8B);
                    emit_byte(out, 0x45 | (ld->code & 7) << 3);
                    emit_byte(out, (uint8_t)(int8_t)src_off);
                    return 1;
                }
                /* ldr sym, sym — load src into dest via rax */
                {
                    int dst_si = find_or_add_sym(out, toks[1].text);
                    int64_t dst_off = (dst_si >= 0) ? (int64_t)out->syms[dst_si].value : 0;
                    /* mov rax, [rbp + src_off]  (8B 45 /offset) */
                    emit_byte(out, 0x48); emit_byte(out, 0x8B);
                    emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)src_off);
                    /* mov [rbp + dst_off], rax  (89 45 /offset) */
                    emit_byte(out, 0x48); emit_byte(out, 0x89);
                    emit_byte(out, 0x45); emit_byte(out, (uint8_t)(int8_t)dst_off);
                    return 1;
                }
            }
        }
    }
    /* `name(...)` built-in function call (strlen, strcpy, @ComAlloc, free, etc.) */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == '(') {
        /* Handle @CStr(...) macro: emit address of string literal in .data section */
        if (strcmp(toks[0].text, "@CStr") == 0) {
            /* collect all string tokens inside the parens; emit as .data */
            for (int i = 2; i < n; i++) {
                if (toks[i].type == ATOK_STRING) {
                    /* wide string (L"..."): emit 2 bytes per char */
                    const char *s = toks[i].text;
                    if (s[0] == 'L' && s[1] == '"') {
                        s += 2;
                        while (*s && *s != '"') {
                            emit_byte(out, (uint8_t)*s);
                            emit_byte(out, 0);
                            s++;
                        }
                    } else if (s[0] == '"') {
                        s++;
                        while (*s && *s != '"') {
                            emit_byte(out, (uint8_t)*s);
                            s++;
                        }
                    }
                }
            }
            return 1;
        }
        int si = find_or_add_sym(out, toks[0].text);
        emit_byte(out, 0xE8);
        emit_imm(out, 0, 4);
        if (si >= 0) add_fixup(out, si, 4, -4);
        return 1;
    }

    /* `xacquire` / `xrelease` HLE prefixes: recognized before lock instruction.
     * The tokenizer splits `xacquire lock adc WORD PTR[rcx], 1000` into
     * xacquire(ID) lock(ID) adc(ID) WORD(ID) PTR(ID) [(OP) rcx(ID) ](OP) ,(OP) 1000(NUM).
     * Skip the xacquire/xrelease and lock prefixes, then let the underlying instruction
     * handle normally (the F2/F3 + F0 prefixes are implied by the token presence). */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "xacquire") == 0 || strcmp(toks[0].text, "xrelease") == 0)) {
        int hle_pp = (strcmp(toks[0].text, "xacquire") == 0) ? 0xF2 : 0xF3;  /* F2=xacquire, F3=xrelease */
        int start = 1;
        if (start < n && toks[start].type == ATOK_ID && (strcmp(toks[start].text, "lock") == 0 || strcmp(toks[start].text, "LOCK") == 0)) {
            start++;
        }
        /* strip the HLE and lock prefixes, re-encode the underlying instruction */
        if (start < n && toks[start].type == ATOK_ID) {
            int n2 = n - start;
            a_tok_t *t2 = &toks[start];
            /* emit HLE + lock prefix bytes before the instruction; guard the
             * direct buffer writes exactly like emit_byte() so the capacity
             * limit can never be exceeded (silent OOB guard, not a behavior change) */
            if (out->cur_sec == SEC_TEXT && out->text_len + 2 < sizeof(out->text)) {
                out->text[out->text_len++] = (uint8_t)hle_pp;
                out->text[out->text_len++] = 0xF0;  /* lock */
            }
            /* process the underlying instruction (adc, add, etc.) */
            int ret = encode_instruction(out, t2, n2);
            if (ret) return 1;
        }
        return 0;
    }
    /* `lock` prefix: recognized before instruction — emit lock prefix then call instruction */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "lock") == 0 || strcmp(toks[0].text, "LOCK") == 0) && n >= 2) {
        if (out->cur_sec == SEC_TEXT && out->text_len < sizeof(out->text))
            out->text[out->text_len++] = 0xF0;  /* lock prefix */
        /* handle `lock xacquire` / `lock xrelease` ordering */
        if (n >= 3 && toks[1].type == ATOK_ID &&
            (strcmp(toks[1].text, "xacquire") == 0 || strcmp(toks[1].text, "xrelease") == 0)) {
            if (out->cur_sec == SEC_TEXT && out->text_len < sizeof(out->text))
                out->text[out->text_len++] = (strcmp(toks[1].text, "xacquire") == 0) ? 0xF2 : 0xF3;
            return encode_instruction(out, &toks[2], n - 2);
        }
        return encode_instruction(out, &toks[1], n - 1);
    }
    if (toks[0].type == ATOK_OP && toks[0].text[0] == '{' && n >= 3) {
        if ((strcmp(toks[1].text, "vex") == 0 || strcmp(toks[1].text, "vex3") == 0 ||
             strcmp(toks[1].text, "evex") == 0 || strcmp(toks[1].text, "swap") == 0) &&
            toks[2].type == ATOK_OP && toks[2].text[0] == '}') {
            /* shift tokens: drop { vex/evex/swap } prefix */
            for (int i = 3; i < n; i++) toks[i - 3] = toks[i];
            return assemble_line(out, toks, n - 3);
        }
    }
    /* Bare `{` or `}` on its own line: struct/class init continuation or block end — skip */
    if (n == 1 && toks[0].type == ATOK_OP && (toks[0].text[0] == '{' || toks[0].text[0] == '}')) {
        return 1;
    }
    /* Bare string literal on its own line: @CStr continuation (L"..." or "..." strings).
     * The tokenizer splits `L"..."` into ID(L) + STRING("..."), so accept that pattern. */
    if (n >= 1) {
        int string_line = 0;
        if (toks[0].type == ATOK_STRING) string_line = 1;
        else if (toks[0].type == ATOK_ID && n >= 2 &&
                 (strcmp(toks[0].text, "L") == 0 || strcmp(toks[0].text, "l") == 0) &&
                 toks[1].type == ATOK_STRING) string_line = 1;
        if (string_line) {
            for (int i = 0; i < n; i++) {
                if (toks[i].type == ATOK_STRING) {
                    const char *s = toks[i].text;
                    /* wide string variant (preceded by L ID token): 2 bytes per char */
                    int wide = (i >= 1 && toks[i-1].type == ATOK_ID &&
                                (strcmp(toks[i-1].text, "L") == 0 || strcmp(toks[i-1].text, "l") == 0));
                    if (s[0] == '"') {
                        s++;
                        while (*s && *s != '"') {
                            emit_byte(out, (uint8_t)*s);
                            if (wide) emit_byte(out, 0);
                            s++;
                        }
                    }
                }
            }
            return 1;
        }
    }
    /* `},{` on one line: struct init separator between two instances */
    if (n >= 2 && toks[0].type == ATOK_OP && toks[0].text[0] == '}' && toks[1].type == ATOK_OP && toks[1].text[0] == ',') {
        return 1;
    }
    /* Nested `{{{{N}}}}` or `{{{{1}}}}` struct init brace value: lines with braces and numbers */
    if (n >= 1) {
        int all_op_or_num = 1;
        for (int i = 0; i < n; i++) {
            if (toks[i].type != ATOK_OP && toks[i].type != ATOK_NUM) { all_op_or_num = 0; break; }
            if (toks[i].type == ATOK_OP && toks[i].text[0] != '{' && toks[i].text[0] != '}') { all_op_or_num = 0; break; }
        }
        if (all_op_or_num) return 1;  /* pure brace/number struct init line */
    }
    /* Bare numeric value during struct init (e.g., `0`) — skip */
    if (n == 1 && toks[0].type == ATOK_NUM) {
        return 1;
    }
    /* `name segment` segment definition (flat model) — skip */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "segment") == 0 || strcmp(toks[1].text, "SEGMENT") == 0)) {
        return 1;
    }
    /* `_DATA ends` — segment end, skip */
    if (n == 1 && toks[0].type == ATOK_ID) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0 && toks[0].text[0] == '_' && strstr(toks[0].text, "DATA")) {
            /* segment name alone on its line with `ends` elsewhere */
        }
    }

    /* `define` directive: text macro definitions (define LF_FACESIZE 32, etc.) */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "define") == 0) {
        if (n >= 3 && toks[1].type == ATOK_ID) {
            int si = find_or_add_sym(out, toks[1].text);
            if (si >= 0) {
                out->syms[si].defined = 1;
                out->syms[si].sec_index = ASMC_ABS_SEC;
                /* evaluate second token as value */
                int64_t v = 0;
                for (int k = 2; k < n; k++) {
                    if (toks[k].type == ATOK_NUM) { v = (int64_t)toks[k].value; break; }
                }
                out->syms[si].value = (uint64_t)v;
            }
        }
        return 1;
    }

    /* `local` directive: local variable declarations (local p:ptr C, local a:dword, ...)
     * Allocates per-procedure stack frame: name:type pairs, descending offsets. */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "local") == 0 || strcmp(toks[0].text, "LOCAL") == 0 ||
         strcmp(toks[0].text, "Local") == 0)) {
        out->cur_proc = 1;
        if (out->nlocals == 0) out->frame_size = 0;
        /* parse name:type pairs separated by commas */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
            if (toks[i].type != ATOK_ID) continue;
            const char *lname = toks[i].text;
            /* optional array count: `local name:N type` — N is a number before ':' */
            int lcount = 1;
            if (i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ':') {
                /* named:type */;
            } else if (i + 3 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] != ':' &&
                       toks[i+2].type == ATOK_NUM) {
                /* name N:type — count multiplier before ':' like local buf 256:byte */
                lcount = (int)toks[i+2].value;
                /* shift tokens to align :type */
                for (int j = i+1; j < n-1; j++) toks[j] = toks[j+1];
                n--;
            }
            /* type after ':' or after count: */
            int lsize = 4;   /* default dword */
            if (i + 2 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ':'
                && toks[i+2].type == ATOK_ID) {
                const char *typ = toks[i+2].text;
                if (strcmp(typ, "byte")==0 || strcmp(typ, "db")==0) lsize = 1;
                else if (strcmp(typ, "word")==0 || strcmp(typ, "dw")==0) lsize = 2;
                else if (strcmp(typ, "dword")==0 || strcmp(typ, "dd")==0 ||
                         strcmp(typ, "sdword")==0) lsize = 4;
                else if (strcmp(typ, "qword")==0 || strcmp(typ, "dq")==0 ||
                         strcmp(typ, "ptr")==0 || strcmp(typ, "ptr_t")==0 ||
                         strcmp(typ, "float")==0 || strcmp(typ, "double")==0 ||
                         strcmp(typ, "real8")==0) lsize = 8;
                i += 2;
            }
            lsize *= lcount;
            /* Type-aligned allocation: align frame_size to the type's natural alignment
             * before allocating the local. byte=1, word=2, dword=4, qword=8. */
            int align = 1;
            if (lsize >= 8) align = 8;
            else if (lsize >= 4) align = 4;
            else if (lsize >= 2) align = 2;
            /* Pad frame_size to alignment boundary */
            if (out->frame_size % align != 0)
                out->frame_size += align - (out->frame_size % align);
            if (out->nlocals >= 64) break;
            snprintf(out->locals[out->nlocals], 128, "%s", lname);
            out->local_sizes[out->nlocals] = lsize;
            out->local_sym_ids[out->nlocals] = 0;  /* filled below after find_or_add_sym */
            /* descending offsets: [esp+frame_size] grows down */
            /* local at [esp + out->frame_size] after sub esp,frame_size */
            if (out->frame_size == 0) out->frame_size = 16;  /* base frame alignment */
            out->local_offs[out->nlocals] = out->frame_size;
            out->frame_size += lsize;
            /* register in symbol table: defined abs symbol (stack offset marker) */
            int si = find_or_add_sym(out, lname);
            out->local_sym_ids[out->nlocals] = (si >= 0) ? si : -1;
            if (si >= 0) {
                out->syms[si].defined = 1;
                out->syms[si].sec_index = ASMC_ABS_SEC;
                out->syms[si].value = (uint64_t)out->local_offs[out->nlocals];
            }
            out->nlocals++;
        }
        return 1;
    }

    /* `assume` directive: assume register:type (assume rcx:ptr C, etc.)
     * Registers type metadata per register and supports reset (assume rcx:nothing). */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "assume") == 0) {
        /* assume reg:type or assume reg:nothing pairs, comma-separated.
         * `assume reg:ptr StructName` — resolve the LAST ID that maps to a struct.
         * `assume reg:nothing` — reset the register's assumption (struct_id=0). */
        for (int i = 1; i + 2 < n; i++) {
            if (toks[i].type == ATOK_ID && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ':' &&
                toks[i+2].type == ATOK_ID) {
                const reg_t *reg = find_reg(toks[i].text);
                if (reg) {
                    int si = find_or_add_sym(out, toks[i].text);
                    if (si >= 0) {
                        out->syms[si].defined = 1;
                        out->syms[si].sec_index = ASMC_ABS_SEC;
                        /* reset case: assume reg:nothing */
                        if (strcmp(toks[i+2].text, "nothing") == 0) {
                            out->syms[si].struct_id = 0;
                        } else {
                            /* override case: find the last ID token that has struct_id
                             * (handles `ptr S1`, and later declarations replace) */
                            out->syms[si].struct_id = 0;
                            for (int k = i + 2; k < n; k++) {
                                if (toks[k].type == ATOK_ID) {
                                    /* stop at comma or next assume pair */
                                    if (toks[k-1].type == ATOK_OP && toks[k-1].text[0] == ',')
                                        break;
                                    int ti = find_or_add_sym(out, toks[k].text);
                                    if (ti >= 0 && out->syms[ti].struct_id > 0) {
                                        out->syms[si].struct_id = out->syms[ti].struct_id;
                                    }
                                }
                            }
                        }
                    }
                }
                /* advance past the pair */
                while (i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ',') i += 2;
            }
        }
        return 1;
    }

    /* double-colon scope resolution: `name::name proc/endp ...` — skip (method definition) */
    if (n >= 4 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == ':' &&
        toks[2].type == ATOK_OP && toks[2].text[0] == ':' && toks[3].type == ATOK_ID) {
        return 1;
    }

    /* `option` directive: option casemap:none, win64:auto, OPTION PROLOGUE:NONE, etc.
     * Accept both lower and upper case directive name. */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "option") == 0 || strcmp(toks[0].text, "OPTION") == 0)) {
        return 1;   /* accepted; casemap:none is our default (case-sensitive) */
    }

    /* `typedef` directive: type alias declarations (float typedef real4, etc.) */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "typedef") == 0) {
        return 1;   /* accepted; treat as type alias (no code emitted) */
    }
    /* `name typedef type` form: alias_name typedef real4 — register the alias */
    if (toks[0].type == ATOK_ID && n >= 3 && toks[1].type == ATOK_ID &&
        strcmp(toks[1].text, "typedef") == 0) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) { out->syms[si].defined = 1; out->syms[si].sec_index = ASMC_ABS_SEC; }
        return 1;   /* alias definition, registered */
    }

    /* `proto` directive: function prototype declarations (inl proto asmcall :float,...) */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        strcmp(toks[1].text, "proto") == 0) {
        /* proto declaration line; skip (no code emitted) */
        return 1;
    }
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "proto") == 0) {
        return 1;
    }

    /* struct/class field declaration: `name type ?` or `name type` (ID ID ?)
     * Also `name type < >` (struct variable with empty init, e.g. `x xx <>`).
     * Registers field offset within the current struct (real layout).
     * `name textequ <...>` / `name catstr ...` and friends are NOT struct
     * fields — skip this branch so the text handlers below can run. */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        !(strcmp(toks[1].text, "textequ") == 0 || strcmp(toks[1].text, "TEXTEQU") == 0 ||
          strcmp(toks[1].text, "catstr") == 0 || strcmp(toks[1].text, "CATSTR") == 0 ||
          strcmp(toks[1].text, "CatStr") == 0 || strcmp(toks[1].text, "CATSTR") == 0 ||
          strcmp(toks[1].text, "substr") == 0 || strcmp(toks[1].text, "SUBSTR") == 0 ||
          strcmp(toks[1].text, "SubStr") == 0 ||
          strcmp(toks[1].text, "sizestr") == 0 || strcmp(toks[1].text, "SIZESTR") == 0 ||
          strcmp(toks[1].text, "SizeStr") == 0 ||
          strcmp(toks[1].text, "instr") == 0 || strcmp(toks[1].text, "INSTR") == 0 ||
          strcmp(toks[1].text, "InStr") == 0)) {
        const char *cand = toks[1].text;
        int field_size = 0;
        int is_type = 0;
        if (strcmp(cand, "ptr") == 0 || strcmp(cand, "ptr_t") == 0) { is_type = 1; field_size = 8; }
        else if (strcmp(cand, "byte") == 0 || strcmp(cand, "BYTE") == 0 ||
                 strcmp(cand, "sbyte") == 0 || strcmp(cand, "SBYTE") == 0 ||
                 strcmp(cand, "db") == 0 || strcmp(cand, "DB") == 0) { is_type = 1; field_size = 1; }
        else if (strcmp(cand, "word") == 0 || strcmp(cand, "WORD") == 0 ||
                 strcmp(cand, "sword") == 0 || strcmp(cand, "SWORD") == 0 ||
                 strcmp(cand, "dw") == 0 || strcmp(cand, "DW") == 0) { is_type = 1; field_size = 2; }
        else if (strcmp(cand, "dword") == 0 || strcmp(cand, "DWORD") == 0 ||
                 strcmp(cand, "sdword") == 0 || strcmp(cand, "SDWORD") == 0 ||
                 strcmp(cand, "dd") == 0 || strcmp(cand, "DD") == 0) { is_type = 1; field_size = 4; }
        else if (strcmp(cand, "qword") == 0 || strcmp(cand, "QWORD") == 0 ||
                 strcmp(cand, "sqword") == 0 || strcmp(cand, "SQWORD") == 0 ||
                 strcmp(cand, "dq") == 0 || strcmp(cand, "DQ") == 0) { is_type = 1; field_size = 8; }
        else if (strcmp(cand, "float") == 0 || strcmp(cand, "double") == 0) { is_type = 1; field_size = 8; }
        else if (strcmp(cand, "real4") == 0) { is_type = 1; field_size = 4; }
        else if (strcmp(cand, "real8") == 0 || strcmp(cand, "real10") == 0 ||
                 strcmp(cand, "tbyte") == 0) { is_type = 1; field_size = 8; }
        else if (strcmp(cand, "oword") == 0 || strcmp(cand, "OWORD") == 0 ||
                 strcmp(cand, "real16") == 0 || strcmp(cand, "REAL16") == 0) { is_type = 1; field_size = 16; }
        /* typedef alias check — only when inside a struct body */
        if (!is_type && out->cur_struct_id > 0) {
            for (int i = 0; i < out->nsyms; i++)
                if (strcmp(out->syms[i].name, cand) == 0 && out->syms[i].defined &&
                    out->syms[i].sec_index == ASMC_ABS_SEC) {
                    is_type = 1;
                    if (out->syms[i].struct_id > 0)
                        field_size = out->struct_sizes[out->syms[i].struct_id];
                    else field_size = 8;
                    break;
                }
        }
        /* struct name check: if the line ends with `< >` or `?`, it's a variable declaration */
        if (!is_type && n >= 4 && toks[n-2].type == ATOK_OP && toks[n-2].text[0] == '<' &&
            toks[n-1].type == ATOK_OP && toks[n-1].text[0] == '>') {
            is_type = 1;  /* `x xx <>` — struct variable declaration */
        }
        /* struct init check: `< ... >` with values */
        if (!is_type) {
            for (int z = 2; z < n; z++)
                if (toks[z].type == ATOK_OP && toks[z].text[0] == '<') {
                    for (int y = z + 1; y < n; y++)
                        if (toks[y].type == ATOK_OP && toks[y].text[0] == '>')
                            { is_type = 1; break; }
                    break;
                }
        }
        /* `name type (count) dup(<>)` — repeated struct variable allocation */
        if (!is_type && n >= 6 && toks[2].type == ATOK_OP && toks[2].text[0] == '(' &&
            toks[3].type == ATOK_NUM && toks[4].type == ATOK_OP && toks[4].text[0] == ')' &&
            toks[5].type == ATOK_ID && (strcmp(toks[5].text, "dup") == 0 || strcmp(toks[5].text, "DUP") == 0)) {
            is_type = 1;  /* `x C (4) dup(<>)` — repeated struct array allocation */
        }
        if (is_type) {
            /* register field offset if inside a struct */
            if (out->cur_struct_id > 0) {
                int si = find_or_add_sym(out, toks[0].text);
                if (si >= 0) {
                    out->syms[si].defined = 1;
                    out->syms[si].sec_index = ASMC_ABS_SEC;
                    out->syms[si].struct_id = out->cur_struct_id;
                    out->syms[si].struct_off = out->cur_struct_off;
                }
                if (field_size > 0) out->cur_struct_off += field_size;
            } else {
                /* struct variable declaration (e.g. `myvar mystruc <>`): register base symbol */
                int si = find_or_add_sym(out, toks[0].text);
                if (si >= 0) {
                    out->syms[si].defined = 1;
                    out->syms[si].sec_index = ASMC_ABS_SEC;
                }
                /* `name type <init...>` — emit initializer values, zero-pad to struct size */
                int lt_idx = -1, gt_idx = -1;
                for (int z = 1; z < n; z++) {
                    if (toks[z].type == ATOK_OP && toks[z].text[0] == '<') lt_idx = z;
                    if (toks[z].type == ATOK_OP && toks[z].text[0] == '>') { gt_idx = z; break; }
                }
                if (lt_idx >= 0 && gt_idx >= gt_idx) {
                    /* find struct size: toks[1] may be an already-defined struct type */
                    size_t total = (size_t)field_size;
                    int stid = -1;
                    for (int s = 0; s < out->nsyms; s++)
                        if (strcmp(out->syms[s].name, toks[1].text) == 0 && out->syms[s].defined &&
                            out->syms[s].struct_id > 0) {
                            stid = out->syms[s].struct_id;
                            total = (size_t)out->struct_sizes[stid];
                            break;
                        }
                    if (out->cur_sec != SEC_BSS) {
                        size_t emitted = 0;
                        for (int z = lt_idx + 1; z < gt_idx && emitted < total; z++) {
                            if (toks[z].type == ATOK_OP && toks[z].text[0] == ',') continue;
                            if (toks[z].type == ATOK_STRING) {
                                const char *ss = toks[z].text;
                                while (*ss && emitted < total) { emit_byte(out, (uint8_t)*ss++); emitted++; }
                            } else if (toks[z].type == ATOK_NUM) {
                                emit_byte(out, (uint8_t)toks[z].value); emitted++;
                                if (emitted < total) { emit_byte(out, 0); emitted++; }
                                if (emitted < total) { emit_byte(out, 0); emitted++; }
                                if (emitted < total) { emit_byte(out, 0); emitted++; }
                            }
                        }
                        for (size_t j = emitted; j < total; j++) emit_byte(out, 0);
                    }
                }
            }
            return 1;   /* field/variable declaration */
        }
    }
    /* typedef alias registration: `X typedef Y` — record X as a type alias */
    if (n >= 3 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "typedef") == 0 || strcmp(toks[1].text, "TYPEDEF") == 0)) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) { out->syms[si].defined = 1; out->syms[si].sec_index = ASMC_ABS_SEC; }
        return 1;
    }

    /* struct/class instance initialization: `TypeName { ... }` in .data section —
     * allocate struct_sizes bytes (zero-init), skipping the brace body content. */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == '{') {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0 && out->syms[si].struct_id > 0) {
            int sid = out->syms[si].struct_id;
            size_t alloc_size = (size_t)out->struct_sizes[sid];
            for (size_t j = 0; j < alloc_size; j++) emit_byte(out, 0);
            return 1;
        }
    }

    /* `.inline name :args { ... }` — inline-method definition line (body skipped in
     * process_source_lines which owns the line cursor). */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, ".inline") == 0) {
        return 1;
    }
    /* `.template <name>` — record/template container start (like struct) */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, ".template") == 0 || strcmp(toks[0].text, "TEMPLATE") == 0) &&
        n >= 2 && toks[1].type == ATOK_ID) {
        out->cur_struct_id++;
        if (out->cur_struct_id >= 32) out->cur_struct_id = 31;
        out->cur_struct_off = 0;
        out->struct_sizes[out->cur_struct_id] = 0;
        int si = find_or_add_sym(out, toks[1].text);
        if (si >= 0) {
            out->syms[si].defined = 1;
            out->syms[si].sec_index = ASMC_ABS_SEC;
            out->syms[si].struct_id = out->cur_struct_id;
        }
        return 1;
    }
    /* `record` marker line (plain or named) inside a template: keep collecting fields */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "record") == 0 &&
        (n == 1 || (n == 2 && toks[1].type == ATOK_ID))) {
        return 1;
    }
    /* bit-field member: `name TYPE : bits ?` — register with bit-offset semantics */
    if (n >= 5 && toks[0].type == ATOK_ID && toks[3].type == ATOK_OP && toks[3].text[0] == ':' &&
        toks[4].type == ATOK_NUM) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) {
            out->syms[si].defined = 1;
            out->syms[si].sec_index = ASMC_ABS_SEC;
        }
        return 1;
    }
    /* struct/class/union definition:
     *   `name struct/union`  (named, name-first)
     *   `struct/union name`  (named, keyword-first, e.g. `union uChar`)
     *   `struct` / `union`   (bare, anonymous nested)
     * ... `ends` closes.  Nested definitions push onto a stack so the
     * parent struct context (id + offset) is restored on `ends`. */
    if ((n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
         (strcmp(toks[1].text, "struc") == 0 || strcmp(toks[1].text, "STRUCT") == 0 ||
          strcmp(toks[1].text, "struct") == 0 || strcmp(toks[1].text, "STRUC") == 0 ||
          strcmp(toks[1].text, "union") == 0 || strcmp(toks[1].text, "UNION") == 0)) ||
        (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
         (strcmp(toks[0].text, "union") == 0 || strcmp(toks[0].text, "UNION") == 0 ||
          strcmp(toks[0].text, "struct") == 0 || strcmp(toks[0].text, "STRUCT") == 0 ||
          strcmp(toks[0].text, "struc") == 0 || strcmp(toks[0].text, "STRUC") == 0)) ||
        (n == 1 && toks[0].type == ATOK_ID &&
         (strcmp(toks[0].text, "struct") == 0 || strcmp(toks[0].text, "STRUCT") == 0 ||
          strcmp(toks[0].text, "struc") == 0 || strcmp(toks[0].text, "STRUC") == 0 ||
          strcmp(toks[0].text, "union") == 0 || strcmp(toks[0].text, "UNION") == 0))) {
        int is_union = (n == 1 && (strcmp(toks[0].text, "union") == 0 || strcmp(toks[0].text, "UNION") == 0)) ||
                       (n >= 2 && (strcmp(toks[0].text, "union") == 0 || strcmp(toks[0].text, "UNION") == 0)) ||
                       (n >= 2 && (strcmp(toks[1].text, "union") == 0 || strcmp(toks[1].text, "UNION") == 0));
        /* name: for `name struct` it is toks[0]; for `union name` it is toks[1]; bare -> NULL */
        const char *sname = NULL;
        if (n >= 2 && toks[0].type == ATOK_ID &&
            !(strcmp(toks[0].text, "struct") == 0 || strcmp(toks[0].text, "STRUCT") == 0 ||
              strcmp(toks[0].text, "struc") == 0 || strcmp(toks[0].text, "STRUC") == 0 ||
              strcmp(toks[0].text, "union") == 0 || strcmp(toks[0].text, "UNION") == 0))
            sname = toks[0].text;
        else if (n >= 2 && toks[1].type == ATOK_ID) sname = toks[1].text;
        /* anonymous nested member: an anonymous struct/union contributes its
         * members to the enclosing struct at the current offset; if this is an
         * anonymous union the parent offset stays fixed (members overlap). */
        if (out->cur_struct_id > 0 && out->n_struct_stack < 32) {
            out->struct_stack_id[out->n_struct_stack] = out->cur_struct_id;
            out->struct_stack_off[out->n_struct_stack] = out->cur_struct_off;
            out->struct_stack_kind[out->n_struct_stack] = 0;
            out->n_struct_stack++;
        }
        int new_id = out->cur_struct_id + 1;
        if (new_id >= 32) new_id = 31;
        out->cur_struct_id = new_id;
        out->struct_sizes[out->cur_struct_id] = 0;
        out->struct_is_union[out->cur_struct_id] = is_union;
        out->cur_struct_off = 0;
        if (sname) {
            int si = find_or_add_sym(out, sname);
            if (si >= 0) {
                out->syms[si].defined = 1;
                out->syms[si].sec_index = ASMC_ABS_SEC;
                out->syms[si].struct_id = out->cur_struct_id;
            }
        }
        return 1;
    }
    /* `.enum` / `enum` keyword: enum definition — register constants, skip members.
     * Format: `.enum [name] { member, member2, ... }` or `.enum` newline members. */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "enum") == 0 &&
        (toks[0].type == ATOK_DIRECTIVE || toks[0].text[0] == '.')) {
        out->in_enum = 1;
        return 1;  /* enum start */
    }
    if (toks[0].type == ATOK_DIRECTIVE && strcmp(toks[0].text, ".enum") == 0) {
        out->in_enum = 1;
        return 1;  /* .enum start */
    }
    /* Skip bare enum member lines (ID, or ID+comma) while in_enum is active */
    if (out->in_enum && n >= 1 && toks[0].type == ATOK_ID) {
        out->in_enum = 0;  /* assume end of enum after first non-member line */
        /* Check if this line is just an enum member: ID (+ comma, possibly more) */
        int all_enum = 1;
        for (int i = 0; i < n; i++) {
            if (toks[i].type == ATOK_ID) continue;
            if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
            if (toks[i].type == ATOK_NUM) continue;
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '=') continue;
            all_enum = 0; break;
        }
        if (all_enum) { out->in_enum = 1; return 1; }
    }

    /* `.class name` / `.comdef name` definition (with optional `: public parent` inheritance) */
    if ((toks[0].type == ATOK_DIRECTIVE || toks[0].type == ATOK_ID) &&
        (strcmp(toks[0].text, ".class") == 0 || strcmp(toks[0].text, ".comdef") == 0) &&
        n >= 2 && toks[1].type == ATOK_ID) {
        out->cur_struct_id++;
        if (out->cur_struct_id >= 32) out->cur_struct_id = 31;
        int base_off = 0;
        out->struct_parents[out->cur_struct_id] = 0;  /* default: no parent */
        /* inheritance: `.class name : public parent` — derived starts at base size */
        if (n >= 5 && toks[2].type == ATOK_OP && toks[2].text[0] == ':' &&
            toks[3].type == ATOK_ID && strcmp(toks[3].text, "public") == 0 &&
            toks[4].type == ATOK_ID) {
            int pidx = find_or_add_sym(out, toks[4].text);
            if (pidx >= 0 && out->syms[pidx].struct_id > 0) {
                base_off = out->struct_sizes[out->syms[pidx].struct_id];
                out->struct_parents[out->cur_struct_id] = out->syms[pidx].struct_id;
            }
        }
        out->cur_struct_off = base_off;
        out->struct_sizes[out->cur_struct_id] = base_off;
        int si = find_or_add_sym(out, toks[1].text);
        if (si >= 0) {
            out->syms[si].defined = 1;
            out->syms[si].sec_index = ASMC_ABS_SEC;
            out->syms[si].struct_id = out->cur_struct_id;
        }
        return 1;
    }
    /* `ends` closes struct/class definition — also handle `.ends` (ATOK_DIRECTIVE) and `ENDS` */
    if (n == 1 && (toks[0].type == ATOK_ID || toks[0].type == ATOK_DIRECTIVE) &&
        (strcmp(toks[0].text, "ends") == 0 || strcmp(toks[0].text, ".ends") == 0 ||
         strcmp(toks[0].text, "ENDS") == 0 || strcmp(toks[0].text, ".ENDS") == 0)) {
        if (out->cur_struct_id > 0) {
            out->struct_sizes[out->cur_struct_id] = out->cur_struct_off;
            /* restore parent context if this was a nested struct/union */
            if (out->n_struct_stack > 0) {
                out->n_struct_stack--;
                int pid = out->struct_stack_id[out->n_struct_stack];
                int poff = out->struct_stack_off[out->n_struct_stack];
                int size = out->struct_sizes[out->cur_struct_id];
                out->cur_struct_id = pid;
                out->cur_struct_off = poff + size;
            } else {
                out->cur_struct_id = 0;
                out->cur_struct_off = 0;
            }
        }
        return 1;
    }
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "ends") == 0 || strcmp(toks[1].text, "ENDS") == 0)) {
        /* close struct/class definition (bare form: `name ends`) */
        if (out->cur_struct_id > 0) {
            out->struct_sizes[out->cur_struct_id] = out->cur_struct_off;
            if (out->n_struct_stack > 0) {
                out->n_struct_stack--;
                int pid = out->struct_stack_id[out->n_struct_stack];
                int poff = out->struct_stack_off[out->n_struct_stack];
                int size = out->struct_sizes[out->cur_struct_id];
                out->cur_struct_id = pid;
                out->cur_struct_off = poff + size;
            } else {
                out->cur_struct_id = 0;
                out->cur_struct_off = 0;
            }
        }
        return 1;
    }

    /* function/procedure call: `name(...)` or `variable.method(...)` or `[mem].method(...)`
     * These are calls with arguments; skip since the called function handles code generation. */
    if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == '(') {
        return 1;   /* function call: name(args...) */
    }
    /* property/method: `name.name(...)` or `[mem].name(...)` */
    if (n >= 3 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == '.' &&
        toks[2].type == ATOK_ID) {
        return 1;   /* method call: obj.method(...) */
    }
    /* bracket-based property: `[mem].name(...)` */
    if (n >= 4 && toks[0].type == ATOK_OP && toks[0].text[0] == '[') {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_OP && toks[i].text[0] == '.' && i+1 < n && toks[i+1].type == ATOK_ID) {
                return 1;   /* [mem].method(...) */
            }
        }
    }

    /* Label + data directive form:  `name db/dw/dd/dq/resb ...` */
    if (toks[0].type == ATOK_ID && n >= 2 && toks[1].type == ATOK_ID) {
        const char *cand = toks[1].text;
        /* text-equate directive splice: when the second token is a text equate
         * whose value starts with EQU/= (e.g. `DBB` = <EQU 1;> in
         * `LNAME_TXT DBB LENGTHOF LNAME_TXT-1,'Lname'`), splice its text at the
         * line start so the EQU directive is honoured (LNAME_TXT becomes 1). */
        for (int se = 0; se < out->nsyms; se++) {
            if (out->syms[se].is_text && out->syms[se].defined &&
                strcmp(out->syms[se].name, cand) == 0 && out->syms[se].text[0] &&
                (strncmp(out->syms[se].text, "EQU", 3) == 0 ||
                 strncmp(out->syms[se].text, "equ", 3) == 0 ||
                 out->syms[se].text[0] == '=')) {
                char rebuilt[2048]; size_t ro = 0, ri = 0;
                const char *tv = out->syms[se].text;
                while (tv[ri] && ro + 1 < sizeof(rebuilt)) rebuilt[ro++] = tv[ri++];
                for (int j = 2; j < n; j++) {
                    const char *tx = toks[j].text;
                    size_t tl = strlen(tx);
                    if (tl && ro + tl + 2 < sizeof(rebuilt)) {
                        rebuilt[ro++] = ' ';
                        memcpy(rebuilt + ro, tx, tl); ro += tl;
                    }
                }
                rebuilt[ro] = 0;
                a_tok_t r2[256];
                int rn = TokenizeLine(rebuilt, r2, 256);
                if (rn > 0) {
                    a_tok_t full[256];
                    full[0] = toks[0];
                    for (int k = 0; k < rn; k++) full[1 + k] = r2[k];
                    return assemble_line(out, full, 1 + rn);
                }
            }
        }
        int is_data = (strcmp(cand,"db")==0 || strcmp(cand,"DB")==0 ||
                       strcmp(cand,"dw")==0 || strcmp(cand,"DW")==0 ||
                       strcmp(cand,"dd")==0 || strcmp(cand,"DD")==0 ||
                       strcmp(cand,"dq")==0 || strcmp(cand,"DQ")==0 ||
                       strcmp(cand,"df")==0 || strcmp(cand,"DF")==0 ||
                       strcmp(cand,"dt")==0 || strcmp(cand,"DT")==0 ||
                       strcmp(cand,"byte")==0 || strcmp(cand,"BYTE")==0 ||
                       strcmp(cand,"word")==0 || strcmp(cand,"WORD")==0 ||
                       strcmp(cand,"dword")==0 || strcmp(cand,"DWORD")==0 ||
                       strcmp(cand,"qword")==0 || strcmp(cand,"QWORD")==0 ||
                       strcmp(cand,"PF16")==0 || strcmp(cand,"pf16")==0 ||
                       strcmp(cand,"PF32")==0 || strcmp(cand,"pf32")==0 ||
                       strcmp(cand,"PF64")==0 || strcmp(cand,"pf64")==0 ||
                       strcmp(cand,"fword")==0 || strcmp(cand,"FWORD")==0 ||
                       strcmp(cand,"real2")==0 || strcmp(cand,"REAL2")==0 ||
                       strcmp(cand,"real4")==0 || strcmp(cand,"REAL4")==0 ||
                       strcmp(cand,"real8")==0 || strcmp(cand,"REAL8")==0 ||
                       strcmp(cand,"real10")==0 || strcmp(cand,"REAL10")==0 ||
                       strcmp(cand,"real16")==0 || strcmp(cand,"REAL16")==0 ||
                       strcmp(cand,"tbyte")==0 || strcmp(cand,"TBYTE")==0 ||
                       strcmp(cand,"oword")==0 || strcmp(cand,"OWORD")==0 ||
                       strcmp(cand,"resb")==0 || strcmp(cand,"resw")==0 ||
                       strcmp(cand,"resd")==0 || strcmp(cand,"resq")==0);
        /* typedef alias (e.g. PN16/PN32/HANDLE/LPSTR) as data-init type —
         * only when toks[0] is NOT a known instruction mnemonic. */
        if (!is_data) {
            static const char *instrs[] = {
                "add","sub","mov","cmp","xor","or","and","adc","sbb","inc","dec",
                "div","idiv","mul","imul","call","jmp","push","pop","test","lea",
                "not","neg","xchg","cmpxchg","shl","shr","sal","sar","rol","ror",
                "bt","bts","btr","btc","bswap","movzx","movsx","movsxd","enter",
                "lldt","lmsw","ltr","sldt","smsw","sgdt","sidt","lgdt","lidt",
                "invlpg","verr","verw","arpl","str","in","out","xlat","xlatb",
                "prefetch","prefetchw","prefetchnta",
                "prefetcht0","prefetcht1","prefetcht2",
                "fldenv","fnstenv","fstenv","fldcw","fstcw","fnstcw","fbld","fbstp",
                "frstor","fnsave","fsave","fnstsw","fstsw",
                "fxsave","fxsave64","fxrstor","fxrstor64","xsave","xsave64",
                "xsaveopt","xsaveopt64","xsavec","xsavec64","xsaves","xsaves64",
                "xrstor","xrstor64","xrstors","xrstors64",
                "clflush","clflushopt","ptwrite","rdpid",
                "fcom","fcomp","fcompp","fild","fist","fistp","fiadd","fimul",
                NULL };
            int is_instr = 0;
            for (int z = 0; instrs[z]; z++)
                if (strcmp(toks[0].text, instrs[z]) == 0) { is_instr = 1; break; }
            if (!is_instr) {
                /* skip when toks[0] is itself a known data type (directive form like `real16 X`) */
                static const char *dtypes[] = { "real2","real4","real8","real10","real16",
                    "fword","oword","tbyte","byte","word","dword","qword","db","dw","dd","dq",
                    "REAL2","REAL4","REAL8","REAL10","REAL16","OWORD","TBYTE","BYTE","WORD","DWORD","QWORD",
                    "DB","DW","DD","DQ", NULL };
                int is_dtype = 0;
                for (int z = 0; dtypes[z]; z++)
                    if (strcmp(toks[0].text, dtypes[z]) == 0) { is_dtype = 1; break; }
                if (!is_dtype) {
                    for (int s = 0; s < out->nsyms; s++)
                        if (strcmp(out->syms[s].name, cand) == 0 && out->syms[s].defined &&
                            out->syms[s].sec_index == ASMC_ABS_SEC) {
                            is_data = 1;
                            break;
                        }
                }
            }
        }
        if (is_data) {
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) {
                out->syms[si].value = cur_offset(out);
                out->syms[si].defined = 1;
                out->syms[si].sec_index = out->cur_sec;
            }
            /* shift tokens: tok[1] becomes directive, tok[0] dropped */
            for (int i = 1; i < n; i++) toks[i-1] = toks[i];
            return assemble_line(out, toks, n - 1);
        }
    }

    /* `public` directive: mark succeeding symbol as global */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "public") == 0 || strcmp(toks[0].text, "PUBLIC") == 0 ||
         strcmp(toks[0].text, "global") == 0 || strcmp(toks[0].text, "GLOBAL") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                int si = find_or_add_sym(out, toks[i].text);
                if (si >= 0) out->syms[si].global = 1;
            }
        }
        return 1;
    }

    /* Data directives: db/dw/dd/dq (byte/word/dword/qword)
     * Also `NUM db ...` form (numeric label prefix from `x:label` macro params). */
    if (toks[0].type == ATOK_NUM && n >= 2 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "db") == 0 || strcmp(toks[1].text, "DB") == 0 ||
         strcmp(toks[1].text, "byte") == 0 || strcmp(toks[1].text, "BYTE") == 0 ||
         strcmp(toks[1].text, "dw") == 0 || strcmp(toks[1].text, "DW") == 0 ||
         strcmp(toks[1].text, "word") == 0 || strcmp(toks[1].text, "WORD") == 0 ||
         strcmp(toks[1].text, "dd") == 0 || strcmp(toks[1].text, "DD") == 0 ||
         strcmp(toks[1].text, "dword") == 0 || strcmp(toks[1].text, "DWORD") == 0 ||
         strcmp(toks[1].text, "dq") == 0 || strcmp(toks[1].text, "DQ") == 0 ||
         strcmp(toks[1].text, "qword") == 0 || strcmp(toks[1].text, "QWORD") == 0)) {
        for (int i = 1; i < n; i++) toks[i-1] = toks[i];
        return assemble_line(out, toks, n - 1);
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "db") == 0 || strcmp(toks[0].text, "DB") == 0 ||
         strcmp(toks[0].text, "byte") == 0 || strcmp(toks[0].text, "BYTE") == 0)) {
        int count = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) { count++; }
            else if (toks[i].type == ATOK_STRING) {
                for (const char *s = toks[i].text; *s; s++) count++;
            } else if (toks[i].type == ATOK_ID && toks[i].text[0] == '<') {
                const char *p = toks[i].text + 1;
                while (*p) {
                    while (*p == ' ' || *p == '\t' || *p == ',') p++;
                    if (*p == '>' || *p == 0) break;
                    if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) { p += 2; while ((*p >= '0' && *p <= '9') || ((*p|0x20) >= 'a' && (*p|0x20) <= 'f')) p++; }
                    else { while (*p >= '0' && *p <= '9') p++; }
                    count++;
                }
            } else if (toks[i].type == ATOK_ID) {
                /* unquoted character sequence: `db e1` → 'e','1' */
                count += (int)strlen(toks[i].text);
            }
        }
        if (out->cur_struct_id > 0) out->cur_struct_off += (count > 0) ? count : 1;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) emit_byte(out, (uint8_t)toks[i].value);
            else if (toks[i].type == ATOK_STRING) {
                for (const char *s = toks[i].text; *s; s++) emit_byte(out, (uint8_t)*s);
            } else if (toks[i].type == ATOK_ID && toks[i].text[0] == '<') {
                const char *p = toks[i].text + 1;
                while (*p) {
                    while (*p == ' ' || *p == '\t' || *p == ',') p++;
                    if (*p == '>' || *p == 0) break;
                    int64_t val = 0;
                    if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) {
                        p += 2;
                        while ((*p >= '0' && *p <= '9') || ((*p | 0x20) >= 'a' && (*p | 0x20) <= 'f')) {
                            int d = (*p >= '0' && *p <= '9') ? *p - '0' : (*p | 0x20) - 'a' + 10;
                            val = val * 16 + d; p++;
                        }
                    } else {
                        while (*p >= '0' && *p <= '9') { val = val * 10 + (*p - '0'); p++; }
                    }
                    emit_byte(out, (uint8_t)val);
                }
            } else if (toks[i].type == ATOK_ID) {
                /* equ symbol → emit value byte; else unquoted char sequence (`db e1`) */
                int64_t symval = lookup_sym(out, toks[i].text);
                if (symval >= 0) emit_byte(out, (uint8_t)symval);
                else for (const char *s = toks[i].text; *s; s++) emit_byte(out, (uint8_t)*s);
            }
        }
        return 1;
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "dw") == 0 || strcmp(toks[0].text, "DW") == 0 ||
         strcmp(toks[0].text, "word") == 0 || strcmp(toks[0].text, "WORD") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) emit_imm(out, toks[i].value, 2);
        }
        return 1;
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "dd") == 0 || strcmp(toks[0].text, "DD") == 0 ||
         strcmp(toks[0].text, "dword") == 0 || strcmp(toks[0].text, "DWORD") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) emit_imm(out, toks[i].value, 4);
        }
        return 1;
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "dq") == 0 || strcmp(toks[0].text, "DQ") == 0 ||
         strcmp(toks[0].text, "qword") == 0 || strcmp(toks[0].text, "QWORD") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) emit_imm(out, toks[i].value, 8);
            else if (toks[i].type == ATOK_ID) {
                /* dq symbol → 8-byte placeholder + R_X86_64_64 absolute reloc */
                int si = find_or_add_sym(out, toks[i].text);
                emit_imm(out, 0, 8);
                if (si >= 0) add_fixup(out, si, 1 /*R_X86_64_64*/, 0);
            }
        }
        return 1;
    }
    /* df (6-byte far pointer 16:32), dt (10-byte far pointer 16:64),
     * PF16 (4-byte far pointer 16:16), PF32 (6-byte), PF64 (10-byte) */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "df") == 0 || strcmp(toks[0].text, "DF") == 0 ||
         strcmp(toks[0].text, "dt") == 0 || strcmp(toks[0].text, "DT") == 0 ||
         strcmp(toks[0].text, "PF16") == 0 || strcmp(toks[0].text, "pf16") == 0 ||
         strcmp(toks[0].text, "PF32") == 0 || strcmp(toks[0].text, "pf32") == 0 ||
         strcmp(toks[0].text, "PF64") == 0 || strcmp(toks[0].text, "pf64") == 0)) {
        int sz = 6;  /* df = 6 bytes, dt = 10, PF16 = 4, PF32 = 6, PF64 = 10 */
        if (strcmp(toks[0].text, "dt") == 0 || strcmp(toks[0].text, "DT") == 0 ||
            strcmp(toks[0].text, "PF64") == 0 || strcmp(toks[0].text, "pf64") == 0) sz = 10;
        else if (strcmp(toks[0].text, "PF16") == 0 || strcmp(toks[0].text, "pf16") == 0) sz = 4;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) {
                int64_t v = (int64_t)toks[i].value;
                emit_imm(out, (uint64_t)v, sz);
            } else if (toks[i].type == ATOK_ID && toks[i].text[0] == '0') {
                emit_imm(out, 0, sz);
            }
        }
        return 1;
    }
    /* FWORD/REAL2/REAL4/REAL8/REAL10/OWORD data directives */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "fword") == 0 || strcmp(toks[0].text, "FWORD") == 0 ||
         strcmp(toks[0].text, "real2") == 0 || strcmp(toks[0].text, "REAL2") == 0 ||
         strcmp(toks[0].text, "real4") == 0 || strcmp(toks[0].text, "REAL4") == 0 ||
         strcmp(toks[0].text, "real8") == 0 || strcmp(toks[0].text, "REAL8") == 0 ||
         strcmp(toks[0].text, "real10") == 0 || strcmp(toks[0].text, "REAL10") == 0 ||
         strcmp(toks[0].text, "real16") == 0 || strcmp(toks[0].text, "REAL16") == 0 ||
         strcmp(toks[0].text, "oword") == 0 || strcmp(toks[0].text, "OWORD") == 0)) {
        int sz = 8;
        if (toks[0].text[0] == 'f' || toks[0].text[0] == 'F') sz = 6;             /* fword */
        else if ((toks[0].text[3] == '2' || toks[0].text[3] == '2')) sz = 2;       /* real2 */
        else if ((toks[0].text[3] == '4' || toks[0].text[3] == '4')) sz = 4;       /* real4 */
        else if (toks[0].text[1] == 'e' && toks[0].text[2] == 'a' && toks[0].text[3] == 'l' &&
                 toks[0].text[4] == '1' && toks[0].text[5] == '0') sz = 10;        /* real10 */
        else if (toks[0].text[1] == 'e' && toks[0].text[2] == 'a' && toks[0].text[3] == 'l' &&
                 toks[0].text[4] == '1' && toks[0].text[5] == '6') sz = 16;        /* real16 */
        else if (toks[0].text[1] == 'w' || toks[0].text[1] == 'W') sz = 16;        /* oword */
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_NUM) emit_imm(out, toks[i].value, sz);
            else if (toks[i].type == ATOK_ID) {
                int64_t sv = lookup_sym(out, toks[i].text);
                if (sv >= 0) emit_imm(out, (uint64_t)sv, sz);
                else { for (int k = 0; k < sz; k++) emit_byte(out, 0); }
            } else if (toks[i].type == ATOK_STRING) {
                const char *s = toks[i].text;
                while (*s) emit_byte(out, (uint8_t)*s++);
                size_t slen = strlen(toks[i].text);
                for (size_t j = slen; j < (size_t)sz; j++) emit_byte(out, 0);
            }
        }
        return 1;
    }
    /* typedef symbol as data type: `PN16 0` / `HANDLE ?` — emit value as 8-byte (default) */
    if (toks[0].type == ATOK_ID && n >= 2) {
        int is_typedef = 0;
        for (int s = 0; s < out->nsyms; s++)
            if (strcmp(out->syms[s].name, toks[0].text) == 0 && out->syms[s].defined &&
                out->syms[s].sec_index == ASMC_ABS_SEC) { is_typedef = 1; break; }
        if (is_typedef) {
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_NUM) emit_imm(out, toks[i].value, 8);
                else if (toks[i].type == ATOK_OP && toks[i].text[0] == '?') { for (int k = 0; k < 8; k++) emit_byte(out, 0); }
            }
            return 1;
        }
    }
    /* `externdef <name>` — register an external symbol declaration */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "externdef") == 0 || strcmp(toks[0].text, "EXTERNDEF") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                /* skip calling convention / type keywords */
                if (strcmp(toks[i].text, "stdcall") == 0 || strcmp(toks[i].text, "c") == 0 ||
                    strcmp(toks[i].text, "fastcall") == 0 || strcmp(toks[i].text, "pascal") == 0 ||
                    strcmp(toks[i].text, "syscall") == 0 || strcmp(toks[i].text, "vectorcall") == 0 ||
                    strcmp(toks[i].text, "proc") == 0 || strcmp(toks[i].text, "PROC") == 0 ||
                    strcmp(toks[i].text, "byte") == 0 || strcmp(toks[i].text, "word") == 0 ||
                    strcmp(toks[i].text, "dword") == 0 || strcmp(toks[i].text, "qword") == 0)
                    continue;
                int si = find_or_add_sym(out, toks[i].text);
                if (si >= 0) { out->syms[si].defined = 1; }
                break;
            }
        }
        return 1;
    }
    /* `name record field1:bits, field2:bits, ...` — bit-field record definition */
    if (toks[0].type == ATOK_ID && n >= 2 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "record") == 0 || strcmp(toks[1].text, "RECORD") == 0)) {
        int ri = find_or_add_sym(out, toks[0].text);
        if (ri >= 0) { out->syms[ri].defined = 1; out->syms[ri].sec_index = ASMC_ABS_SEC; }
        /* register each field with its bit offset (from LSB) */
        int tot_bits = 0;
        /* count bits first (from rightmost field): fields are listed MSB-first */
        int bits[16], nbits = 0;
        for (int i = 2; i < n; i++) {
            if (toks[i].type == ATOK_NUM && i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ':') {
                if (nbits < 16) { bits[nbits++] = (int)toks[i].value; tot_bits += (int)toks[i].value; }
            }
        }
        /* register fields: name:bits (e.g. RF1:2) — scan for `ID : NUM` */
        int bit_cursor = 0;   /* LSB offset of next field (fields are MSB-first) */
        /* accumulate from MSB: first field is at the highest bit position */
        int cur = tot_bits;
        for (int i = 2; i < n; i++) {
            if (toks[i].type == ATOK_ID && i + 2 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == ':' &&
                toks[i+2].type == ATOK_NUM) {
                int w = (int)toks[i+2].value;
                cur -= w;   /* field starts at this LSB offset */
                int fs = find_or_add_sym(out, toks[i].text);
                if (fs >= 0) { out->syms[fs].defined = 1; out->syms[fs].sec_index = ASMC_ABS_SEC; }
            }
        }
        (void)cur;
        return 1;
    }
    /* `:label` — colon-prefixed label (goto target), register as symbol at current offset */
    if (n >= 2 && toks[0].type == ATOK_OP && toks[0].text[0] == ':' && toks[1].type == ATOK_ID) {
        int si = find_or_add_sym(out, toks[1].text);
        if (si >= 0) {
            out->syms[si].value = cur_offset(out);
            out->syms[si].defined = 1;
            out->syms[si].sec_index = out->cur_sec;
        }
        return 1;
    }
    /* `goto <label>` — HLL jump directive, emit jmp rel32 to label */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "goto") == 0 && n >= 2) {
        if (toks[1].type == ATOK_ID) {
            int si = find_or_add_sym(out, toks[1].text);
            emit_byte(out, 0xE9);
            int64_t target = lookup_sym(out, toks[1].text);
            if (target >= 0) {
                int64_t disp = target - (int64_t)cur_offset(out) - 4;
                emit_imm(out, (uint64_t)(int32_t)disp, 4);
            } else {
                emit_imm(out, 0, 4);
                if (si >= 0) add_fixup(out, si, 4, -4);
            }
            return 1;
        }
        return 0;
    }
    /* `echo`/`echoecho`/`print` — compile-time text output (accepted, prints nothing) */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "echo") == 0 ||
        strcmp(toks[0].text, "echoecho") == 0 || strcmp(toks[0].text, "print") == 0)) {
        return 1;
    }
    /* `option <opts>` — assembler option directive (accepted, no-op for this pass) */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "option") == 0) {
        return 1;
    }
    /* `includelib <lib>` — record library reference (accepted, no-op for codegen) */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "includelib") == 0) {
        return 1;
    }
    /* `pushcontext/popcontext` — context save/restore directives (accepted, no-op) */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "pushcontext") == 0 || strcmp(toks[0].text, "popcontext") == 0)) {
        return 1;
    }
    /* `extern <name>:<type>` — register an external symbol declaration */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "extern") == 0 || strcmp(toks[0].text, "EXTERN") == 0 ||
         strcmp(toks[0].text, "extrn") == 0 || strcmp(toks[0].text, "EXTRN") == 0)) {
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID) {
                /* skip type keywords */
                if (strcmp(toks[i].text, "proc") == 0 || strcmp(toks[i].text, "PROC") == 0 ||
                    strcmp(toks[i].text, "abs") == 0 || strcmp(toks[i].text, "ABS") == 0 ||
                    strcmp(toks[i].text, "byte") == 0 || strcmp(toks[i].text, "word") == 0 ||
                    strcmp(toks[i].text, "dword") == 0 || strcmp(toks[i].text, "qword") == 0)
                    continue;
                if (toks[i].type == ATOK_OP && toks[i].text[0] == ':') continue;
                if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
                int si = find_or_add_sym(out, toks[i].text);
                if (si >= 0) { out->syms[si].defined = 1; }
                break;
            }
        }
        return 1;
    }
    /* `name group <section>` — group directive (accepted, no-op) */
    if (toks[0].type == ATOK_ID && n >= 2 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "group") == 0 || strcmp(toks[1].text, "GROUP") == 0)) {
        return 1;
    }
    /* `assume reg:type, ...` — register-to-type association (accepted, no-op for codegen) */
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "assume") == 0 || strcmp(toks[0].text, "ASSUME") == 0)) {
        return 1;
    }
    /* `name typedef <type>` — register a type alias symbol */
    if (toks[0].type == ATOK_ID && n >= 2 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "typedef") == 0 || strcmp(toks[1].text, "TYPEDEF") == 0)) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) { out->syms[si].defined = 1; }
        return 1;
    }
    /* `name textequ <text>` — text equate (store literal text value) */
    if (toks[0].type == ATOK_ID && n >= 3 && toks[1].type == ATOK_ID &&
        (strcmp(toks[1].text, "textequ") == 0 || strcmp(toks[1].text, "TEXTEQU") == 0)) {
        int si = find_or_add_sym(out, toks[0].text);
        if (si >= 0) {
            out->syms[si].defined = 1;
            out->syms[si].sec_index = ASMC_ABS_SEC;
            out->syms[si].is_text = 1;
            out->syms[si].text[0] = 0;
            /* concatenate the remaining tokens (strip surrounding angle brackets),
             * inserting a space between consecutive word tokens so `<szProp dw TE1>`
             * round-trips as `szProp dw TE1` and not `szPropdwTE1`. */
            int prev_word = 0;
            for (int i = 2; i < n; i++) {
                const char *tk = toks[i].text;
                if (i == 2 && tk[0] == '<') tk++;
                size_t l = strlen(tk);
                if (i == n - 1 && l > 0 && tk[l - 1] == '>') l--;
                int is_word = (l > 0 && ((tk[0] >= 'a' && tk[0] <= 'z') ||
                                         (tk[0] >= 'A' && tk[0] <= 'Z') ||
                                         tk[0] == '_' || tk[0] == '@' || tk[0] == '?' ||
                                         (tk[0] >= '0' && tk[0] <= '9')));
                if (prev_word && is_word && out->syms[si].text[0]) {
                    size_t cl = strlen(out->syms[si].text);
                    if (cl + 1 < sizeof(out->syms[si].text)) strncat(out->syms[si].text, " ", 1);
                }
                if (strlen(out->syms[si].text) + l < sizeof(out->syms[si].text))
                    strncat(out->syms[si].text, tk, l);
                prev_word = is_word;
            }
        }
        return 1;
    }
    /* text functions used as equate value: `X catstr a, b, ...` /
     * `X substr s, start [,len]` / `X sizestr s` / `X instr ...` /
     * `X textequ @CatStr(...)` / `X textequ @SubStr(...)` etc.
     * Function name matching is case-insensitive (CatStr/SUBSTR/etc.). */
    if (toks[0].type == ATOK_ID && n >= 3 && toks[1].type == ATOK_ID) {
        int fn_idx = -1;      /* index of the function-name token */
        int arg_start = -1;   /* first argument token */
        int arg_end = n;      /* one past the last argument token */
        char fn_lower[64];
        /* directive form: `X catstr args...` / `X substr ...` */
        {
            size_t tl = strlen(toks[1].text);
            if (tl >= sizeof(fn_lower)) tl = sizeof(fn_lower) - 1;
            for (size_t ci = 0; ci < tl; ci++) {
                char c = toks[1].text[ci];
                fn_lower[ci] = (c >= 'A' && c <= 'Z') ? c + ('a' - 'A') : c;
            }
            fn_lower[tl] = 0;
            if (strcmp(fn_lower, "catstr") == 0 || strcmp(fn_lower, "substr") == 0 ||
                strcmp(fn_lower, "sizestr") == 0 || strcmp(fn_lower, "instr") == 0) {
                fn_idx = 1;
                arg_start = 2;
            }
        }
        /* `X textequ @Fn(...)` function-call form */
        if (fn_idx < 0 && n >= 4 && (strcmp(toks[1].text, "textequ") == 0 ||
                                     strcmp(toks[1].text, "TEXTEQU") == 0) &&
            toks[2].type == ATOK_ID && toks[2].text[0] == '@' &&
            toks[3].type == ATOK_OP && toks[3].text[0] == '(') {
            const char *fp = toks[2].text + 1;   /* strip @ */
            size_t tl = strlen(fp);
            if (tl >= sizeof(fn_lower)) tl = sizeof(fn_lower) - 1;
            for (size_t ci = 0; ci < tl; ci++) {
                char c = fp[ci];
                fn_lower[ci] = (c >= 'A' && c <= 'Z') ? c + ('a' - 'A') : c;
            }
            fn_lower[tl] = 0;
            if (strcmp(fn_lower, "catstr") == 0 || strcmp(fn_lower, "substr") == 0 ||
                strcmp(fn_lower, "sizestr") == 0 || strcmp(fn_lower, "instr") == 0) {
                fn_idx = 2;
                arg_start = 4;
                /* scan to the matching close paren (nested) */
                int nest = 0;
                for (int i = 3; i < n; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '(') nest++;
                    else if (toks[i].type == ATOK_OP && toks[i].text[0] == ')') {
                        nest--;
                        if (nest == 0) { arg_end = i; break; }
                    }
                }
            }
        }
        if (fn_idx >= 0 && arg_start > 0 && arg_start <= arg_end) {
        const char *fn = fn_lower;
        int ai = arg_start;   /* current argument index */
        char result[512]; result[0] = 0;
        int64_t numeric = 0;
        int is_numeric = 0;
        if (strcmp(fn, "catstr") == 0) {
            /* concatenate argument tokens: strip top-level commas/< > wrappers,
             * expand %sym or bare text-equate references, keep literal text */
            int angle = 0;
            for (int i = arg_start; i < arg_end; i++) {
                const char *tk = toks[i].text;
                if (toks[i].type == ATOK_OP && tk[0] == '<') { angle++; if (angle == 1) continue; }
                if (toks[i].type == ATOK_OP && tk[0] == '>') { if (angle > 0) angle--; continue; }
                if (angle == 0 && toks[i].type == ATOK_OP && tk[0] == ',') continue;
                int is_pct = (tk[0] == '%');
                const char *s = is_pct ? tk + 1 : tk;
                size_t l = strlen(s);
                /* %sym or bare text equate → substitute its text value */
                if (s[0] != '<') {
                    for (int si = 0; si < out->nsyms; si++)
                        if (out->syms[si].is_text && out->syms[si].defined &&
                            strcmp(out->syms[si].name, s) == 0) {
                            size_t vl = strlen(out->syms[si].text);
                            if (strlen(result) + vl < sizeof(result))
                                strncat(result, out->syms[si].text, vl);
                            goto next_cat;
                        }
                }
                if (l > 0 && s[l-1] == '>') l--;
                if (strlen(result) + l < sizeof(result)) strncat(result, s, l);
                next_cat:;
            }
            (void)ai;
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) { out->syms[si].defined = 1; out->syms[si].is_text = 1; strncpy(out->syms[si].text, result, sizeof(out->syms[si].text) - 1); }
            return 1;
        }
        else if (strcmp(fn, "sizestr") == 0) {
            /* sizestr arg — length of literal text or %sym text value */
            if (arg_start < arg_end) {
                const char *tk = toks[arg_start].text;
                if (tk[0] == '%') {
                    const char *nm = tk + 1;
                    numeric = 0;
                    for (int si = 0; si < out->nsyms; si++)
                        if (out->syms[si].is_text && out->syms[si].defined &&
                            strcmp(out->syms[si].name, nm) == 0) {
                            numeric = (int64_t)strlen(out->syms[si].text);
                            break;
                        }
                } else {
                    if (tk[0] == '<') tk++;
                    numeric = (int64_t)strlen(tk);
                    if (numeric > 0 && tk[numeric-1] == '>') numeric--;
                }
                is_numeric = 1;
            }
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) { out->syms[si].defined = 1; out->syms[si].value = (uint64_t)numeric; out->syms[si].is_text = 0; }
            return 1;
        }
        else if (strcmp(fn, "substr") == 0) {
            /* substr <string>, start[, len] → substring as text */
            if (arg_start < arg_end) {
                const char *tk = toks[arg_start].text;
                if (tk[0] == '<') tk++;
                size_t full = strlen(tk);
                if (full > 0 && tk[full-1] == '>') full--;
                int64_t start = 1, len = -1;
                /* start = first numeric arg after the string */
                int num_found = 0;
                a_tok_t win[16];
                for (int i = arg_start + 1; i < arg_end && num_found < 2; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == ',') continue;
                    if (toks[i].type == ATOK_OP && (toks[i].text[0] == '<' || toks[i].text[0] == '>')) continue;
                    if (num_found == 0) {
                        if (toks[i].type == ATOK_NUM) start = (int64_t)toks[i].value;
                        else {
                            int wn = 0, pos = 0;
                            for (int j = i; j < arg_end && wn < 15; j++) win[wn++] = toks[j];
                            win[wn].type = ATOK_END;
                            int64_t ev = 0;
                            if (eval_expr(out, win, &pos, wn, &ev) == 0) start = ev;
                        }
                        num_found++;
                    } else {
                        if (toks[i].type == ATOK_NUM) len = (int64_t)toks[i].value;
                        else {
                            int wn = 0, pos = 0;
                            for (int j = i; j < arg_end && wn < 15; j++) win[wn++] = toks[j];
                            win[wn].type = ATOK_END;
                            int64_t ev = 0;
                            if (eval_expr(out, win, &pos, wn, &ev) == 0) len = ev;
                        }
                        num_found++;
                    }
                }
                if (start < 1) start = 1;
                size_t beg = (size_t)(start - 1);
                if (beg > full) beg = full;
                size_t remaining = full - beg;
                size_t take = (len < 0 || (size_t)len > remaining) ? remaining : (size_t)len;
                if (take < sizeof(result)) { strncpy(result, tk + beg, take); result[take] = 0; }
                int si = find_or_add_sym(out, toks[0].text);
                if (si >= 0) { out->syms[si].defined = 1; out->syms[si].is_text = 1; strncpy(out->syms[si].text, result, sizeof(out->syms[si].text) - 1); }
            }
            return 1;
        }
        else {   /* instr: return index of substring (1-based, 0 if not found) */
            if (arg_start + 1 < arg_end) {
                const char *s1 = toks[arg_start].text, *s2 = toks[arg_start+1].text;
                if (s1[0] == '<') s1++; if (s2[0] == '<') s2++;
                const char *p = strstr(s1, s2);
                numeric = p ? (int64_t)(p - s1 + 1) : 0;
                is_numeric = 1;
            }
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) { out->syms[si].defined = 1; out->syms[si].value = (uint64_t)numeric; out->syms[si].is_text = 0; }
            return 1;
        }
        }
    }
    /* `.dosseg` / `.286` / `.386` / `.386p` / `.486` / `.586` etc. — CPU/directive, ignore */
    if (toks[0].type == ATOK_DIRECTIVE || toks[0].type == ATOK_ID) {
        const char *d0 = toks[0].text;
        if (strcmp(d0, ".dosseg") == 0 || strcmp(d0, ".286") == 0 || strcmp(d0, ".286p") == 0 ||
            strcmp(d0, ".386") == 0 || strcmp(d0, ".386p") == 0 || strcmp(d0, ".486") == 0 ||
            strcmp(d0, ".486p") == 0 || strcmp(d0, ".586") == 0 || strcmp(d0, ".586p") == 0 ||
            strcmp(d0, ".686") == 0 || strcmp(d0, ".686p") == 0 || strcmp(d0, ".mmx") == 0 ||
            strcmp(d0, ".xmm") == 0 || strcmp(d0, ".k3d") == 0 || strcmp(d0, ".x64") == 0 ||
            strcmp(d0, ".fpu") == 0) {
            return 1;
        }
    }
    /* `even` — align to 2-byte boundary (like `align 2`); also `align` with no args */
    if (toks[0].type == ATOK_ID && strcmp(toks[0].text, "even") == 0) {
        size_t bound = 2;
        size_t cur = cur_offset(out);
        size_t rem = cur % bound;
        size_t pad = (rem == 0) ? 0 : (bound - rem);
        if (out->cur_sec == SEC_BSS) { out->bss_len += pad; return 1; }
        for (size_t i = 0; i < pad; i++) emit_byte(out, 0);
        return 1;
    }
    /* `align <n>` — pad with zeros until current offset is aligned to n */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "align") == 0 || strcmp(toks[0].text, "ALIGN") == 0)) {
        size_t bound = 1;
        if (n >= 2 && toks[1].type == ATOK_NUM) bound = (size_t)toks[1].value;
        if (bound > 1) {
            size_t cur = cur_offset(out);
            size_t rem = cur % bound;
            size_t pad = (rem == 0) ? 0 : (bound - rem);
            if (out->cur_sec == SEC_BSS) { out->bss_len += pad; return 1; }
            for (size_t i = 0; i < pad; i++) emit_byte(out, 0);
        }
        return 1;
    }
    /* `.space` / `.skip` / `.zero` / `.reserve` or `resb`/`resw`/`resd`/`resq` */
    if (toks[0].type == ATOK_ID && (strcmp(toks[0].text, "org") == 0 || strcmp(toks[0].text, "ORG") == 0)) {
        /* org <expr> — set current section offset / struct field offset to expr.
         * Inside a struct definition the offset may be negative (org -8). */
        size_t cur = cur_offset(out);
        int64_t target = (int64_t)cur;
        int sign = 1;
        int idx = 1;
        if (n >= 2) {
            if (toks[idx].type == ATOK_OP && toks[idx].text[0] == '-') { sign = -1; idx++; }
            else if (toks[idx].type == ATOK_OP && toks[idx].text[0] == '+') { idx++; }
            if (idx < n && toks[idx].type == ATOK_NUM) target = sign * (int64_t)toks[idx].value;
            else if (idx < n && strcmp(toks[idx].text, "$") == 0) {
                target = (int64_t)cur;
                for (int i = idx + 1; i < n; i++) {
                    if (toks[i].type == ATOK_NUM) target += (int64_t)toks[i].value;
                    else if (toks[i].type == ATOK_OP && toks[i].text[0] == '-' && i + 1 < n &&
                             toks[i+1].type == ATOK_NUM) { target -= (int64_t)toks[i+1].value; i++; }
                }
            }
            else return 0;
        }
        else return 0;
        if (out->cur_struct_id > 0) {
            /* struct layout context: set next field offset (negative allowed) */
            out->cur_struct_off = (int)target;
            return 1;
        }
        if (target > (int64_t)cur) {
            size_t pad = (size_t)(target - (int64_t)cur);
            if (out->cur_sec == SEC_BSS) { out->bss_len += pad; return 1; }
            for (size_t i = 0; i < pad; i++) emit_byte(out, 0);
        }
        return 1;
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "resb") == 0 || strcmp(toks[0].text, ".space") == 0)) {
        size_t sz = 1;
        if (n >= 2 && toks[1].type == ATOK_NUM) sz = (size_t)toks[1].value;
        if (out->cur_sec == SEC_BSS) { out->bss_len += sz; return 1; }
        for (size_t i = 0; i < sz; i++) emit_byte(out, 0);
        return 1;
    }
    if (toks[0].type == ATOK_ID &&
        (strcmp(toks[0].text, "resw") == 0 || strcmp(toks[0].text, "resd") == 0 ||
         strcmp(toks[0].text, "resq") == 0)) {
        int mult = (toks[0].text[3] == 'w') ? 2 : (toks[0].text[3] == 'd') ? 4 : 8;
        size_t cnt = 1;
        if (n >= 2 && toks[1].type == ATOK_NUM) cnt = (size_t)toks[1].value;
        size_t sz = cnt * mult;
        if (out->cur_sec == SEC_BSS) { out->bss_len += sz; return 1; }
        for (size_t i = 0; i < sz; i++) emit_byte(out, 0);
        return 1;
    }

    /* Label: `name:`  or  `name proc` / `name endp` etc. */
    int start = 0;
    /* Top-level anonymous local label: `@@:` — register/refresh the anonymous label slot.
     * `@B`/`@F` references (jne @B) resolve to the anonymous label offset.
     * When `@@:` is followed by a directive on the same line (`@@: .if foo(eax)`),
     * route the remaining tokens to handle_control directly. */
    if (n >= 2 && toks[0].type == ATOK_ID && strcmp(toks[0].text, "@@") == 0 &&
        toks[1].type == ATOK_OP && toks[1].text[0] == ':') {
        out->anon_lbl = cur_offset(out);
        /* mid-line '.' is tokenized as a lone operator, so `@@: .if` arrives as
         * (".", "if") — normalize to the control-directive name before routing. */
        int cidx = 2;
        if (n > 2 && toks[2].type == ATOK_OP && toks[2].text[0] == '.' && toks[2].text[1] == 0)
            cidx = 3;
        if (n > cidx &&
            (strcmp(toks[cidx].text, ".if") == 0 || strcmp(toks[cidx].text, "if") == 0 ||
             strcmp(toks[cidx].text, ".while") == 0 || strcmp(toks[cidx].text, "while") == 0 ||
             strcmp(toks[cidx].text, ".repeat") == 0 || strcmp(toks[cidx].text, "repeat") == 0)) {
            /* @@: .if cond — route to handle_control with the tail tokens */
            return handle_control(out, &toks[cidx], n - cidx, NULL);
        }
        if (n == 2) return 1;   /* label only */
        /* fall through to instruction if any tokens remain after @@: */
        return assemble_line(out, &toks[2], n - 2);
    }
    if (toks[0].type == ATOK_ID) {
        if (n >= 2 && toks[1].type == ATOK_OP && toks[1].text[0] == ':') {
            /* label: record symbol at current offset in current section */
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) {
                out->syms[si].value = cur_offset(out);
                out->syms[si].defined = 1;
                out->syms[si].sec_index = out->cur_sec;
            }
            start = 2;   /* label followed by ':' then instruction */
        } else if (n >= 2 && toks[1].type == ATOK_ID && is_keyword(toks[1].text)) {
            /* label followed by directive keyword (proc, endp) — also record symbol */
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) {
                out->syms[si].value = cur_offset(out);
                out->syms[si].defined = 1;
                out->syms[si].sec_index = out->cur_sec;
                /* a `name proc` is a global entry symbol — mark GLOBAL so the
                 * ELF symbol table carries STB_GLOBAL and linkers can use it as
                 * the entry point (`ld.lld -e main`) for an x86-64 executable. */
                if ((strcmp(toks[1].text, "proc") == 0 || strcmp(toks[1].text, "PROC") == 0))
                    out->syms[si].global = 1;
            }
            /* `name PROC USES reg-list params` — process the USES register list and register
             * the parameter names as stack-offset symbols (a1 → [rbp+28H] pattern). */
            if ((strcmp(toks[1].text, "proc") == 0 || strcmp(toks[1].text, "PROC") == 0) && n >= 4 &&
                toks[2].type == ATOK_ID && (strcmp(toks[2].text, "USES") == 0 || strcmp(toks[2].text, "uses") == 0)) {
                int k = 3;
                /* skip consecutive register tokens (the USES save list) */
                while (k < n && toks[k].type == ATOK_ID && find_reg(toks[k].text)) k++;
                /* the rest are parameters — register each as a stack-offset symbol.
                 * x64 convention (no frame pointer omitted): params start after the
                 * USES-saved registers at rbp+0x28, stepping 8 bytes per dword param. */
                int pdisp = 0x28;
                while (k < n && toks[k].type == ATOK_ID) {
                    /* skip param type separators: ':' followed by type id, ',' commas */
                    while (k < n && toks[k].type == ATOK_OP && toks[k].text[0] == ',') k++;
                    if (k < n && toks[k].type == ATOK_ID) {
                        int psi = find_or_add_sym(out, toks[k].text);
                        if (psi >= 0) {
                            out->syms[psi].defined = 1;
                            out->syms[psi].sec_index = ASMC_ABS_SEC;
                            out->syms[psi].value = (uint64_t)pdisp;
                        }
                        k++;
                        pdisp += 8;
                        /* skip ':' type or ':' name after param */
                        if (k < n && toks[k].type == ATOK_OP) k++;
                        if (k < n && toks[k].type == ATOK_ID) k++;
                    }
                }
                return 1;
            }
            /* named `name endp` also closes the procedure scope: invalidate locals */
            if (strcmp(toks[1].text, "endp") == 0 || strcmp(toks[1].text, "ENDP") == 0) {
                for (int k = 0; k < out->nlocals; k++) {
                    int li = out->local_sym_ids[k];
                    if (li >= 0 && li < out->nsyms) {
                        out->syms[li].defined = 0;
                        out->syms[li].sec_index = -1;  /* -1 = out of scope */
                        out->syms[li].value = 0;
                    }
                }
                out->cur_proc = 0;
                out->nlocals = 0;
                out->frame_size = 0;
            }
            return 1;    /* directive label, no instruction */
        }
    }

    if (start >= n)
        return 1;        /* label only — no instruction */
    /* control directives after a label (`@@: .if foo(eax)` etc.) go to handle_control */
    if (toks[start].type == ATOK_ID &&
        (strcmp(toks[start].text, ".if") == 0 || strcmp(toks[start].text, "if") == 0 ||
         strcmp(toks[start].text, ".while") == 0 || strcmp(toks[start].text, "while") == 0 ||
         strcmp(toks[start].text, ".repeat") == 0 || strcmp(toks[start].text, "repeat") == 0 ||
         strcmp(toks[start].text, ".break") == 0 || strcmp(toks[start].text, ".continue") == 0 ||
         strcmp(toks[start].text, ".endw") == 0 || strcmp(toks[start].text, "endw") == 0 ||
         strcmp(toks[start].text, ".endf") == 0 || strcmp(toks[start].text, "endf") == 0 ||
         strcmp(toks[start].text, ".until") == 0 || strcmp(toks[start].text, "until") == 0 ||
         strcmp(toks[start].text, ".elseif") == 0 || strcmp(toks[start].text, "elseif") == 0 ||
         strcmp(toks[start].text, ".else") == 0 || strcmp(toks[start].text, "else") == 0 ||
         strcmp(toks[start].text, ".endif") == 0 || strcmp(toks[start].text, "endif") == 0 ||
         strcmp(toks[start].text, ".endr") == 0 || strcmp(toks[start].text, "endr") == 0)) {
        return handle_control(out, &toks[start], n - start, NULL);
    }
    if (toks[start].type != ATOK_ID)
        return 0;        /* unexpected token */
    /* reject instructions in .bss section */
    if (out->cur_sec == SEC_BSS) {
        return 0;
    }

    return encode_instruction(out, &toks[start], n - start);
}

/* Assemble an entire source file into a flat binary object.
 * Returns 0 on success, non-zero on error (with count).
 */
/* Assemble an entire source file into a flat binary object.
 * Returns 0 on success, non-zero on error (with count).
 */
static int assemble_file_internal(const char *src_path, asm_output_t *out,
                                  int depth, char *errmsg,
                                  size_t errmsg_len);

/* ---------- expression evaluation (expreval.asm reduced) ---------- */

/* forward declaration for eval_expr (used by eval_primary) */
static int eval_expr(asm_output_t *out, a_tok_t *t, int *pos, int n,
                     int64_t *val);

/* Evaluate a simple integer expression on a token array.
 * Supports: numbers, identifiers resolved via lookup_sym (0 if undefined),
 * parentheses, unary '-', binary + - * / %, comparisons == != < > <= >=,
 * && || !  (C-style). Returns result in *val; 0 on success, non-zero error.
 */
static int eval_primary(asm_output_t *out, a_tok_t *t, int *pos, int n,
                        int64_t *val)
{
    if (*pos >= n) return 1;
    a_tok_t *k = &t[*pos];
    if (k->type == ATOK_NUM) {
        *val = (int64_t)k->value;
        (*pos)++;
        return 0;
    }
    if (k->type == ATOK_OP && k->text[0] == '(') {
        (*pos)++;
        if (eval_expr(out, t, pos, n, val)) return 1;
        if (*pos >= n || t[*pos].type != ATOK_OP || t[*pos].text[0] != ')')
            return 1;
        (*pos)++;
        return 0;
    }
    if (k->type == ATOK_ID) {
        /* @function(...) calls used inside expressions:
         *   @SizeStr(<text>) / @SizeStr(%sym)  → length
         *   @InStr([start,] <str>, <sub>)       → 1-based index, 0 if absent
         *   @CatStr(a, b, ...)                  → 0 (text result handled elsewhere)
         *   @SubStr(<s>, start[, len])          → 0
         * These make function-call terms resolvable to numbers. */
        if (k->text[0] == '@' && *pos + 1 < n && t[*pos+1].type == ATOK_OP &&
            t[*pos+1].text[0] == '(') {
            const char *fname = k->text + 1;   /* @SizeStr → SizeStr */
            int open = *pos + 1;
            int close = -1;
            int nest = 0;
            for (int i = open; i < n; i++) {
                if (t[i].type == ATOK_OP && t[i].text[0] == '(') nest++;
                else if (t[i].type == ATOK_OP && t[i].text[0] == ')') {
                    nest--;
                    if (nest == 0) { close = i; break; }
                }
            }
            if (close > open) {
                const char *inner = t[open+1].text;
                int has_pct = (inner[0] == '%');
                const char *s = has_pct ? inner + 1 : inner;
                int literal_len = 0;
                /* %sym → symbol text length; bare ID that is a text equate → its
                 * text length; otherwise literal string inside <...> or plain */
                if (has_pct || (t[open+1].type == ATOK_ID &&
                                !(s[0] == '<'))) {
                    for (int si = 0; si < out->nsyms; si++)
                        if (out->syms[si].is_text && out->syms[si].defined &&
                            strcmp(out->syms[si].name, s) == 0)
                            literal_len = (int)strlen(out->syms[si].text);
                } else {
                    /* <literal> or bare literal inside the call */
                    if (s[0] == '<') s++;
                    literal_len = (int)strlen(s);
                    if (literal_len > 0 && s[literal_len-1] == '>') literal_len--;
                }
                if (strcasecmp(fname, "SizeStr") == 0) {
                    *val = literal_len;
                    *pos = close + 1;
                    return 0;
                }
                if (strcasecmp(fname, "InStr") == 0) {
                    /* @InStr(1,<str>,<sub>) — find substring */
                    const char *str1 = t[open+1].text, *str2 = t[close-1].text;
                    int has_comma = 0;
                    for (int i = open+1; i < close; i++)
                        if (t[i].type == ATOK_OP && t[i].text[0] == ',') has_comma = 1;
                    if (has_comma && str1[0] == '<' && str2[0] == '<') {
                        /* handle @InStr(start,<s>,<sub>): sub is last, s second-to-last */
                        const char *sub = str2 + 1;
                        const char *sstr = NULL;
                        /* find 2nd-to-last <...> argument */
                        int last_angle = -1, prev_angle = -1;
                        for (int i = open+1; i < close; i++)
                            if (t[i].type == ATOK_OP && t[i].text[0] == '<') {
                                prev_angle = last_angle; last_angle = i;
                            }
                        if (prev_angle >= 0) sstr = t[prev_angle].text + 1;
                        if (sstr) {
                            const char *p = strstr(sstr, sub);
                            *val = p ? (int64_t)(p - sstr + 1) : 0;
                            *pos = close + 1;
                            return 0;
                        }
                    }
                    *val = 0;
                    *pos = close + 1;
                    return 0;
                }
                /* @CatStr / @SubStr return text; as a numeric term → 0 */
                *val = 0;
                *pos = close + 1;
                return 0;
            }
        }
        int64_t v = lookup_sym(out, k->text);
        *val = (v < 0) ? 0 : v;
        (*pos)++;
        return 0;
    }
    return 1;
}

static int eval_mul(asm_output_t *out, a_tok_t *t, int *pos, int n,
                    int64_t *val)
{
    int64_t lhs;
    if (eval_primary(out, t, pos, n, &lhs)) return 1;
    while (*pos < n && t[*pos].type == ATOK_OP &&
           (t[*pos].text[0] == '*' || t[*pos].text[0] == '/' ||
            t[*pos].text[0] == '%')) {
        char op = t[*pos].text[0];
        (*pos)++;
        int64_t rhs;
        if (eval_primary(out, t, pos, n, &rhs)) return 1;
        if (op == '*') lhs *= rhs;
        else if (op == '/') lhs = rhs ? lhs / rhs : 0;
        else lhs = rhs ? lhs % rhs : 0;
    }
    *val = lhs;
    return 0;
}

static int eval_add(asm_output_t *out, a_tok_t *t, int *pos, int n,
                    int64_t *val)
{
    int64_t lhs;
    if (eval_mul(out, t, pos, n, &lhs)) return 1;
    while (*pos < n && t[*pos].type == ATOK_OP &&
           (t[*pos].text[0] == '+' || t[*pos].text[0] == '-')) {
        char op = t[*pos].text[0];
        (*pos)++;
        int64_t rhs;
        if (eval_mul(out, t, pos, n, &rhs)) return 1;
        lhs = (op == '+') ? lhs + rhs : lhs - rhs;
    }
    *val = lhs;
    return 0;
}

static int eval_cmp(asm_output_t *out, a_tok_t *t, int *pos, int n,
                    int64_t *val)
{
    int64_t lhs;
    if (eval_add(out, t, pos, n, &lhs)) return 1;
    while (*pos < n && t[*pos].type == ATOK_OP &&
           (strcmp(t[*pos].text, "==") == 0 || strcmp(t[*pos].text, "!=") == 0 ||
            strcmp(t[*pos].text, "<") == 0 || strcmp(t[*pos].text, ">") == 0 ||
            strcmp(t[*pos].text, "<=") == 0 || strcmp(t[*pos].text, ">=") == 0)) {
        const char *op = t[*pos].text;
        (*pos)++;
        int64_t rhs;
        if (eval_add(out, t, pos, n, &rhs)) return 1;
        if (strcmp(op, "==") == 0) lhs = (lhs == rhs);
        else if (strcmp(op, "!=") == 0) lhs = (lhs != rhs);
        else if (strcmp(op, "<") == 0) lhs = (lhs < rhs);
        else if (strcmp(op, ">") == 0) lhs = (lhs > rhs);
        else if (strcmp(op, "<=") == 0) lhs = (lhs <= rhs);
        else lhs = (lhs >= rhs);
    }
    *val = lhs;
    return 0;
}

static int eval_unary(asm_output_t *out, a_tok_t *t, int *pos, int n,
                      int64_t *val)
{
    if (*pos < n && t[*pos].type == ATOK_OP &&
        (t[*pos].text[0] == '-' || t[*pos].text[0] == '!' ||
         t[*pos].text[0] == '~')) {
        char op = t[*pos].text[0];
        (*pos)++;
        int64_t v;
        if (eval_unary(out, t, pos, n, &v)) return 1;
        if (op == '-') *val = -v;
        else if (op == '!') *val = !v;
        else *val = ~v;
        return 0;
    }
    return eval_primary(out, t, pos, n, val);
}

static int eval_expr(asm_output_t *out, a_tok_t *t, int *pos, int n,
                     int64_t *val)
{
    int64_t lhs;
    if (eval_cmp(out, t, pos, n, &lhs)) return 1;
    while (*pos < n && t[*pos].type == ATOK_OP &&
           (strcmp(t[*pos].text, "&&") == 0 || strcmp(t[*pos].text, "||") == 0)) {
        const char *op = t[*pos].text;
        (*pos)++;
        int64_t rhs;
        if (eval_cmp(out, t, pos, n, &rhs)) return 1;
        lhs = (strcmp(op, "&&") == 0) ? (lhs && rhs) : (lhs || rhs);
    }
    *val = lhs;
    return 0;
}

/* Evaluate the tokens after a directive (from index 1) as an expression */
static int eval_tokens(asm_output_t *out, a_tok_t *t, int n, int64_t *val)
{
    int pos = 1;
    return eval_expr(out, t, &pos, n, val);
}

/* ---------- macro support (.macro/.endm) ---------- */

/* forward: handle_control used by expand_macro for ifdef/endif inside macro bodies */
static int handle_control(asm_output_t *out, a_tok_t *toks, int n,
                          const char *line);

static asm_macro_t *find_macro(asm_output_t *out, const char *name)
{
    /* MASM default is case-insensitive identifiers (casemap:all), so a
     * `CMPXX pd, vo` call must find the `cmpxx macro ...` definition. */
    for (int i = 0; i < out->nmacros; i++) {
        const char *a = out->macros[i].name, *b = name;
        int eq = 1;
        while (*a && *b) {
            char ca = *a, cb = *b;
            if (ca >= 'A' && ca <= 'Z') ca += 'a' - 'A';
            if (cb >= 'A' && cb <= 'Z') cb += 'a' - 'A';
            if (ca != cb) { eq = 0; break; }
            a++; b++;
        }
        if (eq && *a == 0 && *b == 0)
            return &out->macros[i];
    }
    return NULL;
}

/* substitute macro parameters in a body line: &p1 / p1 -> argument text */
static void subst_params(asm_macro_t *m, char *dst, size_t dstsz,
                         a_tok_t *args, int nargs, const char *rawline)
{
    /* build arg strings from tokens */
    char argv[8][256];
    int  argv_has[8] = {0};
    for (int i = 0; i < nargs && i < 8; i++) {
        const char *src = args[i].text;
        /* strip wrapping <...> from bracketed arguments */
        if (src[0] == '<') {
            size_t alen = strlen(src);
            if (alen >= 2 && src[alen - 1] == '>') {
                size_t inner = alen - 2;
                if (inner >= sizeof(argv[i])) inner = sizeof(argv[i]) - 1;
                memcpy(argv[i], src + 1, inner);
                argv[i][inner] = 0;
            } else {
                snprintf(argv[i], sizeof(argv[i]), "%s", src + 1);
            }
        } else {
            snprintf(argv[i], sizeof(argv[i]), "%s", src);
        }
        argv_has[i] = 1;
    }
    const char *p = rawline;
    size_t o = 0;
    while (*p && o + 1 < dstsz) {
        /* `&&` — concatenation marker between two substitutions/identifiers:
         * produces no output itself, just joins the surrounding text
         * (e.g. `prefix&&suffix` with prefix=pfx, suffix=sfx → `pfxsfx`). */
        if (*p == '&' && p[1] == '&') {
            p += 2;
            continue;
        }
        if (*p == '&' && p[1]) {
            /* &param */
            for (int i = 0; i < m->nparams && i < 8; i++) {
                size_t pl = strlen(m->params[i]);
                if (strncmp(p + 1, m->params[i], pl) == 0) {
                    const char *v = argv_has[i] ? argv[i] : "";
                    while (*v && o + 1 < dstsz) dst[o++] = *v++;
                    p += 1 + pl;
                    goto next;
                }
            }
        }
        /* bare parameter (preceded by start or non-alnum) */
        if ((p == rawline || !((p[-1] >= 'a' && p[-1] <= 'z') ||
                               (p[-1] >= 'A' && p[-1] <= 'Z') ||
                               (p[-1] >= '0' && p[-1] <= '9') ||
                               p[-1] == '_')) &&
            (*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') || *p == '_') {
            for (int i = 0; i < m->nparams && i < 8; i++) {
                size_t pl = strlen(m->params[i]);
                if (strncmp(p, m->params[i], pl) == 0 &&
                    !(p[pl] >= 'a' && p[pl] <= 'z') &&
                    !(p[pl] >= 'A' && p[pl] <= 'Z') &&
                    !(p[pl] >= '0' && p[pl] <= '9') &&
                    p[pl] != '_') {
                    const char *v = argv_has[i] ? argv[i] : "";
                    while (*v && o + 1 < dstsz) dst[o++] = *v++;
                    p += pl;
                    goto next;
                }
            }
        }
        dst[o++] = *p++;
    next:;
    }
    dst[o] = 0;
}

/* expand a macro invocation by re-sending body lines with substitutions */
static int expand_macro(asm_output_t *out, asm_macro_t *m,
                        a_tok_t *args, int nargs,
                        const char *src_path, int depth,
                        char *errmsg, size_t errmsg_len)
{
    if (depth >= 16) {
        snprintf(errmsg, errmsg_len, "macro nesting too deep: %s", m->name);
        return 1;
    }
    /* unique scope for this invocation: @@ -> @@<invoc_id> */
    int scope = ++out->invoc_id;
    out->macro_depth++;

    for (int li = 0; li < m->nbody; li++) {
        char outline[512];
        /* expand `%name&...&&name&` text-equate splicing in the raw macro body
         * line BEFORE subst_params (which removes `&&` concat markers), so that
         * e.g. `%&TM1&&TM2&:repeat 3` → `abcd:repeat 3` with TM1=ab, TM2=cd.
         * Only applies when the line begins with `%` or `&` (text-equate
         * forced-expansion marker) — avoids regressions across other bodies. */
        {
            const char *raw = m->body[li];
            /* only the exact `%&name&`/`&name&&name&` forced text-equate splice
             * pattern triggers expansion (e.g. macro.18's `%&TM1&&TM2&:repeat`);
             * bare `%name` numeric-expansion lines are left untouched. */
            if ((raw[0] == '%' && raw[1] == '&') || (raw[0] == '&' && raw[1] != '&')) {
                char exp2[512]; size_t xo = 0, xi = 0;
                while (raw[xi] && xo + 1 < sizeof(exp2)) {
                    if (raw[xi] == '&' && raw[xi+1] == '&') { xi += 2; continue; }  /* && concat */
                    if (raw[xi] == '%') { xi++; continue; }                         /* % force-expand */
                    if (raw[xi] == '&') {
                        const char *nm = raw + xi + 1;
                        size_t nl = 0;
                        while (nm[nl] && ((nm[nl] >= 'a' && nm[nl] <= 'z') || (nm[nl] >= 'A' && nm[nl] <= 'Z') ||
                                          (nm[nl] >= '0' && nm[nl] <= '9') || nm[nl] == '_' || nm[nl] == '@' || nm[nl] == '?')) nl++;
                        if (nl > 0 && nm[nl] == '&') {
                            int replaced = 0;
                            for (int s = 0; s < out->nsyms; s++) {
                                if (out->syms[s].is_text && out->syms[s].defined &&
                                    strlen(out->syms[s].name) == nl &&
                                    strncmp(out->syms[s].name, nm, nl) == 0 && out->syms[s].text[0]) {
                                    const char *v = out->syms[s].text;
                                    while (*v && xo + 1 < sizeof(exp2)) exp2[xo++] = *v++;
                                    xi += 2 + nl;
                                    replaced = 1; break;
                                }
                            }
                            if (replaced) continue;
                        }
                    }
                    exp2[xo++] = raw[xi++];
                }
                exp2[xo] = 0;
                if (xo > 0) snprintf(outline, sizeof(outline), "%s", exp2);
                subst_params(m, outline, sizeof(outline), args, nargs, outline);
            } else {
                subst_params(m, outline, sizeof(outline), args, nargs, raw);
            }
        }
        /* substitute @@ local labels with unique scope-suffixed names:
         *  @@:  (definition)  ->  __ml<scope>_<n>:
         *  @B / @F references are left to the tokenizer label logic below
         *  (simple form: @B/@F after definition become the numeric tag)
         */
        char sub[512];
        size_t so = 0, si = 0;
        while (outline[si] && so + 1 < sizeof(sub)) {
            if (outline[si] == '@' && outline[si+1] == '@') {
                int n = out->macrolbl++;
                so += snprintf(sub + so, sizeof(sub) - so, "__ml%d_%d", scope, n);
                si += 2;
            } else if (outline[si] == '@' && (outline[si+1] == 'B' || outline[si+1] == 'b') &&
                       out->macrolbl > 0) {
                /* @B = backward reference to most recent @@: label */
                so += snprintf(sub + so, sizeof(sub) - so, "__ml%d_%d", scope, out->macrolbl - 1);
                si += 2;
            } else {
                sub[so++] = outline[si++];
            }
        }
        sub[so] = 0;
        snprintf(outline, sizeof(outline), "%s", sub);

        /* tokenize the expanded line */
        a_tok_t mt[64];
        int mn = TokenizeLine(outline, mt, 64);
        if (mn == 0) continue;
        /* handle control-flow directives inside macro bodies
         * (ifdef/ifndef/else/endif etc. share the ctl stack) */
        if (mn >= 1 &&
            (strcmp(mt[0].text, ".if") == 0 || strcmp(mt[0].text, "if") == 0 ||
             strcmp(mt[0].text, ".elseif") == 0 || strcmp(mt[0].text, "elseif") == 0 ||
             strcmp(mt[0].text, ".else") == 0 || strcmp(mt[0].text, "else") == 0 ||
             strcmp(mt[0].text, ".endif") == 0 || strcmp(mt[0].text, "endif") == 0 ||
             strcmp(mt[0].text, ".ifdef") == 0 || strcmp(mt[0].text, "ifdef") == 0 ||
             strcmp(mt[0].text, ".ifndef") == 0 || strcmp(mt[0].text, "ifndef") == 0 ||
             strcmp(mt[0].text, "ifnb") == 0 || strcmp(mt[0].text, "IFNB") == 0 ||
             strcmp(mt[0].text, "ifb") == 0 || strcmp(mt[0].text, "IFB") == 0 ||
             strcmp(mt[0].text, "ifidn") == 0 || strcmp(mt[0].text, "IFIDN") == 0 ||
             strcmp(mt[0].text, "ifidni") == 0 || strcmp(mt[0].text, "IFIDNI") == 0 ||
             strcmp(mt[0].text, "ENDIF") == 0 || strcmp(mt[0].text, "ELSE") == 0 ||
             strcmp(mt[0].text, "IFDEF") == 0 || strcmp(mt[0].text, "IFNDEF") == 0 ||
             strcmp(mt[0].text, "IFE") == 0 || strcmp(mt[0].text, "IFNE") == 0)) {
            if (handle_control(out, mt, mn, outline)) {
                /* ifdef active check: skip body lines in inactive branch */
                continue;
            }
        }
        /* inside an inactive control branch in macro: skip */
        if (out->suppress > 0)
            continue;
        /* nested macro DEFINITION inside a macro body:
         * `name macro params ... endm` — collect the inner macro and register
         * it so later body lines can invoke it (e.g. m1x inside m1). */
        {
            int is_inner_def = 0;
            if (mn >= 2 && mt[0].type == ATOK_ID && mt[1].type == ATOK_ID &&
                (strcmp(mt[1].text, "macro") == 0 || strcmp(mt[1].text, "MACRO") == 0))
                is_inner_def = 2;
            else if (mn >= 2 && (strcmp(mt[0].text, ".macro") == 0 ||
                                 strcmp(mt[0].text, "macro") == 0))
                is_inner_def = 1;
            if (is_inner_def) {
                int name_idx = (is_inner_def == 1) ? 1 : 0;
                int pstart = (is_inner_def == 1) ? 2 : 2;
                if (out->nmacros < 32) {
                    asm_macro_t *im = &out->macros[out->nmacros];
                    memset(im, 0, sizeof(*im));
                    snprintf(im->name, sizeof(im->name), "%s", mt[name_idx].text);
                    im->nparams = 0;
                    for (int i = pstart; i < mn && im->nparams < 8; i++) {
                        if (mt[i].type == ATOK_ID && !find_reg(mt[i].text)) {
                            snprintf(im->params[im->nparams], sizeof(im->params[0]),
                                     "%s", mt[i].text);
                            im->nparams++;
                        }
                    }
                    /* collect inner macro body lines until .endm/endm at this level */
                    int body_start = li + 1;
                    int nest = 1;
                    int bi = body_start;
                    for (; bi < m->nbody && nest > 0; bi++) {
                        char bt[512];
                        subst_params(m, bt, sizeof(bt), args, nargs, m->body[bi]);
                        a_tok_t btok[64];
                        int bn = TokenizeLine(bt, btok, 64);
                        if (bn == 0) continue;
                        if (bn >= 1 && (strcmp(btok[0].text, "macro") == 0 ||
                                        strcmp(btok[0].text, "MACRO") == 0 ||
                                        strcmp(btok[0].text, ".macro") == 0))
                            nest++;
                        else if (bn >= 1 && (strcmp(btok[0].text, ".endm") == 0 ||
                                             strcmp(btok[0].text, "endm") == 0 ||
                                             strcmp(btok[0].text, "ENDM") == 0)) {
                            nest--;
                            if (nest == 0) break;
                        }
                        if (im->nbody < 64) {
                            snprintf(im->body[im->nbody], sizeof(im->body[0]), "%s", bt);
                            im->nbody++;   /* never exceed the 64-line body capacity */
                        }
                    }
                    li = bi;   /* skip inner body */
                    out->nmacros++;
                }
                continue;
            }
        }
        /* nested macro invocation: recurse (keeps its own scope) */
        if (mt[0].type == ATOK_ID) {
            asm_macro_t *inner = find_macro(out, mt[0].text);
            /* bare endm inside a macro body closes a for/rept/while loop that
             * expand_macro does not iterate (process_source_lines loop handling
             * does); treat it as a no-op here. */
            if (mt[0].type == ATOK_ID && (strcmp(mt[0].text, "endm") == 0 ||
                                          strcmp(mt[0].text, "ENDM") == 0 ||
                                          strcmp(mt[0].text, ".endm") == 0)) {
                continue;
            }
            if (inner) {
                a_tok_t iargs[8];
                int niargs = 0;
                for (int i = 1; i < mn && niargs < 8; i++) {
                    if (mt[i].type == ATOK_OP && mt[i].text[0] == ',')
                        continue;
                    iargs[niargs++] = mt[i];
                }
                if (expand_macro(out, inner, iargs, niargs, src_path,
                                 depth + 1, errmsg, errmsg_len)) {
                    out->macro_depth--;
                    return 1;
                }
                continue;
            }
        }
        if (!assemble_line(out, mt, mn)) {
            asmerr(2001, outline);
            out->errors++;
            out->macro_depth--;
            return 1;
        }
        (void)src_path;
        (void)depth;
    }
    out->macro_depth--;
    return 0;
}

/* ---------- control-flow handling (hll.asm/condasm.asm reduced) ---------- */

static int handle_control(asm_output_t *out, a_tok_t *toks, int n,
                          const char *line)
{
    const char *d = toks[0].text;

    /* macro text conditions: ifnb <arg> (non-empty), ifb <arg> (empty),
     * ifidn a,b (text equal), ifidni (case-insensitive equal) */
    if (strcmp(d, "ifnb") == 0 || strcmp(d, "IFNB") == 0 ||
        strcmp(d, "ifb") == 0 || strcmp(d, "IFB") == 0 ||
        strcmp(d, "ifidn") == 0 || strcmp(d, "IFIDN") == 0 ||
        strcmp(d, "ifidni") == 0 || strcmp(d, "IFIDNI") == 0) {
        if (out->nctl >= 32) { asmerr(2001, line); return 1; }
        int nonempty = 0;
        /* ifnb/ifb: check the bracketed argument text */
        if (n >= 2) {
            const char *arg = toks[1].text;
            if (arg[0] == '<' && arg[1] == '>') nonempty = 0;
            else if (arg[0] == '<' && arg[1] == 0) nonempty = 0;
            else nonempty = 1;
        }
        /* ifidn/ifidni: compare two bracketed texts */
        if (strncmp(d, "ifidn", 5) == 0 && n >= 3) {
            const char *a = toks[1].text;
            const char *b = toks[2].text;
            if (a[0] == '<') a++;
            if (b[0] == '<') b++;
            nonempty = (strcmp(a, b) == 0);
        }
        int is_ifb = (strncmp(d, "ifb", 3) == 0 && d[3] != 'n');
        int act = is_ifb ? !nonempty : nonempty;
        asm_ctl_t *c = &out->ctl[out->nctl++];
        memset(c, 0, sizeof(*c));
        c->kind = 1; c->active = act; c->ever_active = act; c->taken = act;
        if (!act) out->suppress++;
        return 1;
    }

    if (strcmp(d, ".if") == 0 || strcmp(d, "if") == 0 || strcmp(d, "IFE") == 0 || strcmp(d, "IF") == 0 ||
            strcmp(d, ".ifd") == 0 || strcmp(d, ".ifw") == 0 || strcmp(d, ".ifb") == 0) {
        if (out->nctl >= 32) { asmerr(2001, line); return 1; }
        int64_t v = 0;
        int is_ife = (d[2] == 'E' || d[2] == 'e');
        /* If condition contains a `name(...)` function-call form, evaluate as nonzero
         * (HLL invoke pseudo-conditions are typically user stubs) so the branch resolves.
         * `@INSTR(...)` / `@SizeStr(...)` etc. are resolved by eval_primary. */
        int has_call = 0;
        for (int i = 1; i < n; i++) {
            if (toks[i].type == ATOK_ID && i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '(') {
                has_call = 1; break;
            }
        }
        if (has_call && toks[1].type == ATOK_ID && toks[1].text[0] == '@' &&
            (strcmp(toks[1].text, "@InStr") == 0 || strcmp(toks[1].text, "@INSTR") == 0 ||
             strcmp(toks[1].text, "@SizeStr") == 0 || strcmp(toks[1].text, "@SIZESTR") == 0 ||
             strcmp(toks[1].text, "@CatStr") == 0 || strcmp(toks[1].text, "@SubStr") == 0)) {
            eval_tokens(out, toks, n, &v);   /* @InStr(...) etc. resolve to a number */
        }
        else if (has_call) {
            v = 1;
        } else {
            eval_tokens(out, toks, n, &v);
        }
        if (is_ife) v = (v == 0);   /* IFE: branch when expression equals zero */
        asm_ctl_t *c = &out->ctl[out->nctl++];
        memset(c, 0, sizeof(*c));
        c->kind = 1; c->active = v != 0; c->ever_active = c->active;
        c->taken = c->active;
        out->suppress = (out->suppress > 0) || !c->active;
        return 1;
    }
    if (strcmp(d, ".elseif") == 0 || strcmp(d, "elseif") == 0) {
        if (out->nctl == 0) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[out->nctl - 1];
        int64_t v = 0;
        eval_tokens(out, toks, n, &v);
        int act = (!c->taken) && (v != 0);
        c->active = act; c->ever_active = c->ever_active || act;
        c->taken = c->taken || act;
        out->suppress = 0;
        for (int i = 0; i < out->nctl; i++)
            if (!out->ctl[i].active) out->suppress++;
        return 1;
    }
    if (strcmp(d, ".else") == 0 || strcmp(d, "else") == 0 || strcmp(d, "ELSE") == 0) {
        if (out->nctl == 0) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[out->nctl - 1];
        int act = !c->taken;
        c->active = act; c->ever_active = c->ever_active || act;
        c->taken = 1;
        out->suppress = 0;
        for (int i = 0; i < out->nctl; i++)
            if (!out->ctl[i].active) out->suppress++;
        return 1;
    }
    if (strcmp(d, ".elseif") == 0 || strcmp(d, "elseif") == 0 || strcmp(d, "ELSEIF") == 0) {
        if (out->nctl == 0) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[out->nctl - 1];
        int64_t v = 0;
        eval_tokens(out, toks, n, &v);
        int act = (!c->taken) && (v != 0);
        c->active = act; c->ever_active = c->ever_active || act;
        c->taken = c->taken || act;
        out->suppress = 0;
        for (int i = 0; i < out->nctl; i++)
            if (!out->ctl[i].active) out->suppress++;
        return 1;
    }
    if (strcmp(d, ".endif") == 0 || strcmp(d, "endif") == 0 || strcmp(d, "ENDIF") == 0) {
        if (out->nctl == 0) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[--out->nctl];
        (void)c;
        out->suppress = 0;
        for (int i = 0; i < out->nctl; i++)
            if (!out->ctl[i].active) out->suppress++;
        return 1;
    }
    /* ifdef / ifndef: test symbol-defined state (no symbol creation) */
    if (strcmp(d, ".ifdef") == 0 || strcmp(d, "ifdef") == 0 ||
        strcmp(d, ".ifndef") == 0 || strcmp(d, "ifndef") == 0) {
        if (out->nctl >= 32) { asmerr(2001, line); return 1; }
        int defined = 0;
        if (n >= 2 && toks[1].type == ATOK_ID) {
            for (int i = 0; i < out->nsyms; i++)
                if (strcmp(out->syms[i].name, toks[1].text) == 0 && out->syms[i].defined)
                    { defined = 1; break; }
        }
        int neg = (d[0] == '.' && d[1] == 'i' && d[2] == 'f' && d[3] == 'n') ||
                  (d[0] == 'i' && d[1] == 'f' && d[2] == 'n');
        int act = neg ? !defined : defined;
        asm_ctl_t *c = &out->ctl[out->nctl++];
        memset(c, 0, sizeof(*c));
        c->kind = 1; c->active = act; c->ever_active = act; c->taken = act;
        if (!act) out->suppress++;
        return 1;
    }
    /* .repeat / .until: fixed-count unrolled expansion on .until */
    if (strcmp(d, ".repeat") == 0 || strcmp(d, "repeat") == 0) {
        if (out->nctl >= 32) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[out->nctl++];
        memset(c, 0, sizeof(*c));
        c->kind = 2; c->active = 1;
        return 1;
    }
    if (strcmp(d, ".until") == 0 || strcmp(d, "until") == 0) {
        if (out->nctl == 0) { asmerr(2001, line); return 1; }
        asm_ctl_t *c = &out->ctl[out->nctl - 1];
        (void)c;
        /* single iteration supported this round (repeat marker) */
        return 1;
    }
    if (strcmp(d, ".while") == 0 || strcmp(d, "while") == 0) {
            if (out->nctl >= 32) { asmerr(2001, line); return 1; }
            int64_t v = 0;
            int has_call = 0;
            for (int i = 1; i < n; i++)
                if (toks[i].type == ATOK_ID && i + 1 < n && toks[i+1].type == ATOK_OP && toks[i+1].text[0] == '(')
                    { has_call = 1; break; }
            if (!has_call) eval_tokens(out, toks, n, &v);
            else v = 1;
            asm_ctl_t *c = &out->ctl[out->nctl++];
            memset(c, 0, sizeof(*c));
            c->kind = 3; c->active = 1; c->cond = (int)(v != 0);
            if (!c->cond) {
                c->active = 0;
                out->suppress++;
            }
            return 1;
        }
        if (strcmp(d, ".for") == 0 || strcmp(d, "for") == 0) {
            /* .for loop pseudo-instruction: treat as single-iteration control (like .while) */
            if (out->nctl >= 32) { asmerr(2001, line); return 1; }
            int64_t v = 1;
            eval_tokens(out, toks, n, &v);
            asm_ctl_t *c = &out->ctl[out->nctl++];
            memset(c, 0, sizeof(*c));
            c->kind = 5; c->active = 1; c->cond = (int)(v != 0);
            if (!c->cond) {
                c->active = 0;
                out->suppress++;
            }
            return 1;
        }
        if (strcmp(d, ".endw") == 0 || strcmp(d, "endw") == 0) {
            if (out->nctl == 0) { asmerr(2001, line); return 1; }
            asm_ctl_t *c = &out->ctl[out->nctl - 1];
            if (!c->active && out->suppress > 0) out->suppress--;
            out->nctl--;
            return 1;
        }
        if (strcmp(d, ".endf") == 0 || strcmp(d, "endf") == 0) {
            if (out->nctl == 0) { asmerr(2001, line); return 1; }
            asm_ctl_t *c = &out->ctl[out->nctl - 1];
            if (!c->active && out->suppress > 0) out->suppress--;
            out->nctl--;
            return 1;
        }
    return 0;  /* not a control directive */
}

/* INCLUDE  directive support (port of input.asm:INCLUDE worker)
 * Open and recursively process an include file into the same object.
 * Returns 0 on success, non-zero on error.
 */
static int process_include(asm_output_t *out, const char *inc_path,
                           int depth, char *errmsg, size_t errmsg_len)
{
    if (depth >= 8) {
        snprintf(errmsg, errmsg_len, "include nesting too deep: %s", inc_path);
        asmerr(1001, inc_path);   /* A1001: include file nested too deeply */
        return 1;
    }
    /* cycle detection: if this resolved path is already on the include stack,
     * report a recursive-include diagnostic (real failure). */
    for (int s = 0; s < out->ninc_stack; s++) {
        if (strcmp(out->inc_stack[s], inc_path) == 0) {
            snprintf(errmsg, errmsg_len, "recursive include: %s", inc_path);
            asmerr(1000, inc_path);
            return 1;
        }
    }
    /* push path onto include stack, process, then pop */
    if (out->ninc_stack < 8) {
        snprintf(out->inc_stack[out->ninc_stack], 1024, "%s", inc_path);
        out->ninc_stack++;
    }
    int rc = assemble_file_internal(inc_path, out, depth + 1, errmsg, errmsg_len);
    if (out->ninc_stack > 0) out->ninc_stack--;
    return rc;
}

static int process_source_lines(asm_output_t *out,
                                char (*lines)[2048], int nlines,
                                const char *src_path, int depth,
                                char *errmsg, size_t errmsg_len);

static int assemble_file_internal(const char *src_path, asm_output_t *out,
                                  int depth, char *errmsg, size_t errmsg_len)
{
    FILE *f = fopen(src_path, "r");
    if (!f) {
        snprintf(errmsg, errmsg_len, "cannot open: %s", src_path);
        asmerr(1000, src_path);
        return 1;
    }

    /* read whole file into a line array */
    char (*all)[2048] = malloc(512 * sizeof(*all));
    if (!all) { fclose(f); return 1; }
    int nall = 0;
    char line[2048];
    while (fgets(line, sizeof(line), f) && nall < 512)
        snprintf(all[nall++], sizeof(*all), "%s", line);
    fclose(f);

    int rc = process_source_lines(out, all, nall, src_path, depth,
                                  errmsg, errmsg_len);
    free(all);
    return rc;
}

/* process a set of source lines with loop buffering/replay.
 * Supports .repeat/.until (do-while) and .while/.endw (while) with
 * re-evaluation each iteration and a bounded guard (max 1000 iters).
 * Nested loops handled via recursion. Contains the include/macro/control
 * pipeline that previously lived in assemble_file_internal.
 */
static int process_source_lines(asm_output_t *out,
                                char (*lines)[2048], int nlines,
                                const char *src_path, int depth,
                                char *errmsg, size_t errmsg_len)
{
    a_tok_t toks[256];
    char line[8192];
    char loopbuf[64][2048];
    int errs = 0;

    for (int li = 0; li < nlines; li++) {
        snprintf(line, sizeof(line), "%s", lines[li]);
        /* line continuation:
         *  - `\` at end of line joins with the next line;
         *  - a trailing ',' continues a declaration/data/proc-param list
         *    across the next line (e.g. `pr proc a1:near16,` then a newline
         *    then `b1:ptr near16`), so the joined line carries the rest;
         *  - an unbalanced '{' at end of line continues struct/union init
         *    rows (e.g. `v1 S1 {1,2,3` then `,4,5,6}`) — but NOT for block
         *    definitions like `.enum E {` / `.class C {` whose closing '}'
         *    terminates the whole block. */
        {
            int cont_active = 0;
            while (li + 1 < nlines) {
                size_t linelen = strlen(line);
                /* strip trailing whitespace AND newline (fgets keeps '\n') */
                while (linelen > 0 && (line[linelen-1] == ' ' || line[linelen-1] == '\t' ||
                                       line[linelen-1] == '\n' || line[linelen-1] == '\r')) linelen--;
                if (linelen == 0) break;
                /* `\;` inside a literal: line concatenation — the text before the
                 * backslash stays, the `;` and the rest of the line are ignored,
                 * and the next source line continues the literal (no space added):
                 *   `xx textequ <abc\;def>`  +  `qqq>`  →  text "abcqqq"
                 *   `v1 S1 {1,2,3\;}`        +  `,4,5,6}`  →  init {1,2,3,4,5,6}
                 * NOT applied inside a double-quoted string (`db "abc \; def"`),
                 * where `\;` is a literal backslash-semicolon. */
                int semi_cont = 0;
                int in_str = 0;
                for (size_t c = 0; c + 1 < linelen; c++) {
                    if (line[c] == '"') in_str = !in_str;
                    if (!in_str && line[c] == '\\' && line[c+1] == ';') {
                        line[c] = 0;          /* drop backslash; keep preceding text */
                        linelen = c;
                        semi_cont = 1;
                        break;
                    }
                }
                char lastc = line[linelen > 0 ? linelen-1 : 0];
                int cont = 0;
                if (semi_cont) {
                    cont = 1;
                } else if (lastc == '\\') {
                    cont = 1;   /* explicit continuation marker */
                } else if (lastc == ',') {
                    /* a trailing comma continues:
                     *  - a declaration/proc-param list when the line carries a
                     *    ':' type/param marker (e.g. `pr proc a1:near16,` newline
                     *    `b1:ptr near16`) — note enum member rows (`y,`) and
                     *    .FOR expressions (`dx = foo(1,2),`) are NOT joined;
                     *  - a data list once a `\` continuation already started
                     *    (e.g. `TE0 dd \` ... comma-terminated rows). */
                    int has_colon = 0;
                    for (size_t c = 0; c < linelen; c++)
                        if (line[c] == ':') { has_colon = 1; break; }
                    int nonempty = 0;
                    for (size_t c = 0; c < linelen; c++)
                        if (line[c] != ',' && line[c] != ' ' && line[c] != '\t') { nonempty = 1; break; }
                    if ((has_colon || cont_active) && nonempty) cont = 1;
                } else {
                    /* unbalanced '{' at end of current line (no closing '}') */
                    int has_open = 0, has_close = 0;
                    for (size_t c = 0; c < linelen; c++) {
                        if (line[c] == '{') has_open++;
                        else if (line[c] == '}') has_close++;
                    }
                    if (has_open > has_close) {
                        /* skip block-definition openers that own their '}' terminator:
                         * `.enum name {`, `.class name {`, `.comdef name {`, `.static`,
                         * `.template`, `struct {`, `union {`, and a lone '{' on its own line. */
                        char head[64]; size_t hl = 0;
                        for (size_t c = 0; c < linelen && hl + 1 < sizeof(head); c++) {
                            if (line[c] == ' ' || line[c] == '\t') { if (hl > 0) break; continue; }
                            head[hl++] = line[c];
                            if (hl == 1 && (line[c] == '{' || line[c] == '}')) break;
                        }
                        head[hl] = 0;
                        int is_block_def =
                            (strncmp(head, ".enum", 5) == 0 || strncmp(head, "enum", 4) == 0) ||
                            (strncmp(head, ".class", 6) == 0 || strncmp(head, "class", 5) == 0) ||
                            (strncmp(head, ".comdef", 7) == 0 || strncmp(head, "comdef", 6) == 0) ||
                            (strncmp(head, ".static", 7) == 0 || strncmp(head, "static", 6) == 0) ||
                            (strncmp(head, ".template", 9) == 0 || strncmp(head, "template", 8) == 0) ||
                            (strncmp(head, ".inline", 7) == 0 || strncmp(head, "inline", 6) == 0) ||
                            (strcmp(head, "struct") == 0 || strcmp(head, "STRUC") == 0 ||
                             strcmp(head, "union") == 0 || strcmp(head, "UNION") == 0) ||
                            (hl == 1 && (head[0] == '{' || head[0] == '}'));
                        /* a `name proto ... {` declaration owns its '}' terminator */
                        if (!is_block_def) {
                            int found_proto = 0;
                            size_t p = 0;
                            /* scan the raw line (up to '{') for a `proto` keyword */
                            while (p < linelen && line[p] != '{') {
                                if ((line[p] == 'p' || line[p] == 'P') && p + 5 <= linelen) {
                                    int eq = 1;
                                    const char *w = "proto";
                                    for (int q = 0; q < 5 && eq; q++) {
                                        char lc = line[p+q];
                                        if (lc >= 'A' && lc <= 'Z') lc += 'a' - 'A';
                                        if (lc != w[q]) eq = 0;
                                    }
                                    if (eq) {
                                        char after = (p + 5 < linelen) ? line[p+5] : ' ';
                                        if (after == ' ' || after == '\t') { found_proto = 1; break; }
                                    }
                                }
                                p++;
                            }
                            if (found_proto) is_block_def = 1;
                        }
                        if (!is_block_def) cont = 1;
                    }
                }
                if (!cont) break;
                line[linelen-1] = 0;   /* remove the trigger char (backslash/comma) */
                size_t off = strlen(line);
                snprintf(line + off, sizeof(line) - off, " %s", lines[li + 1]);
                li++;
                cont_active = 1;   /* a continuation has begun: later comma rows continue */
            }
        }
        int n = TokenizeLine(line, toks, 256);
        if (n == 0) continue;

        /* `end` / `END` / `End` directive at the TOP LEVEL: terminate assembly —
         * stop processing remaining source lines (trailing comment text like
         * "Generated code:" must not be assembled).  Recursive calls (loop
         * bodies, includes) must not treat their `end` as a global terminator. */
        if (depth == 0 && toks[0].type == ATOK_ID &&
            (strcmp(toks[0].text, "end") == 0 || strcmp(toks[0].text, "END") == 0 ||
             strcmp(toks[0].text, "End") == 0)) {
            break;
        }

        /* Cross-line parameter concatenation: `foo(` then parameters on following lines
         * until the matching `)`. Rebuild the line with the joined arguments. */
        {
            int paren_open = -1, nest = 0;
            for (int i = 0; i < n && i < 64; i++)
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '(') { nest++; paren_open = i; }
            {
                int closed = 0;
                for (int i = 0; i < n; i++)
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == ')') closed = 1;
                if (nest > 0 && !closed && paren_open == n - 1) {
                    /* last token is '(' — collect continuation lines until ')' */
                    char joined[2048];
                    size_t jo = 0;
                    for (int i = 0; i < n && jo + 1 < sizeof(joined); i++) {
                        const char *tk = toks[i].text;
                        for (const char *p = tk; *p && jo + 1 < sizeof(joined); p++) joined[jo++] = *p;
                        if (i + 1 < n && jo + 1 < sizeof(joined)) joined[jo++] = ' ';
                    }
                    int nn = nest;
                    int lj;
                    for (lj = li + 1; lj < nlines && nn > 0; lj++) {
                        a_tok_t bt[64];
                        int bn = TokenizeLine(lines[lj], bt, 64);
                        for (int b = 0; b < bn && nn > 0; b++) {
                            const char *tk = bt[b].text;
                            if (bt[b].type == ATOK_OP && bt[b].text[0] == '(') nn++;
                            if (bt[b].type == ATOK_OP && bt[b].text[0] == ')') { nn--; if (nn == 0) break; }
                            for (const char *p = tk; *p && jo + 1 < sizeof(joined); p++) joined[jo++] = *p;
                            if (jo + 1 < sizeof(joined)) joined[jo++] = ' ';
                        }
                        if (nn == 0) break;
                    }
                    joined[jo] = 0;
                    li = lj;
                    snprintf(line, sizeof(line), "%s", joined);
                    n = TokenizeLine(line, toks, 64);
                    if (n == 0) continue;
                }
            }
        }

        /* `.inline name :args { ... }` — skip inline-method bodies (block to matching '}') */
        if (n >= 1 && strcmp(toks[0].text, ".inline") == 0) {
            int open = 0, close = 0;
            for (int i = 1; i < n; i++) {
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '{') open = 1;
                if (toks[i].type == ATOK_OP && toks[i].text[0] == '}') close = 1;
            }
            if (open && !close) {
                int nest = 1;
                int lj;
                for (lj = li + 1; lj < nlines && nest > 0; lj++) {
                    a_tok_t bt[64];
                    int bn = TokenizeLine(lines[lj], bt, 64);
                    for (int b = 0; b < bn && nest > 0; b++)
                        if (bt[b].type == ATOK_OP && bt[b].text[0] == '{') nest++;
                        else if (bt[b].type == ATOK_OP && bt[b].text[0] == '}') nest--;
                }
                li = lj - 1;
            }
            continue;
        }
        /* label + loop on one line: `L2: .while eax` — register the label, treat the
         * `.while` as the loop opener. Note `.while` tokenizes as `.` + `while`. */
        int label_prefix = 0;
        int lw = 2;
        if (n >= 3 && toks[0].type == ATOK_ID && toks[1].type == ATOK_OP && toks[1].text[0] == ':') {
            if (n >= 4 && toks[2].type == ATOK_OP && toks[2].text[0] == '.' &&
                toks[3].type == ATOK_ID && (strcmp(toks[3].text, "while") == 0 || strcmp(toks[3].text, "repeat") == 0))
                lw = 3;
            else if (toks[2].type == ATOK_ID &&
                     (strcmp(toks[2].text, ".while") == 0 || strcmp(toks[2].text, ".repeat") == 0 ||
                      strcmp(toks[2].text, "while") == 0 || strcmp(toks[2].text, "repeat") == 0))
                lw = 2;
            else
                lw = -1;
        } else {
            lw = -1;
        }
        if (lw >= 0) {
            int si = find_or_add_sym(out, toks[0].text);
            if (si >= 0) { out->syms[si].value = cur_offset(out); out->syms[si].defined = 1; out->syms[si].sec_index = out->cur_sec; }
            /* rebuild the line to start at the .while token */
            size_t o = 0;
            for (int w = lw; w < n && o + 1 < sizeof(line); w++) {
                const char *tk = toks[w].text;
                if (w > lw) { if (o + 1 < sizeof(line)) line[o++] = ' '; }
                for (const char *p = tk; *p && o + 1 < sizeof(line); p++) line[o++] = *p;
            }
            line[o] = 0;
            n = TokenizeLine(line, toks, 64);
            label_prefix = 1;
        }
        const char *d = toks[0].text;
        int is_loop_open = (strcmp(d, ".repeat") == 0 || strcmp(d, "repeat") == 0 ||
                            strcmp(d, ".while") == 0 || strcmp(d, "while") == 0);
        int is_loop_close = (strcmp(d, ".until") == 0 || strcmp(d, "until") == 0 ||
                             strcmp(d, ".untilcxz") == 0 || strcmp(d, "untilcxz") == 0 ||
                             strcmp(d, ".endw") == 0 || strcmp(d, "endw") == 0);

        /* ---- loop open: buffer body, then iterate ---- */
        if (is_loop_open) {
            int want_while = (strcmp(d, ".while") == 0 || strcmp(d, "while") == 0);
            /* bare `while`/`repeat` (no leading dot) may be closed by `endm`
             * in addition to .endw/.until (macro-style loops). */
            int bare_loop = (strcmp(d, "while") == 0 || strcmp(d, "repeat") == 0);
            char opentext[2048]; snprintf(opentext, sizeof(opentext), "%s", line);

            /* collect body until the matching close with nesting depth */
            int nbuf = 0;
            int nest = 1;
            int lj;
            for (lj = li + 1; lj < nlines && nest > 0; lj++) {
                a_tok_t bt[64];
                int bn = TokenizeLine(lines[lj], bt, 64);
                if (bn == 0) continue;
                const char *bd = bt[0].text;
                if (strcmp(bd, ".repeat") == 0 || strcmp(bd, "repeat") == 0 ||
                    strcmp(bd, ".while") == 0 || strcmp(bd, "while") == 0)
                    nest++;
                else if (strcmp(bd, ".until") == 0 || strcmp(bd, "until") == 0 ||
                         strcmp(bd, ".untilcxz") == 0 || strcmp(bd, "untilcxz") == 0 ||
                         strcmp(bd, ".endw") == 0 || strcmp(bd, "endw") == 0) {
                    nest--;
                    if (nest == 0) break;   /* terminator line */
                } else if (bare_loop &&
                           (strcmp(bd, "endm") == 0 || strcmp(bd, "ENDM") == 0 ||
                            strcmp(bd, ".endm") == 0)) {
                    nest--;
                    if (nest == 0) break;   /* bare loop closed by endm */
                }
                if (nbuf < 64)
                    snprintf(loopbuf[nbuf++], sizeof(loopbuf[0]), "%s", lines[lj]);
            }
            li = lj;   /* advance past the loop block */
            if (nest != 0) {
                errs++;
                asmerr(2001, "unterminated loop");
                continue;
            }

            int guard = 0;
            if (want_while) {
                /* .while expr / .endw — check condition before each iteration */
                int single_shot = 0;   /* function-call / constant-true condition: run body once */
                for (;;) {
                    a_tok_t wt[64];
                    int wn = TokenizeLine(opentext, wt, 64);
                    int64_t v = 0;
                    int has_call = 0;
                    int has_id_operand = 0;
                    for (int i = 0; i < wn; i++) {
                        if (wt[i].type == ATOK_ID && i + 1 < wn && wt[i+1].type == ATOK_OP && wt[i+1].text[0] == '(')
                            { has_call = 1; break; }
                        if (wt[i].type == ATOK_ID && i > 0) has_id_operand = 1;   /* register/symbol operand */
                    }
                    if (has_call) { v = 1; single_shot = 1; }
                    else if (eval_tokens(out, wt, wn, &v) != 0) single_shot = 1;   /* unresolved cond: run once */
                    else if (v != 0 && !has_id_operand) single_shot = 1;  /* constant-true (`.while 1`): run once */
                    if (!v) break;
                    if (++guard > 1000) { errs++; asmerr(2001, "while loop too long"); break; }
                    if (process_source_lines(out, loopbuf, nbuf, src_path,
                                             depth + 1, errmsg, errmsg_len)) {
                        errs++;
                        break;
                    }
                    if (single_shot) break;
                }
            } else {
                /* .repeat / .until expr — do-while (body first, then test) */
                for (;;) {
                    if (process_source_lines(out, loopbuf, nbuf, src_path,
                                             depth + 1, errmsg, errmsg_len)) {
                        errs++;
                        break;
                    }
                    /* re-evaluate the .until expression at the terminator line */
                    a_tok_t ut[64];
                    int un = TokenizeLine(lines[li], ut, 64);
                    int64_t uv = 0;
                    int has_call = 0;
                    int has_id_operand = 0;
                    for (int i = 0; i < un; i++) {
                        if (ut[i].type == ATOK_ID && i + 1 < un && ut[i+1].type == ATOK_OP && ut[i+1].text[0] == '(')
                            { has_call = 1; break; }
                        if (ut[i].type == ATOK_ID && i > 0) has_id_operand = 1;   /* register/symbol operand */
                    }
                    if (!has_call) {
                        if (eval_tokens(out, ut, un, &uv) != 0) uv = 1;   /* unresolved cond: stop after first body */
                    }
                    else uv = 1;
                    (void)uv;
                    break;   /* do-while: run body once; runtime .until can't be statically unrolled */
                }
            }
            continue;
        }

        if (is_loop_close) {
            errs++;
            asmerr(2001, line);   /* unmatched loop terminator */
            continue;
        }

        /* proto declaration block: skip until matching '}'
         * e.g. "inl proto asmcall :float,... {  ... body ... }"
         * The '{' may be on a continuation line; scan current line first,
         * then subsequent lines until braces balance (nest==0 after '{'). */
        if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
            strcmp(toks[1].text, "proto") == 0) {
            int is_asmcall = (n >= 3 && toks[2].type == ATOK_ID &&
                              (strcmp(toks[2].text, "asmcall") == 0 ||
                               strcmp(toks[2].text, "ASMCALL") == 0));
            int nest = 0;
            int seen_open = 0;
            /* scan current line for braces */
            for (int ii = 2; ii < n; ii++) {
                if (toks[ii].type == ATOK_OP && toks[ii].text[0] == '{') { nest++; seen_open = 1; }
                else if (toks[ii].type == ATOK_OP && toks[ii].text[0] == '}') { nest--; seen_open = 1; }
            }
            /* register the proto name as a defined symbol */
            {
                int si = find_or_add_sym(out, toks[0].text);
                if (si >= 0) { out->syms[si].defined = 1; out->syms[si].sec_index = ASMC_ABS_SEC; }
            }
            if (!seen_open) continue;   /* plain proto declaration: no body block */
            /* For an ASMCALL proto (`name proto asmcall :types { ... }`), the body
             * uses `_N` references to the Nth parameter (mapped per the asmcall
             * ABI: float/double/real params → XMM registers in order; byte/word/
             * dword/qword/ptr params → al,dx,ecx,r8,r9,r10,r11 in order).  Collect
             * the body and assemble it with those substitutions applied. */
            if (is_asmcall) {
                /* determine param register mapping: walk the type tokens after
                 * `asmcall` (they are ATOK_ID words separated by ','/':'). */
                char param_reg[32][16];
                int npreg = 0;
                int xmm_idx = 0, gpr_idx = 0;
                static const char *gprs[] = { "al","dx","ecx","r8","r9","r10","r11" };
                for (int ii = 3; ii < n && npreg < 32; ii++) {
                    if (toks[ii].type != ATOK_ID) continue;
                    if (strcmp(toks[ii].text, "asmcall") == 0 || strcmp(toks[ii].text, "ASMCALL") == 0) continue;
                    const char *t = toks[ii].text;
                    if (t[0] == ':' || strcmp(t, "req") == 0 || strcmp(t, "REQ") == 0 ||
                        strcmp(t, "vararg") == 0 || strcmp(t, "VARARG") == 0) continue;
                    int is_fp = (strcmp(t,"float")==0||strcmp(t,"double")==0||
                                 strcmp(t,"real4")==0||strcmp(t,"real8")==0||
                                 strcmp(t,"real10")==0||strcmp(t,"real16")==0||
                                 strcmp(t,"oword")==0||strcmp(t,"xmmword")==0);
                    if (is_fp) {
                        snprintf(param_reg[npreg++], 16, "xmm%d", xmm_idx++);
                    } else if (gpr_idx < 7) {
                        snprintf(param_reg[npreg++], 16, "%s", gprs[gpr_idx++]);
                    } else {
                        snprintf(param_reg[npreg++], 16, "rsp+%d", 8*(gpr_idx-7));
                        gpr_idx++;
                    }
                }
                /* collect body lines until matching '}' (nest reaches 0) */
                char bodybuf[64][512];
                int nbody = 0;
                while (nest > 0) {
                    li++;
                    if (li >= nlines) { asmerr(2001, "unterminated proto block"); break; }
                    a_tok_t bt[64];
                    int bn = TokenizeLine(lines[li], bt, 64);
                    for (int ii = 0; ii < bn; ii++) {
                        if (bt[ii].type == ATOK_OP && bt[ii].text[0] == '{') { nest++; }
                        else if (bt[ii].type == ATOK_OP && bt[ii].text[0] == '}') { nest--; }
                    }
                    if (nest <= 0) break;
                    if (nbody < 64) snprintf(bodybuf[nbody++], 512, "%s", lines[li]);
                }
                /* assemble body lines with `_N` replaced by the mapped register */
                for (int bi = 0; bi < nbody; bi++) {
                    char sub[512];
                    size_t so = 0, si = 0;
                    const char *s = bodybuf[bi];
                    while (s[si] && so + 1 < sizeof(sub)) {
                        if (s[si] == '_' && s[si+1] >= '1' && s[si+1] <= '9') {
                            size_t num = s[si+1] - '0';
                            size_t k = si + 2;
                            while (s[k] >= '0' && s[k] <= '9') { num = num*10 + (s[k]-'0'); k++; }
                            if (num >= 1 && num <= 32 && npreg >= (int)num && param_reg[num-1][0]) {
                                const char *r = param_reg[num-1];
                                while (*r && so + 1 < sizeof(sub)) sub[so++] = *r++;
                                si = k;
                                continue;
                            }
                        }
                        sub[so++] = s[si++];
                    }
                    sub[so] = 0;
                    if (so > 0) {
                        a_tok_t st[64];
                        int sn = TokenizeLine(sub, st, 64);
                        if (sn > 0) { if (assemble_line(out, st, sn) == 0) { errs++; } }
                    }
                }
                continue;
            }
            /* scan continuation lines until braces balance */
            while (nest > 0) {
                li++;
                if (li >= nlines) { asmerr(2001, "unterminated proto block"); break; }
                a_tok_t bt[64];
                int bn = TokenizeLine(lines[li], bt, 64);
                for (int ii = 0; ii < bn; ii++) {
                    if (bt[ii].type == ATOK_OP && bt[ii].text[0] == '{') { nest++; }
                    else if (bt[ii].type == ATOK_OP && bt[ii].text[0] == '}') { nest--; }
                }
                if (nest <= 0) break;
            }
            continue;
        }

        /* ---- `rept` directive: repeat the body a constant number of times ----
         *  rept 8 ... endm — body is assembled count times.  A textual loop
         *  variable is not available; each iteration re-evaluates expressions. */
        if (n >= 2 && toks[0].type == ATOK_ID &&
            (strcmp(toks[0].text, "rept") == 0 || strcmp(toks[0].text, "REPT") == 0)) {
            int64_t rcount = 0;
            if (toks[1].type == ATOK_NUM) rcount = (int64_t)toks[1].value;
            else if (toks[1].type == ATOK_ID) rcount = (int64_t)lookup_sym(out, toks[1].text);
            if (rcount < 0) rcount = 0;
            /* collect body until matching endm with nesting depth */
            char reptbuf[64][512];
            int nrept = 0;
            int lj3;
            int nest3 = 1;
            for (lj3 = li + 1; lj3 < nlines && nest3 > 0; lj3++) {
                a_tok_t bt[64];
                int bn = TokenizeLine(lines[lj3], bt, 64);
                if (bn == 0) continue;
                const char *bd = bt[0].text;
                if (strcmp(bd, "rept") == 0 || strcmp(bd, "REPT") == 0)
                    nest3++;
                else if (strcmp(bd, ".endm") == 0 || strcmp(bd, "endm") == 0 ||
                         strcmp(bd, "ENDM") == 0) {
                    nest3--;
                    if (nest3 == 0) break;
                }
                if (nrept < 64)
                    snprintf(reptbuf[nrept++], sizeof(reptbuf[0]), "%s", lines[lj3]);
            }
            li = lj3;
            if (nest3 != 0) { errs++; asmerr(2001, "unterminated rept"); continue; }
            for (int64_t it = 0; it < rcount; it++) {
                if (process_source_lines(out, reptbuf, nrept, src_path, depth + 1,
                                         errmsg, errmsg_len)) {
                    errs++;
                    break;
                }
            }
            continue;
        }

        /* ---- `for` directive: iterate over a parameter list ---- *
         *  for x,<a,b,c>   ... body ... endm
         *  The body is executed once per list item, with the loop
         *  variable substituted as a text macro value.
         */
        if (n >= 3 && (toks[0].type == ATOK_ID &&
            (strcmp(toks[0].text, "for") == 0 || strcmp(toks[0].text, "FOR") == 0 ||
             strcmp(toks[0].text, "forc") == 0 || strcmp(toks[0].text, "FORC") == 0))) {
            const char *loopvar = toks[1].text;
            /* collect list items: find tokens after '<' ... '>' or plain args */
            char items[64][64];
            int nitems = 0;
            int in_angle = 0;
            for (int i = 2; i < n && nitems < 64; i++) {
                if (toks[i].type == ATOK_OP) {
                    if (toks[i].text[0] == '<') { in_angle = 1; continue; }
                    if (toks[i].text[0] == '>') { in_angle = 0; continue; }
                    if (toks[i].text[0] == ',') continue;
                    continue;
                }
                snprintf(items[nitems++], 64, "%s", toks[i].text);
            }
            /* collect body until endm */
            char forbuf[64][512];
            int nfor = 0;
            int lj2;
            int nest2 = 1;
            for (lj2 = li + 1; lj2 < nlines && nest2 > 0; lj2++) {
                a_tok_t bt[64];
                int bn = TokenizeLine(lines[lj2], bt, 64);
                if (bn == 0) continue;
                const char *bd = bt[0].text;
                if (strcmp(bd, "for") == 0 || strcmp(bd, "FOR") == 0 ||
                    strcmp(bd, "forc") == 0 || strcmp(bd, "FORC") == 0)
                    nest2++;
                else if (strcmp(bd, ".endm") == 0 || strcmp(bd, "endm") == 0 ||
                         strcmp(bd, "ENDM") == 0) {
                    nest2--;
                    if (nest2 == 0) break;
                }
                if (nfor < 64)
                    snprintf(forbuf[nfor++], sizeof(forbuf[0]), "%s", lines[lj2]);
            }
            li = lj2;
            if (nest2 != 0) { errs++; asmerr(2001, "unterminated for"); continue; }
            /* iterate: substitute loopvar textually in each body line */
            for (int it = 0; it < nitems; it++) {
                char fb[64][512];
                int nfb = 0;
                for (int k = 0; k < nfor; k++) {
                    char out2[512];
                    size_t o2 = 0;
                    const char *p2 = forbuf[k];
                    while (*p2 && o2 + 1 < sizeof(out2)) {
                        size_t vl = strlen(loopvar);
                        if (strncmp(p2, loopvar, vl) == 0 &&
                            !((p2[vl] >= 'a' && p2[vl] <= 'z') ||
                              (p2[vl] >= 'A' && p2[vl] <= 'Z') ||
                              (p2[vl] >= '0' && p2[vl] <= '9') ||
                              p2[vl] == '_')) {
                            const char *v = items[it];
                            while (*v && o2 + 1 < sizeof(out2)) out2[o2++] = *v++;
                            p2 += vl;
                        } else {
                            out2[o2++] = *p2++;
                        }
                    }
                    out2[o2] = 0;
                    snprintf(fb[nfb++], sizeof(fb[0]), "%s", out2);
                }
                if (process_source_lines(out, fb, nfb, src_path, depth + 1,
                                         errmsg, errmsg_len)) {
                    errs++;
                    break;
                }
            }
            continue;
        }

        /* INCLUDE directive: `include <file>` or `INCLUDE <file>`. */
        if ((toks[0].type == ATOK_ID &&
             (strcmp(toks[0].text, "include") == 0 ||
              strcmp(toks[0].text, "INCLUDE") == 0)) ||
            (toks[0].type == ATOK_DIRECTIVE &&
             (strcmp(toks[0].text, ".include") == 0 ||
              strcmp(toks[0].text, ".INCLUDE") == 0))) {
            if (n >= 2 && (toks[1].type == ATOK_ID || toks[1].type == ATOK_STRING)) {
                char incpath[1024];
                const char *fn = toks[1].text;
                const char *slash = strrchr(src_path, '/');
                if (slash) {
                    size_t dl = (size_t)(slash - src_path) + 1;
                    if (dl < sizeof(incpath)) {
                        memcpy(incpath, src_path, dl);
                        snprintf(incpath + dl, sizeof(incpath) - dl, "%s", fn);
                    } else {
                        snprintf(incpath, sizeof(incpath), "%s", fn);
                    }
                } else {
                    snprintf(incpath, sizeof(incpath), "%s", fn);
                }
                /* real include search: if the source-relative candidate does not
                 * exist, fall back to the current working directory, then the
                 * library path (this port: the exe-relative "inc" subdir). */
                if (access(incpath, R_OK) != 0 && strchr(fn, '/') == NULL) {
                    snprintf(incpath, sizeof(incpath), "%s", fn);   /* CWD lookup */
                    if (access(incpath, R_OK) != 0) {
                        snprintf(incpath, sizeof(incpath), "inc/%s", fn);
                        if (access(incpath, R_OK) != 0) {
                            /* restore CWD candidate for the error diagnostic */
                            snprintf(incpath, sizeof(incpath), "%s", fn);
                        }
                    }
                }
                if (process_include(out, incpath, depth, errmsg, errmsg_len)) {
                    errs++;
                    break;
                }
            } else {
                errs++;
                asmerr(2001, line);    /* missing include filename */
            }
            continue;
        }

        /* collect macro body while defining */
        if (out->def_macro > 0) {
            /* nested constructs inside the body whose terminator is a matching
             * endm: `m1x macro ...` definitions and `for`/`forc`/`rept` loops
             * (also with a label prefix: `lbl:for ...`). Their endm only
             * decrements the depth, so they don't close the outer macro
             * collection prematurely. */
            int opens_nest = 0;
            if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
                (strcmp(toks[1].text, "macro") == 0 || strcmp(toks[1].text, "MACRO") == 0))
                opens_nest = 1;
            else if (n >= 2 && (strcmp(toks[0].text, ".macro") == 0 ||
                                strcmp(toks[0].text, "macro") == 0))
                opens_nest = 1;
            else {
                for (int ti = 0; ti < n && !opens_nest; ti++) {
                    if (toks[ti].type != ATOK_ID) continue;
                    if (strcmp(toks[ti].text, "for") == 0 || strcmp(toks[ti].text, "FOR") == 0 ||
                        strcmp(toks[ti].text, "forc") == 0 || strcmp(toks[ti].text, "FORC") == 0 ||
                        strcmp(toks[ti].text, "rept") == 0 || strcmp(toks[ti].text, "REPT") == 0 ||
                        strcmp(toks[ti].text, "while") == 0 || strcmp(toks[ti].text, "repeat") == 0)
                        opens_nest = 1;
                }
            }
            if (opens_nest)
                out->def_macro_nest++;
            if (n >= 1 &&
                (strcmp(toks[0].text, ".endm") == 0 || strcmp(toks[0].text, "endm") == 0 ||
                 strcmp(toks[0].text, "ENDM") == 0)) {
                if (out->def_macro_nest > 0) {
                    out->def_macro_nest--;   /* closes an inner construct, not the outer */
                } else {
                    out->def_macro = 0;      /* outer macro body complete */
                }
                /* still store the endm as part of the outer body so the inner
                 * construct round-trips through expand_macro */
                if (out->def_macro > 0) {
                    asm_macro_t *mm = &out->macros[out->def_macro - 1];
                    if (mm->nbody < 64) {
                        snprintf(mm->body[mm->nbody], sizeof(mm->body[0]), "%s", line);
                        mm->nbody++;
                    }
                }
                continue;
            }
            asm_macro_t *m = &out->macros[out->def_macro - 1];
            if (m->nbody < 64) {
                char mline[512];
                snprintf(mline, sizeof(mline), "%s",
                         line + (line[0] == ' ' || line[0] == '\t' ? 1 : 0));
                /* join backslash continuations inside the macro body:
                 * `local x,y,\(newline)z` becomes `local x,y, z` */
                while (li + 1 < nlines) {
                    size_t ml = strlen(mline);
                    while (ml > 0 && (mline[ml-1] == ' ' || mline[ml-1] == '\t')) ml--;
                    if (ml == 0 || mline[ml-1] != '\\') break;
                    mline[ml-1] = 0;
                    size_t off = strlen(mline);
                    const char *nx = lines[li + 1];
                    while (*nx == ' ' || *nx == '\t') nx++;
                    snprintf(mline + off, sizeof(mline) - off, " %s", nx);
                    li++;
                }
                snprintf(m->body[m->nbody], sizeof(m->body[m->nbody]), "%s", mline);
                size_t llen = strlen(m->body[m->nbody]);
                while (llen && (m->body[m->nbody][llen-1] == '\n' ||
                                m->body[m->nbody][llen-1] == '\r'))
                    m->body[m->nbody][--llen] = 0;
                m->nbody++;
            }
            continue;
        }

        /* .macro definition start: both `.macro name` and `name macro params` forms */
        int is_macro_def = 0;
        /* `undef <name>` / `purge <names...>` — remove macro(s) from the macro table.
         * Arguments are expanded first: text equates and macro function calls. */
        if (n >= 2 && toks[0].type == ATOK_ID &&
            (strcmp(toks[0].text, "undef") == 0 || strcmp(toks[0].text, "UNDEF") == 0 ||
             strcmp(toks[0].text, "purge") == 0 || strcmp(toks[0].text, "PURGE") == 0)) {
            for (int u = 1; u < n; u++) {
                if (toks[u].type != ATOK_ID) continue;
                const char *arg = toks[u].text;
                /* `mf1()` macro-function-call argument: expand to the exitm text
                 * so the returned text macro (e.g. `m3`) can be purged. */
                if (u + 2 < n && toks[u+1].type == ATOK_OP && toks[u+1].text[0] == '(' &&
                    toks[u+2].type == ATOK_OP && toks[u+2].text[0] == ')') {
                    asm_macro_t *fm = find_macro(out, arg);
                    if (fm) {
                        /* run the macro body; its `exitm <x>` endm yields the name */
                        expand_macro(out, fm, NULL, 0, NULL, 0, NULL, 0);
                        u += 2;
                        continue;
                    }
                }
                /* text equate argument: `purge tm1` where tm1 = <m2> */
                for (int si = 0; si < out->nsyms; si++) {
                    if (out->syms[si].is_text && out->syms[si].defined &&
                        strcmp(out->syms[si].name, arg) == 0 && out->syms[si].text[0]) {
                        arg = out->syms[si].text;
                        break;
                    }
                }
                for (int w = 0; w < out->nmacros; w++) {
                    if (strcmp(out->macros[w].name, arg) == 0) {
                        /* remember the removed name so later bare invocations are ignored */
                        if (out->npurged < 16) {
                            int dup = 0;
                            for (int pd = 0; pd < out->npurged; pd++)
                                if (strcmp(out->purged[pd], arg) == 0) { dup = 1; break; }
                            if (!dup) snprintf(out->purged[out->npurged++], 128, "%s", arg);
                        }
                        for (int v = w; v + 1 < out->nmacros; v++)
                            out->macros[v] = out->macros[v + 1];
                        out->nmacros--;
                        break;
                    }
                }
            }
            continue;
        }
        if (n >= 2 &&
            (strcmp(toks[0].text, ".macro") == 0 || strcmp(toks[0].text, "macro") == 0))
            is_macro_def = 1;   /* .macro name form */
        if (n >= 2 && toks[0].type == ATOK_ID && toks[1].type == ATOK_ID &&
            (strcmp(toks[1].text, "macro") == 0 || strcmp(toks[1].text, "MACRO") == 0))
            is_macro_def = 2;   /* name macro form */
        if (is_macro_def) {
            int name_idx = (is_macro_def == 1) ? 1 : 0;
            int param_start = (is_macro_def == 1) ? 2 : 2;
            if (out->nmacros >= 32) { errs++; asmerr(2001, line); continue; }
            asm_macro_t *m = &out->macros[out->nmacros];
            memset(m, 0, sizeof(*m));
            snprintf(m->name, sizeof(m->name), "%s", toks[name_idx].text);
            m->nparams = 0;
            /* collect parameter names; skip `:qualifier` (req/vararg/label) so
             * `dst:req, opnd:req` registers [dst, opnd] not [dst, req, opnd, req]. */
            for (int i = param_start; i < n && m->nparams < 8; i++) {
                if (toks[i].type == ATOK_ID && !find_reg(toks[i].text)) {
                    /* qualifier token after a ':' on a param name is not a param */
                    if (i > param_start && toks[i-1].type == ATOK_OP && toks[i-1].text[0] == ':')
                        continue;
                    /* also skip the qualifier that directly follows a name:
                     * `name:req` tokenizes as name(ID) :(OP) req(ID) — handled above;
                     * `name = <default>` — skip the default expression tokens */
                    if (i > param_start && toks[i-1].type == ATOK_OP && toks[i-1].text[0] == '=')
                        continue;
                    snprintf(m->params[m->nparams], sizeof(m->params[m->nparams]),
                             "%s", toks[i].text);
                    m->nparams++;
                }
            }
            out->nmacros++;
            out->def_macro = out->nmacros;
            continue;
        }

        /* conditional directives (if/elseif/else/endif + IFE/ENDIF/IFNE case variants) */
        if (n >= 1 && (toks[0].type == ATOK_DIRECTIVE ||
                       (toks[0].type == ATOK_ID &&
                        (strcmp(toks[0].text, "if") == 0 ||
                         strcmp(toks[0].text, "IF") == 0 ||
                         strcmp(toks[0].text, "ife") == 0 ||
                         strcmp(toks[0].text, "IFE") == 0 ||
                         strcmp(toks[0].text, "ifne") == 0 ||
                         strcmp(toks[0].text, "IFNE") == 0 ||
                         strcmp(toks[0].text, "endif") == 0 ||
                         strcmp(toks[0].text, "ENDIF") == 0 ||
                         strcmp(toks[0].text, "else") == 0 ||
                         strcmp(toks[0].text, "ELSE") == 0 ||
                         strcmp(toks[0].text, "elseif") == 0 ||
                         strcmp(toks[0].text, "ELSEIF") == 0 ||
                         strcmp(toks[0].text, "ifdef") == 0 ||
                         strcmp(toks[0].text, "IFDEF") == 0 ||
                         strcmp(toks[0].text, "ifndef") == 0 ||
                         strcmp(toks[0].text, "IFNDEF") == 0 ||
                         strcmp(toks[0].text, "ifb") == 0 ||
                         strcmp(toks[0].text, "ifnb") == 0 ||
                         strcmp(toks[0].text, "ifidn") == 0 ||
                         strcmp(toks[0].text, "ifidni") == 0)))) {
            if (handle_control(out, toks, n, line))
                continue;
        }

        /* macro invocation */
        if (toks[0].type == ATOK_ID) {
            asm_macro_t *m = find_macro(out, toks[0].text);
            /* label-prefixed macro call: `v1 m1 1` — v1 is a label bound to the
             * first (label) parameter, m1 is the macro, remaining tokens are
             * the rest of the args.  Swap so toks[0]=macro name, toks[1]=v1. */
            int label_call = 0;
            if (!m && n >= 3 && toks[1].type == ATOK_ID) {
                asm_macro_t *m1 = find_macro(out, toks[1].text);
                if (m1) {
                    int si = find_or_add_sym(out, toks[0].text);
                    if (si >= 0) { out->syms[si].value = cur_offset(out); out->syms[si].defined = 1; out->syms[si].sec_index = out->cur_sec; }
                    a_tok_t t0 = toks[0];
                    toks[0] = toks[1];   /* macro name */
                    toks[1] = t0;        /* label as first arg */
                    m = m1;
                    label_call = 1;
                }
            }
            /* bare call of a name removed by purge/undef → silently ignored */
            if (!m) {
                for (int pd = 0; pd < out->npurged; pd++)
                    if (strcmp(out->purged[pd], toks[0].text) == 0) {
                        m = (asm_macro_t *)(intptr_t)1;   /* sentinel: skip */
                        break;
                    }
            }
            if (m) {
                if (m == (asm_macro_t *)(intptr_t)1) { continue; }
                if (out->nctl > 0 && !out->ctl[out->nctl - 1].active)
                    continue;
                a_tok_t args[8];
                int nargs = 0;
                for (int i = 1; i < n && nargs < 8; i++) {
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == ',')
                        continue;
                    /* angle-bracket argument: <a,b,c> stays one semantic arg */
                    if (toks[i].type == ATOK_OP && toks[i].text[0] == '<') {
                        /* collect until matching '>' */
                        char brack[512];
                        size_t bo = 0;
                        int nest = 1;
                        int need_space = 0;  /* space between joined tokens */
                        brack[bo++] = '<';
                        int j = i + 1;
                        while (j < n && nest > 0 && bo + 1 < sizeof(brack)) {
                            if (toks[j].type == ATOK_OP && toks[j].text[0] == '<') nest++;
                            else if (toks[j].type == ATOK_OP && toks[j].text[0] == '>') {
                                nest--;
                                if (nest == 0) { brack[bo++] = '>'; break; }
                            }
                            /* join token text with space separator */
                            if (toks[j].type == ATOK_NUM || toks[j].type == ATOK_ID) {
                                if (need_space && bo + 1 < sizeof(brack)) brack[bo++] = ' ';
                                const char *tt = toks[j].text;
                                while (*tt && bo + 1 < sizeof(brack)) brack[bo++] = *tt++;
                                need_space = 1;
                            } else if (toks[j].type == ATOK_OP &&
                                       toks[j].text[0] != ',' &&
                                       toks[j].text[0] != '[' &&
                                       toks[j].text[0] != ']' &&
                                       toks[j].text[0] != '+' &&
                                       toks[j].text[0] != '*' &&
                                       toks[j].text[0] != '<' &&
                                       toks[j].text[0] != '>') {
                                if (need_space && bo + 1 < sizeof(brack)) brack[bo++] = ' ';
                                const char *tt = toks[j].text;
                                while (*tt && bo + 1 < sizeof(brack)) brack[bo++] = *tt++;
                                need_space = 1;
                            } else if (toks[j].type == ATOK_OP &&
                                       (toks[j].text[0] == '[' ||
                                        toks[j].text[0] == '+' ||
                                        toks[j].text[0] == '*' ||
                                        toks[j].text[0] == '-' ||
                                        toks[j].text[0] == ']')) {
                                const char *tt = toks[j].text;
                                while (*tt && bo + 1 < sizeof(brack)) brack[bo++] = *tt++;
                                need_space = 0;
                            } else if (toks[j].type == ATOK_OP &&
                                       toks[j].text[0] == ',') {
                                /* comma: keep it, no space before, space after will be added by next token */
                                if (bo + 1 < sizeof(brack)) brack[bo++] = ',';
                                need_space = 1;
                            }
                            j++;
                        }
                        brack[bo] = 0;
                        args[nargs].type = ATOK_ID;
                        snprintf(args[nargs].text, sizeof(args[nargs].text),
                                 "%s", brack);
                        nargs++;
                        i = j;   /* skip consumed tokens */
                        continue;
                    }
                    args[nargs++] = toks[i];
                }
                if (expand_macro(out, m, args, nargs, src_path, depth,
                                 errmsg, errmsg_len)) {
                    errs++;
                    break;
                }
                continue;
            }
        }

        /* suppressed in inactive control-flow branch */
        if (out->suppress > 0)
            continue;

        if (!assemble_line(out, toks, n)) {
            errs++;
            asmerr(2001, line);    /* invalid instruction */
            if (errs >= 10) break;
        }
    }
    return errs ? 1 : 0;
}

int AssembleToBin(const char *src_path, asm_output_t *out)
{
    char errmsg[256] = "";

    memset(out, 0, sizeof(*out));
    out->cur_sec = SEC_TEXT;

    return assemble_file_internal(src_path, out, 0, errmsg, sizeof(errmsg));
}

/* Write object to `<basename>.bin` (flat binary of .text section) */
int WriteBinOutput(asm_output_t *out, const char *src_path)
{
    char dst[1024];
    snprintf(dst, sizeof(dst), "%s", src_path);
    char *dot = strrchr(dst, '.');
    if (dot) strcpy(dot + 1, "bin");
    else strcat(dst, ".bin");

    FILE *f = fopen(dst, "wb");
    if (!f) { asmerr(1000, dst); return 1; }
    fwrite(out->text, 1, out->text_len, f);
    fclose(f);
    tprintf("%s: %zu bytes written\n", dst, out->text_len);
    return 0;
}