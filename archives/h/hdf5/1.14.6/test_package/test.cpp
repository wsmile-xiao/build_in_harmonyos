/* HDF5 1.14.6 真实功能断言。
 *
 * 消费方 ecell4-base 用的是 **C++ API**（H5Cpp.h / H5File / H5std_string）加 HL，
 * 所以测试必须覆盖 C++ 层与 HL 层——只验 C 层会漏掉真正被消费的部分：
 * 这两层各是独立的 .so（libhdf5_cpp / libhdf5_hl），任何一个没装出来或没导出符号，
 * 只测 C 层都发现不了，要等下游构建期才炸。
 *
 * 四条断言：
 *   ① C++ API：建文件 → 写 2D 数据集 → 读回逐元素比对
 *   ② HL API ：H5LTmake_dataset / H5LTread_dataset 往返
 *   ③ szip 过滤器**确实可用**（H5Zfilter_avail(H5Z_FILTER_SZIP)）——
 *      这是我们特意为它做 libaec 的理由；若为假则说明 szip 没接上，
 *      包能装但压缩数据集读不了。
 *   ④ zlib(deflate) 过滤器同理。
 */
#include <H5Cpp.h>
#include <hdf5.h>
#include <hdf5_hl.h>
#include <cstdio>
#include <cstring>
#include <string>

static const int NX = 8, NY = 5;

static int test_cpp_api(const char *path)
{
    const H5std_string fname(path);
    const H5std_string dsname("ramp");
    int wbuf[NX][NY];
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            wbuf[i][j] = i * 100 + j;

    try {
        H5::H5File file(fname, H5F_ACC_TRUNC);
        hsize_t dims[2] = {NX, NY};
        H5::DataSpace space(2, dims);
        H5::DataSet ds = file.createDataSet(dsname, H5::PredType::NATIVE_INT, space);
        ds.write(wbuf, H5::PredType::NATIVE_INT);
    } catch (H5::Exception &e) {
        std::printf("FAIL C++ 写入: %s\n", e.getDetailMsg().c_str());
        return 1;
    }

    int rbuf[NX][NY];
    std::memset(rbuf, 0, sizeof(rbuf));
    try {
        H5::H5File file(fname, H5F_ACC_RDONLY);
        H5::DataSet ds = file.openDataSet(dsname);
        H5::DataSpace sp = ds.getSpace();
        if (sp.getSimpleExtentNdims() != 2) { std::printf("FAIL 维度不是 2\n"); return 1; }
        hsize_t dims[2] = {0, 0};
        sp.getSimpleExtentDims(dims, NULL);
        if (dims[0] != (hsize_t)NX || dims[1] != (hsize_t)NY) {
            std::printf("FAIL 形状 %llu x %llu != %d x %d\n",
                        (unsigned long long)dims[0], (unsigned long long)dims[1], NX, NY);
            return 1;
        }
        ds.read(rbuf, H5::PredType::NATIVE_INT);
    } catch (H5::Exception &e) {
        std::printf("FAIL C++ 读取: %s\n", e.getDetailMsg().c_str());
        return 1;
    }

    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            if (rbuf[i][j] != i * 100 + j) {
                std::printf("FAIL C++ 往返 [%d][%d]=%d 期望 %d\n", i, j, rbuf[i][j], i * 100 + j);
                return 1;
            }
    std::printf("C++ API 往返 OK: %dx%d 数据集逐元素一致\n", NX, NY);
    return 0;
}

