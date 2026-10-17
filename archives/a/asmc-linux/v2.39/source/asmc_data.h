/* AArch64 native port: Asmc data model (Options, MODULE)
 * Port of asmc.inc: global_options, module_info structs
 * Target: aarch64-unknown-linux-ohos
 */

#ifndef ASMC_DATA_H
#define ASMC_DATA_H

#include <stdint.h>
#include <stddef.h>

/* Basic types (matching asmc.inc) */
typedef char *string_t;
typedef char **array_t;
typedef int int_t;
typedef unsigned int uint_t;
typedef void *asym_t;       /* symbol pointer */
typedef void *token_t;      /* token pointer */
typedef void *LPFILE;       /* FILE pointer */
typedef void *qdesc_t;      /* queue descriptor */
typedef void *ptr_t;        /* generic pointer */

/* File type indices */
#define TASM 0
#define TERR 1
#define TOBJ 2
#define TLST 3
#define NUM_FILE_TYPES 4

/* Option name types */
#define OPTN_LAST 4  /* number of name slots */

/* Output format constants */
#define OFORMAT_OMF  0
#define OFORMAT_BIN  1
#define OFORMAT_COFF 2
#define OFORMAT_ELF  3
#define OFORMAT_MZ   4
#define OFORMAT_PE   5

/* global_options struct (port of asmc.inc:global_options) */
typedef struct global_options {
    /* flags union */
    unsigned int flags;          /* bitfield */
    unsigned int quiet : 1;      /* -q */
    unsigned int line_numbers : 1;
    unsigned int warning_error : 1;
    unsigned int no_error_disp : 1;
    unsigned int process_subdir : 1;
    unsigned int no_comment_in_code_rec : 1;
    unsigned int no_opt_farcall : 1;
    unsigned int no_file_entry : 1;
    unsigned int no_static_procs : 1;
    unsigned int no_section_aux_entry : 1;
    unsigned int no_cdecl_decoration : 1;
    unsigned int no_export_decoration : 1;
    unsigned int entry_decorated : 1;
    unsigned int preprocessor_stdout : 1;
    unsigned int masm51_compat : 1;
    unsigned int masm8_proc_visibility : 1;
    unsigned int no_symbol_listing : 1;
    unsigned int first_pass_listing : 1;
    unsigned int all_symbols_public : 1;
    unsigned int safeseh : 1;
    unsigned int strict_masm_compat : 1;
    unsigned int ignore_include : 1;
    unsigned int syntax_check_only : 1;
    unsigned int pe_dll : 1;
    unsigned int chkstack : 1;
    unsigned int nolib : 1;
    unsigned int no_linking : 1;
    unsigned int link_mt : 1;
    unsigned int float_used : 1;
    unsigned int main_found : 1;
    unsigned int argv_used : 1;
    /* end flags */
    unsigned int floating_point;
    unsigned int error_limit;
    string_t names[OPTN_LAST];   /* -Fo, -Fe, etc. */
    ptr_t queues[4];             /* option queues */
    string_t link_exename;
    string_t link_linker;
    string_t link_options;
    string_t link_objects;
    unsigned int list_macro;
    unsigned int output_format;
    unsigned int sub_format;
    unsigned int langtype;
    unsigned int _model;
    unsigned int fctype;
    unsigned int codepage;
    unsigned int floatdigits;
    /* cpu: CPU struct - simplified */
    unsigned int cpu;
    unsigned char frame_auto;
    unsigned char debug_symbols;
    unsigned char debug_ext;
    unsigned char warning_level;
    unsigned char link;
    unsigned char stdcall_decoration;
    unsigned char floatformat;
    unsigned char flt_size;
    unsigned char fieldalign;
    unsigned char loopalign;
    unsigned char casealign;
    unsigned char segmentalign;
    unsigned char pe_subsystem;
    unsigned char win64_flags;
    unsigned char arch;
    unsigned char iddc;
} global_options;

/* module_info struct (port of asmc.inc:module_info) */
typedef struct module_info {
    unsigned int flags;          /* bitfield */
    /* abbreviated: only critical fields for ParseCmdline */
    unsigned char Ofssize;
    unsigned char defOfssize;
    unsigned char wordsize;
    unsigned char fctype;
    unsigned char radix;
    unsigned char langtype;
    unsigned char fieldalign;
    unsigned char sub_format;
    unsigned int cpu;
    unsigned int srcfile;
    /* curr_cpu: CPU */
    unsigned char _model;
    unsigned char line_flags;
    unsigned char offsettype;
    unsigned char inside_comment;
    unsigned char segorder;
    unsigned char distance;
    unsigned char procalign;
    unsigned char ostype;
    /* PADDING to align fields */
    unsigned char pad[3];
    /* Files */
    LPFILE curr_file[NUM_FILE_TYPES];
    string_t curr_fname[NUM_FILE_TYPES];
    string_t *FNames;
    unsigned int cnt_fnames;
    unsigned int error_count;
    unsigned int warning_count;
    /* Key fields for ParseCmdline */
    unsigned int EndDirFound : 1;
    /* ... more fields follow in original; only critical ones above */
} module_info;

/* Global instances */
extern global_options Options;
extern module_info ModuleInfo;
extern uint_t Parse_Pass;
extern string_t *my_environ;

/* Object buffer for x86/x86-64 target emission (asmc_asm.c) */
typedef struct asmc_object {
    uint8_t buf[65536];
    size_t  len;
    int     use64;
    int     errors;
} object_t;

