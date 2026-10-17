/*
 * HarmonyOS 专项测试：验证 netcdf-c 在 aarch64-linux-ohos 平台上的
 * netCDF-4（HDF5 后端）真实读写能力。
 *
 * 覆盖点（均为真实 API 调用，非空壳）：
 *  1. nc_create 创建 netCDF-4 文件（NC_NETCDF4 + NC_CLOBBER）
 *  2. nc_def_dim/nc_def_var 定义维度与变量
 *  3. nc_enddef 结束定义模式
 *  4. nc_put_var_int 写入 2x3 整数矩阵
 *  5. nc_close / nc_open 关闭重开（验证文件落盘可重读）
 *  6. nc_get_var_int 读回并逐元素比对，不一致即失败
 *  7. 清理临时文件，返回真实退出码
 *
 * 编译：clang -I<include> -L<lib> -lnetcdf -lhdf5_hl -lhdf5 -lz -lcurl test_ohos_nc4.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <netcdf.h>

#define DIM0 2
#define DIM1 3
#define CHECK_ERR(e, msg) do { \
    int _e = (e); \
    if (_e != NC_NOERR) { \
        fprintf(stderr, "[OHOS-SPECIFIC] %s failed: %s\n", (msg), nc_strerror(_e)); \
        return 1; \
    } \
} while (0)

int main(void) {
    const char *path = "ohos_nc4_roundtrip.nc";
    int ncid, dimid0, dimid1, varid;
    int in[DIM0][DIM1] = {{1, 2, 3}, {4, 5, 6}};
    int out[DIM0][DIM1] = {{0}};

    CHECK_ERR(nc_create(path, NC_CLOBBER | NC_NETCDF4, &ncid), "nc_create");
    CHECK_ERR(nc_def_dim(ncid, "row", DIM0, &dimid0), "nc_def_dim(row)");
    CHECK_ERR(nc_def_dim(ncid, "col", DIM1, &dimid1), "nc_def_dim(col)");
    {
        int dimids[2] = {dimid0, dimid1};
        CHECK_ERR(nc_def_var(ncid, "matrix", NC_INT, 2, dimids, &varid), "nc_def_var");
    }
    CHECK_ERR(nc_enddef(ncid), "nc_enddef");
    CHECK_ERR(nc_put_var_int(ncid, varid, &in[0][0]), "nc_put_var_int");
    CHECK_ERR(nc_close(ncid), "nc_close");

    CHECK_ERR(nc_open(path, NC_NOWRITE, &ncid), "nc_open");
    CHECK_ERR(nc_inq_varid(ncid, "matrix", &varid), "nc_inq_varid");
    CHECK_ERR(nc_get_var_int(ncid, varid, &out[0][0]), "nc_get_var_int");
    CHECK_ERR(nc_close(ncid), "nc_close(2)");

    if (memcmp(in, out, sizeof(in)) != 0) {
        fprintf(stderr, "[OHOS-SPECIFIC] MISMATCH: got %d,%d,%d,%d,%d,%d\n",
                out[0][0], out[0][1], out[0][2], out[1][0], out[1][1], out[1][2]);
        return 1;
    }

    remove(path);
    printf("[OHOS-SPECIFIC] PASS: netCDF-4 2x3 int matrix round-trip on aarch64-linux-ohos\n");
    return 0;
}
