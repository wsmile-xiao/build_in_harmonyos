/* test_cases.h — 上游 dasm 回归用例真值表（随源码提交，不参与构建逻辑）
 *
 * 用例与期望字节全部取自上游 test/ 目录，判据与上游 test/run_tests.sh
 * 的非 strict 段完全一致：
 *
 *     dasm NAME.asm -f1 -oNAME.bin -LNAME.list.txt -DINEEPROM
 *     cmp NAME.bin NAME.bin.ref
 *
 * .bin.ref 的字节布局 = 2 字节小端 origin 头 + 机器码（-f1 原始格式）。
 *
 * 注意：部分用例（如 doublemacro / toobigword）在上游同时登记了 .fail，
 * 用于 run_tests.sh 的 strict(-S) 段；本测试只走非 strict 段，期望值即
 * 各自 .bin.ref。
 */
#ifndef TEST_DASM_CASES_H
#define TEST_DASM_CASES_H

typedef struct {
    const char *name;      /* 用例名 */
    const char *asm_src;   /* .asm 源文本（末尾带换行） */
    const unsigned char *expect;
    unsigned int expect_len;
    unsigned int origin;   /* 期望 origin（.bin.ref 前 2 字节小端） */
} dasm_case_t;

/* ---- 6502_16h.asm （上游 test/6502_16h.asm 原样内嵌） ---- */
static const char CASE_6502_16h_ASM[] =
    "\t.PROCESSOR\t6502\n"
    "\t.TRACE\ton\n"
    "\n"
    "\t.ORG 0\n"
    "\n"
    "\tand.b\t>400\t; forced byte addressing and taking higher part should be OK\n"
    "\tand.w\t>400\n"
    "\n"
    "\tldy.b\t>400,X\n"
    "\tldy.w\t>400,X\n"
    "\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_6502_16h_EXPECT[10] = {
    0x25, 0x01, 0x2D, 0x01, 0x00, 0xB4, 0x01, 0xBC, 0x01, 0x00,
};

/* ---- 6502_16l.asm （上游 test/6502_16l.asm 原样内嵌） ---- */
static const char CASE_6502_16l_ASM[] =
    "\t.PROCESSOR\t6502\n"
    "\t.TRACE\ton\n"
    "\n"
    "\t.ORG 0\n"
    "\n"
    "\tand.b\t<400\t; forced byte addressing and taking lower part should be OK\n"
    "\tand.w\t<400\n"
    "\n"
    "\tldy.b\t<400,X\n"
    "\tldy.w\t<400,X\n"
    "\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_6502_16l_EXPECT[10] = {
    0x25, 0x90, 0x2D, 0x90, 0x00, 0xB4, 0x90, 0xBC, 0x90, 0x00,
};

/* ---- stawx.asm （上游 test/stawx.asm 原样内嵌） ---- */
static const char CASE_stawx_ASM[] =
    "\n"
    "\t.TRACE\ton\n"
    "\n"
    "\t.processor \t6502\n"
    "\n"
    "\t\n"
    "RESP0 = $10\n"
    "RESP1 = $100\n"
    "\t\n"
    "\t.ORG \t0\n"
    "\n"
    "\tsta.wx  RESP0,x\n"
    "\tsta.w\tRESP0,x\n"
    "\tsta \tRESP1,x\n"
    "\n"
    "\tlda\t(1),Y\n"
    "\tlda\t(RESP0),Y\n"
    "\t\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_stawx_EXPECT[13] = {
    0x9D, 0x10, 0x00, 0x9D, 0x10, 0x00, 0x9D, 0x00, 0x01, 0xB1, 0x01, 0xB1,
    0x10,
};

