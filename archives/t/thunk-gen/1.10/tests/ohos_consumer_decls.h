/* OHOS consumer sample declarations for thunk_gen 1.10.
 *
 * 这批声明模拟下游消费者（dj64dev / comcom64 / fdpp 一类 16/32 位 DOS
 * thunk 工程）交给 thunk_gen 的输入：先用 scripts/parse_decls.sh 从声明
 * 头里筛出两类行，编号后再送进 thunk_gen。
 *
 *   parse_decls.sh 1  -> 只保留“调用侧”的 4 行（送入 thunk_gen 生成 C 派发表）
 *   parse_decls.sh 2  -> 只保留“定义侧”的 2 行（送入 thunk_gen 生成 asm/m4 表）
 *
 * 为了让两个筛选器的“排除”语义也被真实覆盖，下面各放一条干扰行：
 * 第 20 行（宏定义占首）不得进入筛选器 1，第 23~24 行（注释）不得进入筛选器 2。
 * 因此筛选器 1 应恰好输出 4 行，筛选器 2 应恰好输出 2 行。
 */

/* ---- caller side: 4 declarations (selected by parse_decls.sh 1) ---- */
void ASMCFUNC _dos_open(const char *path, int flags);
unsigned int ASMCFUNC _dos_close(int fd);
void ASMCFUNC _dos_putc(unsigned char c);
void ASMCFUNC NORETURN _dos_exit(int code);
#define ASMCFUNC_SYNONYM 1

/* ---- definition side: 2 declarations (selected by parse_decls.sh 2) ---- */
// ASMFUNC / ASMPASCAL definitions below; this line and the macro line above
// must be filtered out by parse_decls.sh.
unsigned short ASMPASCAL _dos_getfree(void);
void ASMFUNC _dos_ret_ax(unsigned int ax);
