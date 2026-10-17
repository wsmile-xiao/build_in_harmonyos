/* AArch64 native port of Asmc I/O functions
 * Target: aarch64-unknown-linux-ohos
 * ReadFiles: directory enumeration with wildcard matching
 * asmerr: simplified error handler
 * ParseCmdline: command-line option parser
 * Uses musl libc dirent/opendir/readdir
 */

#include <dirent.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#include "asmc_data.h"

/* External functions from asmc_runtime.s */
extern int tprintf(const char *fmt, ...);
extern char *MemDup(const char *s);
extern int write_usage(void);
extern char *tstrcpy(char *dst, const char *src);

/* Asmc types */
typedef char *string_t;
typedef int int_t;
typedef unsigned int uint_t;

/* SourceFile template (from asmc.asm:146-149) */
typedef struct SourceFile {
    struct SourceFile *next;
    char file[1];
} SourceFile;

/* External functions from asmc_runtime.s */
extern int cmpwarg(const char *wild, const char *path);
extern string_t MemAlloc(uint_t len);
extern string_t tstrcpy(char *dst, const char *src);
extern string_t tstrcat(char *dst, const char *src);
extern uint_t tstrlen(const char *s);

/* Forward declarations for Options (not yet ported) */
extern int process_subdir; /* Options.process_subdir */

/* ReadFiles - directory enumeration with wildcard matching
 * Original: asmc.asm:ReadFiles proc __ccall uses rsi rdi rbx
 *   directory:string_t, wild:string_t, files:ptr SourceFile
 * Returns: count of files found
 */
int ReadFiles(const char *directory, const char *wild, SourceFile **files)
{
    /* Local buffer for building full paths */
    char dirbuf[4096];
    int cnt = 0;

    /* Copy directory, ensure non-empty */
    if (directory[0] == '\0') {
        dirbuf[0] = '.';
        dirbuf[1] = '\0';
    } else {
        tstrcpy(dirbuf, directory);
    }

    /* Make sure directory ends with '/' when we append filename */
    size_t dirlen = tstrlen(dirbuf);
    if (dirlen > 0 && dirbuf[dirlen - 1] != '/') {
        dirbuf[dirlen] = '/';
        dirbuf[dirlen + 1] = '\0';
        dirlen++;
    }

    DIR *dir = opendir(dirbuf);
    if (!dir)
        return 0;

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_type == DT_DIR) {
            /* Skip . and .. */
            if (entry->d_name[0] == '.' &&
                (entry->d_name[1] == '\0' ||
                 (entry->d_name[1] == '.' && entry->d_name[2] == '\0')))
                continue;
            /* Recurse into subdirectories if process_subdir is set */
            /* (Not yet implemented - requires Options struct) */
            continue;
        }

        /* Regular file: check wildcard match */
        if (cmpwarg(wild, entry->d_name)) {
            /* Build full path: dirbuf + entry->d_name */
            tstrcpy(&dirbuf[dirlen], entry->d_name);

            size_t pathlen = tstrlen(dirbuf);
            SourceFile *sf = (SourceFile *)MemAlloc(
                sizeof(SourceFile) + pathlen);
            if (sf) {
                sf->next = *files;
                *files = sf;
                tstrcpy(sf->file, dirbuf);
                cnt++;
            }
            /* Reset directory to just the path */
            dirbuf[dirlen] = '\0';
        }
    }

    closedir(dir);
    return cnt;
}

/* asmerr - simplified error handler (port of asmerr.asm:asmerr)
 * Original: asmerr proc __ccall uses rsi rdi rbx value:int_t, args:vararg
 * AArch64: value=error code, msg=error message (or NULL)
 * Prints error message via tprintf, returns 1 (ERROR)
 * Note: full asmerr with error tables, source stack, etc. requires
 * the Options/MODULE struct port; this is a minimal working version.
 */
#define MAX_ERRORS 100
static int error_count = 0;
static int warning_count = 0;

int asmerr(int value, const char *msg)
{
    const char *prefix = "ASMC : ";

    if (value >= 4000) {
        tprintf("%s%s warning A%04u: %s\n", prefix, "WARNING", value,
                msg ? msg : "unknown warning");
        warning_count++;
    } else if (value >= 2000) {
        tprintf("%s%s error A%04u: %s\n", prefix, "ERROR", value,
                msg ? msg : "unknown error");
        error_count++;
        if (error_count >= MAX_ERRORS) {
            tprintf("%s%s fatal error A%04u: %s\n", prefix, "FATAL",
                    1012, "too many errors");
            return 1;
        }
    } else {
        tprintf("%s%s fatal error A%04u: %s\n", prefix, "FATAL", value,
                msg ? msg : "unknown fatal error");
        return 1;
    }
    return 1;
}

/* === ParseCmdline (port of cmdline.asm:ParseCmdline) ===
 * Parses the command line, processing options (-X) and file names
 * Returns: 0 when done or file found, 1 for more args
 * On finding a file name, stores it in Options.names[TASM]
 */
#include "asmc_data.h"

/* GetNameToken - simplified token extraction */
static const char *GetNameToken(char *buf, const char *src, int maxlen, char stop)
{
    int i = 0;
    while (*src && *src != stop && *src != ' ' && *src != '\t' && *src != '\n' && i < maxlen - 1) {
        buf[i++] = *src++;
    }
    buf[i] = '\0';
    return src;
}

/* ReadParamFile - read response file content (simplified) */
static char *ReadParamFile(const char *fname)
{
    (void)fname;  /* not implemented yet */
    return NULL;
}

