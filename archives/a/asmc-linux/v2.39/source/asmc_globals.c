/* AArch64 native port: Asmc global state (Options, ModuleInfo)
 * Port of asmc.inc: extern defs + cmdline.asm Options init
 * Target: aarch64-unknown-linux-ohos
 */

#include "asmc_data.h"

/* Global instances */
global_options Options = {0};
module_info ModuleInfo = {0};
uint_t Parse_Pass = 0;

/* Initialize Options with defaults (from cmdline.asm Options init) */
void init_options(void)
{
    Options.floating_point = 0;    /* FPO_NO_EMULATION */
    Options.error_limit = 50;
    Options.list_macro = 1;        /* LM_LISTMACRO */
    Options.output_format = 0;     /* OFORMAT_OMF */
    Options.sub_format = 0;        /* SFORMAT_NONE */
    Options.langtype = 0;          /* LANG_NONE */
    Options._model = 0;            /* MODEL_NONE */
    Options.fctype = 0;            /* FCT_MSC */
    Options.codepage = 0;
    Options.floatdigits = 1;
    Options.warning_level = 2;
    Options.stdcall_decoration = 1; /* STDCALL_FULL */
    Options.floatformat = 0;
    Options.flt_size = 4;
    Options.fieldalign = 0;
    Options.loopalign = 0;
    Options.casealign = 0;
    Options.segmentalign = 4;
    Options.pe_subsystem = 3;
    Options.win64_flags = 0;
    Options.arch = 0;
    Options.iddc = 0;
    Options.frame_auto = 0;
    Options.debug_symbols = 0;
    Options.debug_ext = 0;
    Options.link = 0;
    Options.no_linking = 0;       /* -c not set */
    Options.quiet = 0;
    Options.line_numbers = 0;

    /* Clear name slots */
    for (int i = 0; i < OPTN_LAST; i++)
        Options.names[i] = 0;
}