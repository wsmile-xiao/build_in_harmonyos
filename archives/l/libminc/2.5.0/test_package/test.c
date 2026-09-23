/*
 * libminc test_package —— 真实消费者断言（交叉编译后真跑）
 *
 * 覆盖两条格式链路：
 *   MINC2（HDF5 底层）：micreate_dimension/micreate_volume/miset_voxel_value_hyperslab
 *     写 3D 卷 → 关闭 → miopen_volume 读回逐元素对账；
 *     并用 HDF5 直连 API（H5Fis_hdf5）断言该文件真的是 HDF5 存储 —— 证明 hdf5
 *     依赖真接上（netcdf 包 test_package 同型手法）。
 *   MINC1（netcdf 底层，需配方 LIBMINC_MINC1_SUPPORT=ON）：micreate/ncdimdef/
 *     micreate_std_variable/ncvarput 写卷 → ncvarget 读回对账；
 *     并用 netcdf 直连 API（ncopen/ncinq）断言文件真的是 netCDF 存储。
 *   编译期断言 MINC1/MINC2 公开结构宏（MAX_VAR_DIMS）存在，防止空壳安装。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <minc2.h>
#include <minc.h>
#include <hdf5.h>
#include <netcdf.h>

#if !defined(MAX_VAR_DIMS)
#error "minc.h: MAX_VAR_DIMS missing — header installation broken"
#endif

#define XSIZE 4
#define YSIZE 3
#define ZSIZE 2

static int g_errors = 0;
#define CHECK(cond, what) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL(line %d): %s\n", __LINE__, (what)); \
        ++g_errors; \
    } \
} while (0)

/* ---------- MINC2：写 3D short 卷并读回 ---------- */
static void test_minc2_roundtrip(const char *path)
{
    static const char *names[3] = { MIxspace, MIyspace, MIzspace };
    static const misize_t lens[3] = { XSIZE, YSIZE, ZSIZE };
    midimhandle_t dims[3];
    mihandle_t vol = NULL, vol2 = NULL;
    short data[XSIZE * YSIZE * ZSIZE];
    short back[XSIZE * YSIZE * ZSIZE];
    misize_t start[3] = { 0, 0, 0 };
    misize_t count[3] = { XSIZE, YSIZE, ZSIZE };
    int i, rc;

    printf("[minc2] create %s\n", path);
    for (i = 0; i < 3; ++i) {
        rc = micreate_dimension(names[i], MI_DIMCLASS_SPATIAL,
                                MI_DIMATTR_REGULARLY_SAMPLED, lens[i], &dims[i]);
        CHECK(rc == MI_NOERROR, "micreate_dimension");
    }
    rc = micreate_volume(path, 3, dims, MI_TYPE_SHORT, MI_CLASS_REAL, NULL, &vol);
    CHECK(rc == MI_NOERROR, "micreate_volume");
    rc = micreate_volume_image(vol);
    CHECK(rc == MI_NOERROR, "micreate_volume_image");

    for (i = 0; i < XSIZE * YSIZE * ZSIZE; ++i) {
        data[i] = (short)(i * 3 + 1);
    }
    rc = miset_voxel_value_hyperslab(vol, MI_TYPE_SHORT, start, count, data);
    CHECK(rc == MI_NOERROR, "miset_voxel_value_hyperslab");
    rc = miclose_volume(vol);
    CHECK(rc == MI_NOERROR, "miclose_volume(write)");

    /* 底层指纹：MINC2 文件必须是 HDF5 存储 */
    CHECK(H5Fis_hdf5(path) > 0, "H5Fis_hdf5(minc2 file) != hdf5");

    rc = miopen_volume(path, MI2_OPEN_READ, &vol2);
    CHECK(rc == MI_NOERROR, "miopen_volume");
    rc = miget_voxel_value_hyperslab(vol2, MI_TYPE_SHORT, start, count, back);
    CHECK(rc == MI_NOERROR, "miget_voxel_value_hyperslab");
    rc = miclose_volume(vol2);
    CHECK(rc == MI_NOERROR, "miclose_volume(read)");

    for (i = 0; i < XSIZE * YSIZE * ZSIZE; ++i) {
        if (back[i] != data[i]) {
            fprintf(stderr, "FAIL: voxel[%d] wrote %d read %d\n", i, data[i], back[i]);
            ++g_errors;
            break;
        }
    }
    printf("[minc2] roundtrip OK (%d voxels)\n", XSIZE * YSIZE * ZSIZE);
}