/* ProcessOption - process a single command-line option */
static int ProcessOption(const char **args, char *paramfile)
{
    (void)paramfile;
    const char *arg = *args;
    if (!arg || !*arg) return 0;
    if (*arg == '-') arg++;

    switch (*arg) {
    case 'c': Options.no_linking = 1; break;
    case 'q': Options.quiet = 1; break;
    case 'r': Options.process_subdir = 1; break;
    case 'X': Options.ignore_include = 1; break;
    case 'S':
        if (arg[1] == 'n') Options.no_symbol_listing = 1;
        else if (arg[1] == 'f') Options.first_pass_listing = 1;
        break;
    case 'Z':
        if (arg[1] == 'f') Options.all_symbols_public = 1;
        else if (arg[1] == 'd') Options.line_numbers = 1;
        else if (arg[1] == 'i') Options.debug_symbols = 1;
        else if (arg[1] == '7') { Options.debug_symbols = 1; Options.debug_ext = 1; }
        else if (arg[1] == 's') Options.syntax_check_only = 1;
        break;
    case 'F':
        if (arg[1] == 'o') Options.names[TOBJ] = (char*)(arg + 2);
        else if (arg[1] == 'e') Options.names[TOBJ] = (char*)(arg + 2);
        break;
    case 'e':
        Options.error_limit = 0;
        for (const char *p = arg + 1; *p >= '0' && *p <= '9'; p++)
            Options.error_limit = Options.error_limit * 10 + (*p - '0');
        break;
    case 'W':
        if (arg[1] == 'X') Options.warning_error = 1;
        else if (arg[1] >= '0' && arg[1] <= '9') Options.warning_level = arg[1] - '0';
        break;
    case 'w': Options.warning_level = 0; Options.warning_error = 1; break;
    case 'n':
        if (arg[1] == 'o' && arg[2] == 'l' && arg[3] == 'i' && arg[4] == 'b')
            Options.nolib = 1;
        break;
    case 's':
        if (arg[1]=='a'&&arg[2]=='f'&&arg[3]=='e'&&arg[4]=='s'&&arg[5]=='e'&&arg[6]=='h')
            Options.safeseh = 1;
        break;
    case '?': write_usage(); break;
    default: break;
    }
    return 1;
}

/* ParseCmdline - main command-line parser
 * Original: cmdline.asm:ParseCmdline proc __ccall
 *   cmdline:ptr string_t, numargs:ptr int_t
 * Parses the command line, processing options and file names.
 * Returns: 0 when done, 1 for more args
 * On finding a file name, stores it in Options.names[TASM] and returns 0.
 */
int ParseCmdline(const char **cmdline, int *numargs)
{
    const char *p = *cmdline;
    char paramfile[260];

    if (!p) return 0;

    while (*p) {
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
        if (*p == '\0') break;

        switch (*p) {
        case '@':
            p++;
            p = GetNameToken(paramfile, p, sizeof(paramfile) - 1, '@');
            if (paramfile[0]) {
                char *rf = ReadParamFile(paramfile);
                if (rf) { const char *rfp = rf; ParseCmdline(&rfp, numargs); }
            }
            break;
        case '-':
        case '/':
            p++;
            *cmdline = p;
            ProcessOption(cmdline, paramfile);
            (*numargs)++;
            p = *cmdline;
            break;
        default:
            p = GetNameToken(paramfile, p, sizeof(paramfile) - 1, '@');
            *cmdline = p;
            Options.names[TASM] = MemDup(paramfile);
            (*numargs)++;
            return 0;
        }
    }
    *cmdline = p;
    return 0;
}

/* CmdlineFini - clean up command line options
 * Original: cmdline.asm:CmdlineFini
 */
void CmdlineFini(void)
{
    for (int i = 0; i < NUM_FILE_TYPES; i++) {
        if (Options.names[i]) {
            Options.names[i] = NULL;
        }
    }
}

/* === AssembleModule (real pipeline: tokenize -> encode -> .bin + ELF output) ===
 * Port of assemble.asm:AssembleModule + tokenize.asm + bin.asm/elf.asm semantics.
 * Opened file is tokenized line by line, tokens are parsed and encoded to
 * x86/x86-64 target bytes, then written as flat binary (.bin) AND as an
 * ELF64 relocatable object (.o) with symbols and relocations.
 * Invalid instructions produce diagnostics (asmerr) and error count.
 */
int AssembleModule(const char *fname)
{
    asm_output_t *out = (asm_output_t *)malloc(sizeof(asm_output_t));
    if (!out) return -1;
    int errs = AssembleToBin(fname, out);

    if (!errs) {
        tprintf(" Assembling: %s\n", fname);
        WriteBinOutput(out, fname);
        WriteElfOutput(out, fname);
        tprintf("%s: assembled %zu bytes of x86/x86-64 target code\n",
                fname, out->text_len + out->data_len);
        int total = (int)(out->text_len + out->data_len);
        free(out);
        return total;
    }
    tprintf("%s: assembly failed with errors\n", fname);
    free(out);
    return errs;
}

/* process_cmdline - wire init_options + ParseCmdline + AssembleModule from main()
 * Original: asmc.asm:main calls ParseCmdline + AssembleModule in a loop
 * AArch64: argv=char**, environ=char**
 * Returns: 0 success, 1 no input
 */
int process_cmdline(char **argv, char **environ)
{
    (void)environ;

    init_options();

    if (!argv[1]) {
        write_usage();
        return 1;
    }

    const char *cmd = argv[1];
    int numargs = 0;
    ParseCmdline(&cmd, &numargs);

    if (Options.names[TASM]) {
        AssembleModule(Options.names[TASM]);
        return 0;
    }
    write_usage();
    return 1;
}