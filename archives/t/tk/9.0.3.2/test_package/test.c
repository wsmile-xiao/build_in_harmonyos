#include <tcl.h>
#include <tk.h>
#include <stdio.h>

/*
 * tk/9.0.3.1 test_package — C 级用户测试
 *
 * 链接 libtcl9tk9.0.so（NEEDED），调用 Tcl/Tk C API 验证库可加载且运行时可初始化。
 * 使用 _exit(0) 避免 OHOS 系统库 atexit 悬空（dlclose segfault 根因）。
 */
int main(void) {
    /* 1. 创建 Tcl 解释器 */
    Tcl_Interp *interp = Tcl_CreateInterp();
    if (!interp) {
        fprintf(stderr, "FAIL: Tcl_CreateInterp returned NULL\n");
        _exit(1);
    }
    fprintf(stderr, "ok: Tcl_CreateInterp\n");

    /* 2. 初始化 Tcl */
    if (Tcl_Init(interp) != TCL_OK) {
        fprintf(stderr, "FAIL: Tcl_Init: %s\n", Tcl_GetStringResult(interp));
        _exit(1);
    }
    fprintf(stderr, "ok: Tcl_Init\n");

    /* 3. 初始化 Tk — 真正的 Tk C API 调用 */
    if (Tk_Init(interp) != TCL_OK) {
        fprintf(stderr, "FAIL: Tk_Init: %s\n", Tcl_GetStringResult(interp));
        _exit(1);
    }
    fprintf(stderr, "ok: Tk_Init\n");

    /* 4. 验证 tk_version 变量 */
    const char *ver = Tcl_GetVar(interp, "tk_version", TCL_GLOBAL_ONLY);
    if (!ver) {
        fprintf(stderr, "FAIL: tk_version not set\n");
        _exit(1);
    }
    fprintf(stderr, "ok: tk_version=%s\n", ver);

    /* 5. 验证 Tk 命令注册 */
    Tcl_CmdInfo info;
    if (!Tcl_GetCommandInfo(interp, "toplevel", &info)) {
        fprintf(stderr, "FAIL: toplevel command not found\n");
        _exit(1);
    }
    fprintf(stderr, "ok: toplevel command registered\n");

    Tcl_DeleteInterp(interp);
    _exit(0);
}