/* ---- jmpiw.asm （上游 test/jmpiw.asm 原样内嵌） ---- */
static const char CASE_jmpiw_ASM[] =
    "\n"
    "\t.TRACE\ton\n"
    "\n"
    "\t.processor \t6502\n"
    "\n"
    "\t.ORG \t0\n"
    "RESP0 = $10\t\t; (curious) why is (only) listing output big endian ordered when processor is little ?\n"
    "\tDC.w\tRESP0\n"
    "\n"
    "RESP1 = $100\t\t;       ... but that's a different construction site\n"
    "\tDC.w\tRESP1\n"
    "\n"
    "\n"
    "\tjmp\tRESP0\n"
    "\tjmp\tRESP1\n"
    "\tjmp\t(RESP1)\t\t\n"
    "\n"
    "\tjmp.in\t(RESP0)\t\t; forced(indirect_word)  and coded(indirect_word)\n"
    "\tjmp.in\tRESP0\t\t; forced(indirect_word)  and coded(byteaddr)\t\t; should this be an error with strict mode ?\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_jmpiw_EXPECT[19] = {
    0x10, 0x00, 0x00, 0x01, 0x4C, 0x10, 0x00, 0x4C, 0x00, 0x01, 0x6C, 0x00,
    0x01, 0x6C, 0x10, 0x00, 0x6C, 0x10, 0x00,
};

/* ---- forced_addrmode.asm （上游 test/forced_addrmode.asm 原样内嵌） ---- */
static const char CASE_forced_addrmode_ASM[] =
    "\n"
    "\t\t.PROCESSOR\t6803\n"
    "\n"
    "\n"
    "FAR_ADDR\t.EQU\t\t$F01A\n"
    "DIRECT_ADDR\t.EQU\t\t$40\n"
    "\n"
    "\t.ORG\t\t0\n"
    "\n"
    "\tjsr.b\t\tDIRECT_ADDR\n"
    "\tjsr.w\t\tFAR_ADDR\n"
    "\t\n"
    "\tjsr\t\tDIRECT_ADDR\n"
    "\tjsr\t\tFAR_ADDR\n"
    "\n"
    "\tjsr.w\t\tDIRECT_ADDR\n"
    "\t\n"
    "\tjsr.b\t\t>FAR_ADDR\n"
    "\tjsr.b\t\t<FAR_ADDR\n"
    "\n"
    "\tjsr.w\t\t>FAR_ADDR\n"
    "\tjsr.w\t\t<FAR_ADDR\n"
    "\n"
    "\n"
    "\n"
    "\t\n"
    "\n"
    ;

static const unsigned char CASE_forced_addrmode_EXPECT[23] = {
    0x9D, 0x40, 0xBD, 0xF0, 0x1A, 0x9D, 0x40, 0xBD, 0xF0, 0x1A, 0xBD, 0x00,
    0x40, 0x9D, 0xF0, 0x9D, 0x1A, 0xBD, 0x00, 0xF0, 0xBD, 0x00, 0x1A,
};

/* ---- addressexpression.asm （上游 test/addressexpression.asm 原样内嵌） ---- */
static const char CASE_addressexpression_ASM[] =
    "; addressexpression - adapted from the \"jentzsch3\" address expression bug test.\n"
    "; Original test courtesy Thomas Jentzsch. Output result code generation \n"
    "; added by Mike Saarna.\n"
    "\n"
    "\tprocessor 6502\n"
    "\tORG $100\n"
    "\n"
    "TEST_1 = (.) \n"
    "TEST_2 = (*)\n"
    "TEST_3 = (1 - .)\n"
    "TEST_4 = (1 - *)\n"
    "TEST_5 = (1 - . - 1)\n"
    "TEST_6 = (1 - * - 1)\n"
    "TEST_7 = (1 - 1 - .)\n"
    "TEST_8 = (1 - 1 - *)\n"
    "TEST_9 = (1 + *)\n"
    "TEST_10 = (1 + * + 1)\n"
    "TEST_11 = (1 + 1 + *)\n"
    "\n"
    " if TEST_1 =  256\n"
    "\t.byte $01\n"
    " endif\n"
    " if TEST_2 = 256\n"
    "\t.byte $02\n"
    " endif\n"
    " if TEST_3 = -255\n"
    "\t.byte $03\n"
    " endif\n"
    " if TEST_4 = -255\n"
    "\t.byte $04\n"
    " endif\n"
    " if TEST_5 = -256\n"
    "\t.byte $05\n"
    " endif\n"
    " if TEST_6 = -256\n"
    "\t.byte $06\n"
    " endif\n"
    " if TEST_7 = -256\n"
    "\t.byte $07\n"
    " endif\n"
    " if TEST_8 = -256\n"
    "\t.byte $08\n"
    " endif\n"
    " if TEST_9 = 257\n"
    "\t.byte $09\n"
    " endif\n"
    " if TEST_10 = 258\n"
    "\t.byte $0A\n"
    " endif\n"
    " if TEST_11 = 258\n"
    "\t.byte $0B\n"
    " endif\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_addressexpression_EXPECT[11] = {
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B,
};

