/* lib3mf 1.8.1 —— 真实 3MF 模型往返测试（建模型 → 写文件 → 读回 → 校验）。
 *
 * 覆盖链路：lib3mf_createmodel → addmeshobject → addvertex/addtriangle →
 * addbuilditem → querywriter("3mf") → writetofileutf8 → 新模型 queryreader →
 * readfromfileutf8 → getvertexcount/gettrianglecount 逐项校验。
 * 这条链触发：UUID 生成（ossp-uuid 桥接）、zip 压缩写（libzip+zlib）、
 * XML 序列化、OPC 包结构——四层依赖全走真，桩实现过不了。
 *
 * 注意临时文件建在 CWD —— HarmonyOS 沙箱下 /tmp 不可写。
 */
#include "Model/COM/NMR_DLLInterfaces.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

typedef NMR::PLib3MFModel *PModel;
typedef NMR::PLib3MFModelMeshObject *PMesh;
typedef NMR::PLib3MFModelWriter *PWriter;
typedef NMR::PLib3MFModelReader *PReader;

static int write_model(const char *path, int nv, int nt)
{
    PModel model = NULL;
    PMesh mesh = NULL;
    PWriter writer = NULL;

    CHECK(NMR::lib3mf_createmodel(&model) == LIB3MF_OK, "lib3mf_createmodel 成功");
    if (!model) return 1;
    CHECK(NMR::lib3mf_model_addmeshobject(model, &mesh) == LIB3MF_OK, "addmeshobject 成功");
    if (!mesh) { NMR::lib3mf_release(model); return 1; }

    for (int i = 0; i < nv; i++) {
        NMR::MODELMESHVERTEX v;
        v.m_fPosition[0] = (float)i;
        v.m_fPosition[1] = (float)(i + 1);
        v.m_fPosition[2] = (float)(i + 2);
        DWORD idx = 0;
        CHECK(NMR::lib3mf_meshobject_addvertex(mesh, &v, &idx) == LIB3MF_OK, "addvertex 成功");
    }
    for (int i = 0; i < nt; i++) {
        NMR::MODELMESHTRIANGLE t;
        t.m_nIndices[0] = (DWORD)(i % nv);
        t.m_nIndices[1] = (DWORD)((i + 1) % nv);
        t.m_nIndices[2] = (DWORD)((i + 2) % nv);
        DWORD idx = 0;
        CHECK(NMR::lib3mf_meshobject_addtriangle(mesh, &t, &idx) == LIB3MF_OK, "addtriangle 成功");
    }
    {
        NMR::PLib3MFModelBuildItem *item = NULL;
        CHECK(NMR::lib3mf_model_addbuilditem(model, mesh, NULL, &item) == LIB3MF_OK, "addbuilditem 成功");
        if (item) NMR::lib3mf_release(item);
    }

    CHECK(NMR::lib3mf_model_querywriter(model, "3mf", &writer) == LIB3MF_OK, "querywriter(3mf) 成功");
    if (!writer) { NMR::lib3mf_release(mesh); NMR::lib3mf_release(model); return 1; }
    CHECK(NMR::lib3mf_writer_writetofileutf8(writer, path) == LIB3MF_OK, "writetofileutf8 写盘成功");

    NMR::lib3mf_release(writer);
    NMR::lib3mf_release(mesh);
    NMR::lib3mf_release(model);
    return 0;
}

static int read_back(const char *path, int expect_v, int expect_t)
{
    PModel model = NULL;
    PReader reader = NULL;
    NMR::PLib3MFModelResourceIterator *it = NULL;

    CHECK(NMR::lib3mf_createmodel(&model) == LIB3MF_OK, "读回 createmodel 成功");
    if (!model) return 1;
    CHECK(NMR::lib3mf_model_queryreader(model, "3mf", &reader) == LIB3MF_OK, "queryreader(3mf) 成功");
    if (!reader) { NMR::lib3mf_release(model); return 1; }
    CHECK(NMR::lib3mf_reader_readfromfileutf8(reader, path) == LIB3MF_OK, "readfromfileutf8 读回成功");
    NMR::lib3mf_release(reader);

    DWORD count = 0;
    CHECK(NMR::lib3mf_model_getmeshobjects(model, &it) == LIB3MF_OK, "getmeshobjects 成功");
    if (it) {
        BOOL hasNext = 0;
        NMR::lib3mf_resourceiterator_movenext(it, &hasNext);
        CHECK(hasNext, "迭代器有 mesh 资源");
        if (hasNext) {
            NMR::PLib3MFModelResource *res = NULL;
            PMesh mesh = NULL;
            DWORD rid = 0;
            NMR::lib3mf_resourceiterator_getcurrent(it, &res);
            CHECK(NMR::lib3mf_resource_getresourceid(res, &rid) == LIB3MF_OK, "getresourceid 成功");
            CHECK(NMR::lib3mf_model_getmeshobjectbyid(model, rid, &mesh) == LIB3MF_OK, "getmeshobjectbyid 成功");
            if (mesh) {
                DWORD vc = 0, tc = 0;
                CHECK(NMR::lib3mf_meshobject_getvertexcount(mesh, &vc) == LIB3MF_OK, "getvertexcount 成功");
                CHECK((int)vc == expect_v, "顶点数与写入一致");
                CHECK(NMR::lib3mf_meshobject_gettrianglecount(mesh, &tc) == LIB3MF_OK, "gettrianglecount 成功");
                CHECK((int)tc == expect_t, "三角形数与写入一致");
                NMR::lib3mf_release(mesh);
            }
        }
        NMR::lib3mf_release(it);
    }
    NMR::lib3mf_release(model);
    return 0;
}

int main(void)
{
    const char *path = "./_lib3mf_probe.3mf";
    const int NV = 8, NT = 12;   /* 立方体规模的顶点/三角形 */
    unlink(path);

    if (write_model(path, NV, NT) != 0) { fprintf(stderr, "写阶段失败\n"); return 1; }
    if (read_back(path, NV, NT) != 0) { fprintf(stderr, "读阶段失败\n"); return 1; }
    unlink(path);

    if (failures) { fprintf(stderr, "\nlib3mf: %d 项断言失败\n", failures); return 1; }
    printf("\nlib3mf 1.8.1: 全部断言通过（模型建 → 3MF 写盘 → 读回校验）\n");
    return 0;
}
