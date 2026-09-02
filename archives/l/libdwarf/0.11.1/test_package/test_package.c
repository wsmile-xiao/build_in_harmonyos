/*
 * test_package.c — libdwarf 0.11.1 L1 消费者测试（真实 DWARF 验证）
 *
 * 用法: test_package <fixture-path>
 *   - 必须提供 fixture-path 参数；缺失或无效路径 -> 非零退出。
 *   - 用 libdwarf 实际 API 初始化 Dwarf_Debug，遍历真实 compilation unit
 *     获得非 NULL Dwarf_Die，调用 dwarf_attrlist() 验证至少一个真实属性，
 *     并对属性执行显式成功查询（dwarf_hasform）。
 *   - 释放所有获取的资源（attribute/list/DIE/Dwarf_Error/Dwarf_Debug），
 *     任一失败分支清理自身持有项并以非零返回。
 *
 * 禁止：NULL/零化 Dwarf_Die、无条件 EXIT_SUCCESS、伪造返回。
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef LIBDWARF_NESTED_INCLUDE
    #include "libdwarf/dwarf.h"
    #include "libdwarf/libdwarf.h"
#else
    #include <dwarf.h>
    #include <libdwarf.h>
#endif

static int verify_dwarf(const char *path) {
    Dwarf_Debug dbg = 0;
    Dwarf_Error error = 0;
    Dwarf_Die cu_die = 0;
    Dwarf_Attribute *atlist = 0;
    Dwarf_Signed atcount = 0;
    Dwarf_Signed i = 0;
    int res = DW_DLV_ERROR;
    int ret = EXIT_FAILURE;
    int rc;
    Dwarf_Unsigned cu_header_len = 0, abbrev_off = 0, next_cu_off = 0, typeoff = 0;
    Dwarf_Half version_stamp = 0, addr_size = 0, len_size = 0, ext_size = 0, hdr_cu_type = 0;
    Dwarf_Sig8 type_sig;
    memset(&type_sig, 0, sizeof(type_sig));

    rc = dwarf_init_path(path, NULL, 0, 0, NULL, NULL, &dbg, &error);
    if (rc != DW_DLV_OK) {
        fprintf(stderr, "FAIL: dwarf_init_path(%s) rc=%d\n", path, rc);
        if (rc == DW_DLV_ERROR && error) {
            dwarf_dealloc(dbg, error, DW_DLA_ERROR);
            error = 0;
        }
        return EXIT_FAILURE;
    }

    /* 遍历真实 compilation unit，获得有效非 NULL Dwarf_Die */
    rc = dwarf_next_cu_header_e(dbg, (Dwarf_Bool)1,
        &cu_die, &cu_header_len, &version_stamp, &abbrev_off,
        &addr_size, &len_size, &ext_size, &type_sig, &typeoff,
        &next_cu_off, &hdr_cu_type, &error);
    if (rc != DW_DLV_OK || cu_die == 0) {
        fprintf(stderr, "FAIL: dwarf_next_cu_header_e rc=%d cu_die=%p\n", rc, (void *)cu_die);
        if (rc == DW_DLV_ERROR && error) {
            dwarf_dealloc(dbg, error, DW_DLA_ERROR);
            error = 0;
        }
        dwarf_finish(dbg);
        return EXIT_FAILURE;
    }
    fprintf(stdout, "OK: CU obtained version=%u addr_size=%u\n",
            (unsigned)version_stamp, (unsigned)addr_size);

    /* 对有效 DIE 调用 dwarf_attrlist，验证真实属性 */
    res = dwarf_attrlist(cu_die, &atlist, &atcount, &error);
    if (res != DW_DLV_OK) {
        fprintf(stderr, "FAIL: dwarf_attrlist rc=%d\n", res);
        if (res == DW_DLV_ERROR && error) {
            dwarf_dealloc(dbg, error, DW_DLA_ERROR);
            error = 0;
        }
        dwarf_dealloc_die(cu_die);
        cu_die = 0;
        dwarf_finish(dbg);
        return EXIT_FAILURE;
    }
    if (atcount <= 0 || atlist == 0) {
        fprintf(stderr, "FAIL: dwarf_attrlist atcount=%lld (need real attribute)\n",
                (long long)atcount);
        if (atlist) {
            dwarf_dealloc(dbg, atlist, DW_DLA_LIST);
            atlist = 0;
        }
        dwarf_dealloc_die(cu_die);
        cu_die = 0;
        dwarf_finish(dbg);
        return EXIT_FAILURE;
    }

    /* 显式成功查询：对每个属性 dwarf_hasform；至少一个返回 OK */
    {
        int ok_query = 0;
        for (i = 0; i < atcount; ++i) {
            Dwarf_Bool is_string = (Dwarf_Bool)0;
            int hr = dwarf_hasform(atlist[i], DW_FORM_string, &is_string, &error);
            if (hr == DW_DLV_OK) {
                ok_query = 1;
            } else if (hr == DW_DLV_ERROR && error) {
                dwarf_dealloc(dbg, error, DW_DLA_ERROR);
                error = 0;
            }
            dwarf_dealloc(dbg, atlist[i], DW_DLA_ATTR);
            atlist[i] = 0;
        }
        if (!ok_query) {
            fprintf(stderr, "FAIL: no explicit successful dwarf_hasform query\n");
            dwarf_dealloc(dbg, atlist, DW_DLA_LIST);
            atlist = 0;
            dwarf_dealloc_die(cu_die);
            cu_die = 0;
            dwarf_finish(dbg);
            return EXIT_FAILURE;
        }
        fprintf(stdout, "OK: dwarf_attrlist atcount=%lld with real query success\n",
                (long long)atcount);
    }

    /* 释放 list、DIE、dbg */
    if (atlist) {
        dwarf_dealloc(dbg, atlist, DW_DLA_LIST);
        atlist = 0;
    }
    if (cu_die) {
        dwarf_dealloc_die(cu_die);
        cu_die = 0;
    }
    rc = dwarf_finish(dbg);
    dbg = 0;
    if (rc != DW_DLV_OK) {
        fprintf(stderr, "FAIL: dwarf_finish rc=%d\n", rc);
        return EXIT_FAILURE;
    }
    fprintf(stdout, "OK: libdwarf 0.11.1 fixture DWARF validation PASSED (%s)\n", path);
    ret = EXIT_SUCCESS;
    return ret;
}

int main(int argc, char **argv) {
    const char *path = NULL;
    FILE *f;

    /* 优先级: 显式参数 > 环境变量 DWARF_FIXTURE_PATH > CMake 编译期默认 */
    if (argc >= 2) {
        path = argv[1];
    } else {
        const char *env_path = getenv("DWARF_FIXTURE_PATH");
        if (env_path && env_path[0]) {
            path = env_path;
        } else {
#ifdef DWARF_FIXTURE_PATH
            path = DWARF_FIXTURE_PATH;
#endif
        }
    }

    if (!path || !path[0]) {
        fprintf(stderr, "FAIL: missing fixture-path argument (usage: test_package <fixture-path>)\n");
        return EXIT_FAILURE;
    }

    /* 无效路径校验：必须存在且可读 */
    f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: fixture path not readable: %s\n", path);
        return EXIT_FAILURE;
    }
    fclose(f);
    return verify_dwarf(path);
}