/* ---- multiline_comment.asm （上游 test/multiline_comment.asm 原样内嵌） ---- */
static const char CASE_multiline_comment_ASM[] =
    " processor 6502\n"
    " ORG $1000\n"
    "\n"
    " /* comment 1 */ lda #0\n"
    "\n"
    " /* IF 0\n"
    "*/\n"
    "\n"
    "  lda #1/*test*/\n"
    " /*\n"
    "\n"
    "*/  lda #2\n"
    "\n"
    "/*\n"
    "hello */label lda #3\n"
    "\n"
    "/*foo*/ lda #4/*bar*/\n"
    "\n"
    "/* more \n"
    "   comments\n"
    "     */mylabel lda #5 /* too many comments*/ /*but we can deal with it*/\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_multiline_comment_EXPECT[12] = {
    0xA9, 0x00, 0xA9, 0x01, 0xA9, 0x02, 0xA9, 0x03, 0xA9, 0x04, 0xA9, 0x05,
};

/* ---- same_names.asm （上游 test/same_names.asm 原样内嵌） ---- */
static const char CASE_same_names_ASM[] =
    "\n"
    "\t.TRACE on\n"
    "\n"
    "\t.PROCESSOR 68908\n"
    "\n"
    "\t.MAC\tldx\t\t; we cant overwrite any of the processor ops\n"
    "\t\tlda\t{1}\n"
    "\t.ENDM\n"
    "\n"
    "\t.MAC\tLDHX\t\t; also not with different case\n"
    "\t\tldx\t<{1}\n"
    "\t\tlda\t>{1}\n"
    "\t\tpsha\n"
    "\t\tpulh\n"
    "\t.ENDM\n"
    "\n"
    "\t.MAC M1_postfix7\n"
    "\t\tldhx\t#1\n"
    "\t.ENDM\n"
    "\n"
    "\t.MAC M2_postfix7\n"
    "\t\tldx \t#1\n"
    "\t\tclrh\n"
    "\t.ENDM\n"
    "\n"
    "M1_postfix7\t\t.EQU\t0xA1\t\t; symbols can share the same name with macros or processor ops\n"
    "M2_postfix7\t\t.EQU\t0xB2\n"
    "LDA\t\t\t.EQU\t0xDA\n"
    "\n"
    "\t.MAC M3_postfix7\n"
    "\t\tpshh\n"
    "\t\tpulx\n"
    "\t.ENDM\n"
    "\n"
    "\n"
    "\t.ORG 0\n"
    "\n"
    "; call to macro1\n"
    "\tM1_postfix7\n"
    "\n"
    "; call to macro2\n"
    "\tM2_postfix7\n"
    "\n"
    "\tDC.b\tM1_postfix7\t\n"
    "\tDC.b\tM2_postfix7\t\n"
    "\tDC.b\tLDA\n"
    "\n"
    "\tlda\t#0x0a\n"
    "\tLDA\t#0x0b\n"
    "\n"
    "; call to macro3\n"
    "\tM3_postfix7\n"
    "\n"
    "\tldx\t#1\n"
    "\tldhx\t#2\n"
    "\tLDHX\t#3\n"
    "\n"
    "\t.END\t\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_same_names_EXPECT[23] = {
    0x45, 0x00, 0x01, 0xAE, 0x01, 0x8C, 0xA1, 0xB2, 0xDA, 0xA6, 0x0A, 0xA6,
    0x0B, 0x8B, 0x88, 0xAE, 0x01, 0x45, 0x00, 0x02, 0x45, 0x00, 0x03,
};

