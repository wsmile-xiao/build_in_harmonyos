/* netCDF-c 4.9.3 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 文件读写得对。这里真的**建一个 netCDF-4 文件、
 * 写进去、关掉、重新打开、读回来**，再逐元素对账。
 *
 * 走 NC_NETCDF4 格式是有意的：那条路径底下是 HDF5，能一并验证
 * hdf5 依赖真的接上了 —— 只用经典 CDF 格式的话，HDF5 根本不会被调用，
 * 依赖接没接上测不出来。
 *
 * 覆盖：
 *   ① 建库/定义维度与变量/写入/关闭
 *   ② 重新打开后元数据（维度长度、变量类型、属性）与写入时一致
 *   ③ 数据逐元素相等
 *   ④ 错误路径：打开一个不存在的文件必须返回错误而不是崩溃
 */
#include <netcdf.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NX 4
#define NY 3
#define PATH "nc_test_tmp.nc"

static int fail(const char *what, int status)
{
    printf("FAIL %s: %s\n", what, nc_strerror(status));
    return 1;
}

int main(void)
{
    int ncid, x_dim, y_dim, varid, st;
    int dims[2];
    int data[NX][NY], back[NX][NY];
    const char *ATT = "batch36";

    for (int i = 0; i < NX; ++i)
        for (int j = 0; j < NY; ++j)
            data[i][j] = i * 100 + j;

    remove(PATH);

    /* ① 建库并写入（NC_NETCDF4 → 底层走 HDF5） */
    if ((st = nc_create(PATH, NC_NETCDF4 | NC_CLOBBER, &ncid)))
        return fail("nc_create", st);
    if ((st = nc_def_dim(ncid, "x", NX, &x_dim))) return fail("def_dim x", st);
    if ((st = nc_def_dim(ncid, "y", NY, &y_dim))) return fail("def_dim y", st);
    dims[0] = x_dim; dims[1] = y_dim;
    if ((st = nc_def_var(ncid, "v", NC_INT, 2, dims, &varid)))
        return fail("def_var", st);
    if ((st = nc_put_att_text(ncid, varid, "origin", strlen(ATT), ATT)))
        return fail("put_att", st);
    if ((st = nc_enddef(ncid))) return fail("enddef", st);
    if ((st = nc_put_var_int(ncid, varid, &data[0][0])))
        return fail("put_var", st);
    if ((st = nc_close(ncid))) return fail("close(write)", st);

    /* ② 重新打开，元数据必须与写入时一致 */
    if ((st = nc_open(PATH, NC_NOWRITE, &ncid))) return fail("nc_open", st);
    {
        int rvar, ndims, natts;
        nc_type xtype;
        int rdims[2];
        size_t lenx, leny;
        char att[64] = {0};

        if ((st = nc_inq_varid(ncid, "v", &rvar))) return fail("inq_varid", st);
        if ((st = nc_inq_var(ncid, rvar, NULL, &xtype, &ndims, rdims, &natts)))
            return fail("inq_var", st);
        if (xtype != NC_INT || ndims != 2) {
            printf("FAIL 变量类型/维数不符: xtype=%d ndims=%d，期望 NC_INT/2\n",
                   (int)xtype, ndims);
            return 1;
        }
        if ((st = nc_inq_dimlen(ncid, rdims[0], &lenx))) return fail("dimlen x", st);
        if ((st = nc_inq_dimlen(ncid, rdims[1], &leny))) return fail("dimlen y", st);
        if (lenx != NX || leny != NY) {
            printf("FAIL 维度长度 (%zu,%zu) != (%d,%d)\n", lenx, leny, NX, NY);
            return 1;
        }
        if ((st = nc_get_att_text(ncid, rvar, "origin", att)))
            return fail("get_att", st);
        if (strncmp(att, ATT, strlen(ATT)) != 0) {
            printf("FAIL 属性 [%s] != [%s]\n", att, ATT);
            return 1;
        }

        /* ③ 数据逐元素对账 */
        if ((st = nc_get_var_int(ncid, rvar, &back[0][0])))
            return fail("get_var", st);
        for (int i = 0; i < NX; ++i)
            for (int j = 0; j < NY; ++j)
                if (back[i][j] != data[i][j]) {
                    printf("FAIL 数据 [%d][%d] = %d，期望 %d\n",
                           i, j, back[i][j], data[i][j]);
                    return 1;
                }
    }
    if ((st = nc_close(ncid))) return fail("close(read)", st);
    remove(PATH);

    /* ④ 错误路径：打不开的文件要返回错误码，不能崩溃也不能假装成功 */
    {
        int bad;
        st = nc_open("definitely_not_here_4a7f.nc", NC_NOWRITE, &bad);
        if (st == NC_NOERR) {
            printf("FAIL 打开不存在的文件竟然成功了\n");
            return 1;
        }
    }

    printf("netcdf OK: NC_NETCDF4(HDF5 后端) 建库/写入/重开/元数据与数据逐元素对账 "
           "+ 错误路径，共 4 组；库版本 %s\n", nc_inq_libvers());
    return 0;
}