static int test_hl_api(const char *path)
{
    /* ecell4-base 的 find_package 要 COMPONENTS C CXX HL，HL 是独立 .so，必须单独验。 */
    hid_t f = H5Fcreate(path, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    if (f < 0) { std::printf("FAIL HL H5Fcreate\n"); return 1; }

    const hsize_t dims[1] = {6};
    const double w[6] = {1.5, 2.5, 3.5, 4.5, 5.5, 6.5};
    if (H5LTmake_dataset_double(f, "/vals", 1, dims, w) < 0) {
        std::printf("FAIL H5LTmake_dataset_double\n"); H5Fclose(f); return 1;
    }
    double r[6] = {0};
    if (H5LTread_dataset_double(f, "/vals", r) < 0) {
        std::printf("FAIL H5LTread_dataset_double\n"); H5Fclose(f); return 1;
    }
    H5Fclose(f);

    for (int i = 0; i < 6; i++)
        if (r[i] != w[i]) {
            std::printf("FAIL HL 往返 [%d]=%f 期望 %f\n", i, r[i], w[i]);
            return 1;
        }
    std::printf("HL API 往返 OK: 6 个 double 逐元素一致\n");
    return 0;
}

static int test_filters(void)
{
    /* szip 是我们特意做 libaec 的理由。若这里为假，说明 libaec 没真正接进来——
     * 包照样能装、C++/HL 测试照样过，但下游读带 szip 压缩的 .h5 会失败。 */
    htri_t szip = H5Zfilter_avail(H5Z_FILTER_SZIP);
    htri_t defl = H5Zfilter_avail(H5Z_FILTER_DEFLATE);
    std::printf("过滤器: szip=%d deflate=%d\n", (int)szip, (int)defl);
    if (szip <= 0) { std::printf("FAIL szip 过滤器不可用（libaec 未接入）\n"); return 1; }
    if (defl <= 0) { std::printf("FAIL deflate 过滤器不可用（zlib 未接入）\n"); return 1; }

    /* 不止问"可用否"，真写一个 szip 压缩数据集并读回，确认过滤器能跑通。 */
    hid_t f = H5Fcreate("filt.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    if (f < 0) { std::printf("FAIL 建 filt.h5\n"); return 1; }
    const hsize_t dims[2] = {64, 32}, chunk[2] = {16, 32};
    hid_t sp = H5Screate_simple(2, dims, NULL);
    hid_t dcpl = H5Pcreate(H5P_DATASET_CREATE);
    H5Pset_chunk(dcpl, 2, chunk);
    if (H5Pset_szip(dcpl, H5_SZIP_NN_OPTION_MASK, 16) < 0) {
        std::printf("FAIL H5Pset_szip\n"); return 1;
    }
    hid_t ds = H5Dcreate2(f, "/sz", H5T_NATIVE_INT, sp, H5P_DEFAULT, dcpl, H5P_DEFAULT);
    if (ds < 0) { std::printf("FAIL 建 szip 数据集\n"); return 1; }

    static int wbuf[64][32], rbuf[64][32];
    for (int i = 0; i < 64; i++) for (int j = 0; j < 32; j++) wbuf[i][j] = i / 4;
    if (H5Dwrite(ds, H5T_NATIVE_INT, H5S_ALL, H5S_ALL, H5P_DEFAULT, wbuf) < 0) {
        std::printf("FAIL 写 szip 数据集\n"); return 1;
    }
    H5Dclose(ds); H5Pclose(dcpl); H5Sclose(sp); H5Fclose(f);

    f = H5Fopen("filt.h5", H5F_ACC_RDONLY, H5P_DEFAULT);
    ds = H5Dopen2(f, "/sz", H5P_DEFAULT);
    if (ds < 0) { std::printf("FAIL 打开 szip 数据集\n"); return 1; }
    std::memset(rbuf, 0, sizeof(rbuf));
    if (H5Dread(ds, H5T_NATIVE_INT, H5S_ALL, H5S_ALL, H5P_DEFAULT, rbuf) < 0) {
        std::printf("FAIL 读 szip 数据集\n"); return 1;
    }
    H5Dclose(ds); H5Fclose(f);
    if (std::memcmp(wbuf, rbuf, sizeof(wbuf)) != 0) {
        std::printf("FAIL szip 压缩往返数据不一致\n"); return 1;
    }
    std::printf("szip 压缩数据集往返 OK: 64x32 int 逐字节一致\n");
    return 0;
}

int main(void)
{
    if (test_cpp_api("cpp.h5")) return 1;
    if (test_hl_api("hl.h5"))   return 1;
    if (test_filters())         return 1;
    std::printf("hdf5 1.14.6: 全部断言通过\n");
    return 0;
}