/* ---- declare_var_mac.asm （上游 test/declare_var_mac.asm 原样内嵌） ---- */
static const char CASE_declare_var_mac_ASM[] =
    ";\n"
    "; the purpose of this macro is to declare a global variable without need to know its exact location\n"
    "; the location is automatically derived from its predecessor 'next_var' which gets redefined at every \n"
    "; occurence. This way one can copy-paste, comment-out or conditional-define variable declarations\n"
    "; without worrying. Memory usage will be always as compact as possible\n"
    ";\n"
    "\t.PROCESSOR\t6803\n"
    "\n"
    "\t#ifnconst\tRAM_START\n"
    "RAM_START\t.EQU\t\t0x80\n"
    "\t#endif\n"
    "\n"
    "        .mac declare_var ; {name},{size}\n"
    "{1}             .EQU            next_var\n"
    "next_var        .set            ({1}+{2})\n"
    "        .endm\n"
    "\n"
    "next_var\t.set\t\tRAM_START\n"
    "\n"
    "\tdeclare_var\tfirst, 1\t\t; declare variable name \"first\" 8bit \n"
    "\tdeclare_var\tsecond, 2\t\t; declare variable name \"second\" 16bit\n"
    "    #if (RAM_START == 0x60)\n"
    "\tdeclare_var\textra, 3\t\t; in case of special define, include variable extra 24bit\n"
    "    #endif\n"
    "\tdeclare_var\tthird, 4\t\t; declare variable name \"third\" 32bit\n"
    "\n"
    "\t.ORG\t\t0x8000\n"
    "\n"
    "example_code:\n"
    "\tldx\t#third\n"
    "\ttxs\n"
    "\tldaa\tfirst\n"
    "\tstaa\t,X\n"
    "    #if (RAM_START == 0x60)\n"
    "\tstaa.w\textra\n"
    "    #endif\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_declare_var_mac_EXPECT[8] = {
    0xCE, 0x00, 0x83, 0x35, 0x96, 0x80, 0xA7, 0x00,
};

/* ---- recursive_macro0.asm （上游 test/recursive_macro0.asm 原样内嵌） ---- */
static const char CASE_recursive_macro0_ASM[] =
    "\n"
    "\t.PROCESSOR\t6502\n"
    "\t\n"
    "\t.MAC rec_test\n"
    "\t\t.IF ({1} > 0)\n"
    "\t\t\trec_test [{1}-1]\n"
    "\t\t.ELSE\n"
    "\t\t\tlda\t#{1}\n"
    "\t\t.ENDIF\t\t\n"
    "\t.ENDM\n"
    "\n"
    "\t.ORG\t0\n"
    "\t\n"
    "\trec_test 5\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_recursive_macro0_EXPECT[2] = {
    0xA9, 0x00,
};

/* ---- toobigword.asm （上游 test/toobigword.asm 原样内嵌） ---- */
static const char CASE_toobigword_ASM[] =
    "; Test case for strict mode check for word data size\n"
    "\n"
    "\tprocessor 6502\n"
    "\n"
    "\tORG $f800\n"
    "\n"
    "\t.word $10000\n"
    "\n"
    "\n"
    ;

static const unsigned char CASE_toobigword_EXPECT[2] = {
    0x00, 0x00,
};