/* ---------- MINC1：netcdf 底层写读 ---------- */
static void test_minc1_roundtrip(const char *path)
{
    int cdfid, dimid[3], imgid, i, fd, vid;
    int dims[3];
    static const char *names[3] = { MIxspace, MIyspace, MIzspace };
    static const long lens[3] = { XSIZE, YSIZE, ZSIZE };
    long start[3] = { 0, 0, 0 };
    long count[3] = { XSIZE, YSIZE, ZSIZE };
    short data[XSIZE * YSIZE * ZSIZE];
    short back[XSIZE * YSIZE * ZSIZE];

    printf("[minc1] create %s\n", path);
    cdfid = micreate(path, NC_CLOBBER);
    CHECK(cdfid >= 0, "micreate(minc1)");
    if (cdfid < 0) {
        return;
    }
    for (i = 0; i < 3; ++i) {
        dimid[i] = ncdimdef(cdfid, names[i], lens[i]);
        CHECK(dimid[i] >= 0, "ncdimdef");
    }
    imgid = micreate_std_variable(cdfid, MIimage, NC_SHORT, 3, dimid);
    CHECK(imgid >= 0, "micreate_std_variable(MIimage)");
    CHECK(ncendef(cdfid) == NC_NOERR, "ncendef");

    for (i = 0; i < XSIZE * YSIZE * ZSIZE; ++i) {
        data[i] = (short)(i * 7 + 5);
    }
    vid = ncvarid(cdfid, MIimage);
    CHECK(vid >= 0, "ncvarid(MIimage)");
    CHECK(ncvarput(cdfid, vid, start, count, data) == NC_NOERR, "ncvarput");
    CHECK(miclose(cdfid) == NC_NOERR, "miclose(minc1)");

    /* 底层指纹：MINC1 文件必须是 netCDF 存储 */
    fd = ncopen(path, NC_NOWRITE);
    CHECK(fd >= 0, "ncopen(minc1 file)");
    if (fd >= 0) {
        int ndims = 0, nvars = 0, ngatts = 0, unlim = 0;
        int fmt = -1;
        /* netcdf 4.x 头只保留旧名 ncinquire（ncinq 无宏映射）。
         * V2 兼容语义：成功返回 ncid（netcdf4 的 id 自 65536 起）而非 NC_NOERR。
         */
        int qrc = ncinquire(fd, &ndims, &nvars, &ngatts, &unlim);
        (void)nc_inq_format(fd, &fmt);
        printf("[minc1] ncinquire rc=%d (fmt=%d) ndims=%d nvars=%d\n", qrc, fmt, ndims, nvars);
        CHECK(qrc == NC_NOERR || qrc == fd, "ncinquire");
        CHECK(fmt == NC_FORMAT_CLASSIC, "minc1 file is classic netcdf");
        CHECK(ndims == 3 && nvars >= 1, "ncinquire(minc1 structure)");
        ncclose(fd);
    }

    /* 重开读回（MINC1 语义：miopen + ncvarget） */
    fd = miopen(path, NC_NOWRITE);
    CHECK(fd >= 0, "miopen(minc1)");
    if (fd >= 0) {
        vid = ncvarid(fd, MIimage);
        CHECK(vid >= 0, "ncvarid(MIimage, reopen)");
        CHECK(ncvarget(fd, vid, start, count, back) == NC_NOERR, "ncvarget");
        miclose(fd);
    }
    for (i = 0; i < XSIZE * YSIZE * ZSIZE; ++i) {
        if (back[i] != data[i]) {
            fprintf(stderr, "FAIL: minc1 voxel[%d] wrote %d read %d\n", i, data[i], back[i]);
            ++g_errors;
            break;
        }
    }
    printf("[minc1] roundtrip OK (%d voxels)\n", XSIZE * YSIZE * ZSIZE);
}

int main(int argc, char **argv)
{
    char p2[512], p1[512];
    const char *dir = ".";
    if (argc > 1) {
        dir = argv[1];
    }
    snprintf(p2, sizeof(p2), "%s/tp_minc2_volume.mnc", dir);
    snprintf(p1, sizeof(p1), "%s/tp_minc1_volume.mnc", dir);

    printf("libminc test_package start\n");
    test_minc2_roundtrip(p2);
    test_minc1_roundtrip(p1);
    remove(p2);
    remove(p1);
    if (g_errors) {
        fprintf(stderr, "RESULT: FAILED (errors=%d)\n", g_errors);
        return 1;
    }
    printf("RESULT: ALL OK\n");
    return 0;
}