/* Symbol (label) table entry for ELF output */
typedef struct {
    char     name[128];
    uint64_t value;      /* section offset */
    int      defined;    /* 1 if resolved in this module */
    int      global;     /* 1 = STB_GLOBAL, 0 = STB_LOCAL */
    int      sec_index;  /* section index (1 = .text, 2 = .data, 3 = .bss) */
    int      struct_id;  /* if >0, this symbol is a struct member with this struct id */
    int      struct_off; /* byte offset within struct */
    char     text[512];  /* text-equate value (TEXTEQU); empty if numeric */
    int      is_text;    /* 1 = text equate (symbol value lives in text[]), 0 = numeric */
} asmc_sym_t;

/* Relocation/fixup entry (forward or external reference) */
typedef struct {
    uint64_t offset;     /* offset into section */
    int      sym_index;  /* index into symbols */
    int      type;       /* ELF relocation type (R_X86_64_*) */
    int      addend;
    int      sec;        /* section the relocation applies to (1=.text, 2=.data) */
} asmc_fixup_t;

/* Assembler output state shared between assembler and ELF writer.
 * Multi-section: .text (code), .data (initialized), .bss (uninitialized).
 */

/* macro definition (.macro name p1,p2,... / .endm) */
typedef struct {
    char     name[128];
    char     params[8][128];   /* parameter names */
    int      nparams;
    char     body[64][512];    /* macro body lines (placeholder form) */
    int      nbody;
    int      active;           /* being defined */
} asm_macro_t;

/* conditional/loop nesting frame */
typedef struct {
    int      kind;      /* 1=.if, 2=.repeat, 3=.while, 4=.macro */
    int      active;    /* current branch is being assembled */
    int      ever_active; /* at least one branch was active */
    int      taken;     /* a branch was taken */
    int64_t  repeat_end; /* repeat/while exit marker offset (unused sentinel) */
    int      cond;      /* condition state */
} asm_ctl_t;

typedef struct {
    /* .text -- code bytes (used by .bin output too) */
    uint8_t text[65536];
    size_t  text_len;
    /* .data -- initialized data bytes */
    uint8_t data[65536];
    size_t  data_len;
    /* .bss -- uninitialized storage size only */
    size_t  bss_len;
    /* current section during assembly: 1=.text, 2=.data, 3=.bss */
    int     cur_sec;
    asmc_sym_t   syms[256];
    int          nsyms;
    asmc_fixup_t fixups[256];
    int          nfixups;
    int          errors;
    /* macro table */
    asm_macro_t  macros[32];
    int          nmacros;
    /* names removed by `purge`/`undef` — later bare invocations are ignored */
    char         purged[16][128];
    int          npurged;
    /* text returned by the most recent macro-function call (exitm <text> /
     * retm<text>) — used for `mov eax, MF1()` value adaptation. */
    char         macro_ret[512];
    /* include stack: resolved paths currently being processed (cycle/recursion
     * diagnostics; max 8 levels, matching the nesting depth limit). */
    char         inc_stack[8][1024];
    int          ninc_stack;
    /* control-flow nesting stack (if/repeat/while/macro) */
    asm_ctl_t    ctl[32];
    int          nctl;
    /* if control flow is suppressed (in inactive branch or macro def) */
    int          suppress;
    /* currently defined macro body being collected (index+1 or 0) */
    int          def_macro;
    /* nesting depth of macro definitions while collecting a body (0 = top) */
    int          def_macro_nest;
    /* unique macro-local label counter (each invocation increments) */
    int          macrolbl;
    /* per-invocation unique suffix used by @@ label substitution */
    int          invoc_id;
    /* current macro invocation nesting for origin diagnostics */
    int          macro_depth;
    /* literal pool: floating-point constants */
    uint64_t     litpool[64];   /* IEEE 754 double values */
    int          litpool_n;     /* number of entries */
    int          litpool_data_offsets[64]; /* offset into .data section */
    /* struct/class layout tracking */
    int          cur_struct_id; /* current struct being defined (0=none) */
    int          cur_struct_off; /* current byte offset within struct */
    int          struct_sizes[32]; /* total size of each struct id */
    int          struct_parents[32]; /* parent struct id for inheritance (0 = no parent) */
    int          struct_is_union[32]; /* 1 if struct id is a union (members overlap at offset 0) */
    int          struct_stack_id[32]; /* nesting stack: struct id of open frame */
    int          struct_stack_off[32]; /* nesting stack: cur_struct_off on entry */
    int          struct_stack_kind[32]; /* nesting stack: 0=struct, 1=union */
    int          n_struct_stack;   /* nesting depth */
    int          in_enum;       /* 1 = inside a .enum member list */
    int          anon_lbl;      /* current anonymous label offset (for @@:/@B/@F) */
    /* local variable frame tracking (per procedure) */
    char         locals[64][128];  /* local variable names */
    int          local_sizes[64];  /* local variable sizes (bytes) */
    int          local_offs[64];   /* local variable stack offsets */
    int          local_sym_ids[64];/* symbol-table index of each local (for scope invalidation) */
    int          nlocals;          /* number of locals in current proc */
    int          frame_size;       /* total current procedure frame size */
    int          cur_proc;         /* 1 = inside a procedure body */
} asm_output_t;

/* section index constants */
#define SEC_TEXT 1
#define SEC_DATA 2
#define SEC_BSS  3

/* asmc_asm.c interfaces */
int AssembleToBin(const char *src_path, asm_output_t *out);
int WriteBinOutput(asm_output_t *out, const char *src_path);

/* asmc_elf.c interfaces */
int WriteElfOutput(asm_output_t *out, const char *src_path);

/* asmc_globals.c interfaces */
extern void init_options(void);

#endif /* ASMC_DATA_H */