/* ---- string_conversion.asm （上游 test/string_conversion.asm 原样内嵌） ---- */
static const char CASE_string_conversion_ASM[] =
    "; Bug in string conversion.\n"
    "; Reported 2007/08/25 by Eduardo Casino Almao <casino_e@movistar.es>\n"
    "\n"
    "; I've found a bug in the string conversion feature ([exp]d) I'm using\n"
    "; version 2.20.10b\n"
    ";\n"
    "; Basically, if exp is a not-yet-resolved label, the assembler aborts with\n"
    "; \"program.a: (XX): error Label mismatch...\n"
    "\n"
    "\tprocessor 6502\n"
    "\n"
    "\torg\t$0801\n"
    "\n"
    "\tword\tendprg\t\t\t; pointer to next line\n"
    "\tword\t1968\t\t\t; line number\n"
    "\tbyte\t$9e\t\t\t; SYS token\n"
    "\tbyte\t[start]d\t\t; ASCII of SYS address\n"
    "\tbyte\t\" TESTPROG BY TESTSOFT\"\t; Show copyright\n"
    "endprg\tbyte\t0,0,0\t\t\t; End of BASIC program\n"
    "\n"
    "start\trts\n"
    "\n"
    "; The assembler outputs:\n"
    "; \n"
    "; DASM V2.20.10, Macro Assembler (C)1988-2004\n"
    "; testcase.a (13): error: Label mismatch...\n"
    ";  --> endprg 081c\n"
    "; testcase.a (16): error: Label mismatch...\n"
    ";  --> start 081f\n"
    "; Unrecoverable error(s) in pass, aborting assembly!\n"
    "; Complete.\n"
    ";\n"
    "; The offending code is in symbols.c, lines 203 to 210. I think that there\n"
    "; should be an extra condition, so if in the previous pass it has been a\n"
    "; string conversion, just go for another pass.\n"
    ";\n"
    "; -----CUT-----\n"
    ";            /*\n"
    ";            * If we had an unevaluated IF expression in the\n"
    ";            * previous pass, don't complain about phase errors\n"
    ";            * too loudly.\n"
    ";                */\n"
    "; 203            if (F_verbose >= 1 || !(Redo_if & (REASON_OBSCURE)))\n"
    ";                {\n"
    ";                    char sBuffer[ MAX_SYM_LEN * 2 ];\n"
    ";                    sprintf( sBuffer, \"%s %s\", sym->name, sftos( sym->value, 0 ) );\n"
    ";                    /*, sftos(sym->value,\n"
    ";                    sym->flags) ); , sftos(pc, cflags & 7));*/\n"
    ";                    asmerr( ERROR_LABEL_MISMATCH, false, sBuffer );\n"
    "; 210            }\n"
    ";                ++Redo;\n"
    ";                Redo_why |= REASON_PHASE_ERROR;\n"
    "; -----CUT-----\n"
    "\n"
    ;

static const unsigned char CASE_string_conversion_EXPECT[34] = {
    0x1F, 0x08, 0xB0, 0x07, 0x9E, 0x32, 0x30, 0x38, 0x32, 0x20, 0x54, 0x45,
    0x53, 0x54, 0x50, 0x52, 0x4F, 0x47, 0x20, 0x42, 0x59, 0x20, 0x54, 0x45,
    0x53, 0x54, 0x53, 0x4F, 0x46, 0x54, 0x00, 0x00, 0x00, 0x60,
};

static const dasm_case_t DASM_CASES[] = {
    { "6502_16h", CASE_6502_16h_ASM, CASE_6502_16h_EXPECT, 10, 0x0000u },
    { "6502_16l", CASE_6502_16l_ASM, CASE_6502_16l_EXPECT, 10, 0x0000u },
    { "stawx", CASE_stawx_ASM, CASE_stawx_EXPECT, 13, 0x0000u },
    { "jmpiw", CASE_jmpiw_ASM, CASE_jmpiw_EXPECT, 19, 0x0000u },
    { "forced_addrmode", CASE_forced_addrmode_ASM, CASE_forced_addrmode_EXPECT, 23, 0x0000u },
    { "addressexpression", CASE_addressexpression_ASM, CASE_addressexpression_EXPECT, 11, 0x0100u },
    { "multiline_comment", CASE_multiline_comment_ASM, CASE_multiline_comment_EXPECT, 12, 0x1000u },
    { "same_names", CASE_same_names_ASM, CASE_same_names_EXPECT, 23, 0x0000u },
    { "declare_var_mac", CASE_declare_var_mac_ASM, CASE_declare_var_mac_EXPECT, 8, 0x8000u },
    { "recursive_macro0", CASE_recursive_macro0_ASM, CASE_recursive_macro0_EXPECT, 2, 0x0000u },
    { "toobigword", CASE_toobigword_ASM, CASE_toobigword_EXPECT, 2, 0xF800u },
    { "string_conversion", CASE_string_conversion_ASM, CASE_string_conversion_EXPECT, 34, 0x0801u },
};

#define DASM_CASES_COUNT (sizeof(DASM_CASES) / sizeof(DASM_CASES[0]))

#endif /* TEST_DASM_CASES_H */
