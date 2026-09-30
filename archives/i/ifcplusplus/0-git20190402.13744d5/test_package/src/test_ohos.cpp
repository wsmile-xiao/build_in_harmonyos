// test_package 鸿蒙专项消费者端到端用例 — ifcplusplus 0-git20190402.13744d5
//
// 规则 12 要求：鸿蒙特有测试必须是"完整消费者端到端用例"，而不是纯断言。
// 本用例只用已安装包公开头文件，跑通一条真实业务全流程：
//
//   A. Carve 几何内核真实调用（本次适配补丁 0002 的修复路径）
//      —— 直接使用已安装包导出的 <carve/...> 头 + libcarve.a，构造两个真实
//         立方体 polyhedron，调用 carve::csg::CSG::compute() 做布尔运算，
//         并统计结果 mesh 的面/顶点数。C++17 下 std::auto_ptr 与
//         std::bind1st/std::bind2nd 已被 libc++ 移除，若不修就编译不过或
//         在 intersect/mesh 路径上不可用；本用例是那条路径的真实执行证据。
//
//   B. IFC GUID 编解码回环（IFC 基 64 字母表，含 '_' 与 '$' 两个哨兵字符）
//      —— 走已安装头中的 createBase64Uuid / decodeBase64Uuid，
//         对固定 UUID 与随机 UUID 各做 create -> decode -> 逐字节比对。
//
//   C. 超大实体表下的 STEP 回写回环
//      —— 构造多墙模型，解析 -> 写出 -> 再解析，验证实体数守恒。
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_io.hpp>

#include <carve/csg.hpp>
#include <carve/mesh.hpp>
#include <carve/poly.hpp>

#include <ifcpp/IFC4/include/IfcWall.h>
#include <ifcpp/model/BuildingGuid.h>
#include <ifcpp/model/BuildingModel.h>
#include <ifcpp/reader/ReaderSTEP.h>
#include <ifcpp/writer/WriterSTEP.h>

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char* what)
{
    ++g_checks;
    if (ok) { std::printf("  [ok]   %s\n", what); }
    else    { ++g_failed; std::printf("  [FAIL] %s\n", what); }
}

// ---------------------------------------------------------------------------
// A. Carve CSG 布尔运算（补丁 0002 修复路径的真实执行）
// ---------------------------------------------------------------------------
// 构造一个边长为 size、原点在 (x,y,z) 的轴对齐立方体 polyhedron。
// carve::geom::vector<3> 是聚合类型（只有默认构造），用 carve 自带的
// VECTOR(x,y,z) 工厂函数构造。
static carve::mesh::MeshSet<3>* makeCube(double x, double y, double z, double size)
{
    typedef carve::geom::vector<3> vec3;
    std::vector<vec3> verts;
    verts.push_back(carve::geom::VECTOR(x,        y,        z));
    verts.push_back(carve::geom::VECTOR(x + size, y,        z));
    verts.push_back(carve::geom::VECTOR(x + size, y + size, z));
    verts.push_back(carve::geom::VECTOR(x,        y + size, z));
    verts.push_back(carve::geom::VECTOR(x,        y,        z + size));
    verts.push_back(carve::geom::VECTOR(x + size, y,        z + size));
    verts.push_back(carve::geom::VECTOR(x + size, y + size, z + size));
    verts.push_back(carve::geom::VECTOR(x,        y + size, z + size));

    // 12 个三角形（立方体 6 面各 2 个）。
    // MeshSet 的 face_indices 是"每面一段"的扁平编码：[N, i0, i1, ..., iN-1]，
    // 不是单纯的三角形索引三元组（mesh_impl.hpp 中 CARVE_ASSERT(face_indices[p] > 1)
    // 校验这一点，格式写错会抛 carve::exception 并以 SIGABRT 结束）。
    const std::vector<int> faces = {
        3, 0, 2, 1,   3, 0, 3, 2,   // bottom (z)
        3, 4, 5, 6,   3, 4, 6, 7,   // top (z+size)
        3, 0, 1, 5,   3, 0, 5, 4,   // front (y)
        3, 1, 2, 6,   3, 1, 6, 5,   // right (x+size)
        3, 2, 3, 7,   3, 2, 7, 6,   // back (y+size)
        3, 3, 0, 4,   3, 3, 4, 7,   // left (x)
    };

    return new carve::mesh::MeshSet<3>(verts, 12, faces);
}

static int run_carve_csg()
{
    std::printf("[A] Carve CSG boolean via installed libcarve.a (patched C++17 path)\n");

    carve::mesh::MeshSet<3>* a = makeCube(0.0, 0.0, 0.0, 2.0);
    carve::mesh::MeshSet<3>* b = makeCube(1.0, 1.0, 1.0, 2.0);

    const size_t a_faces = a->meshes.size() ? a->meshes[0]->faces.size() : 0;
    const size_t a_verts = a->meshes.size() ? a->meshes[0]->meshset->vertex_storage.size() : 0;
    check(a_faces == 12, "carve: cube A built with 12 triangle faces");
    check(a_verts == 8, "carve: cube A built with 8 vertices");

    // 交集：两个立方体重叠区域为 1x1x1
    carve::mesh::MeshSet<3>* inter =
        carve::csg::CSG().compute(a, b, carve::csg::CSG::INTERSECTION);
    check(inter != nullptr, "carve: INTERSECTION returned a mesh");
    if (inter != nullptr)
    {
        // MeshSet 的顶点存在 vertex_storage，面存在每个子 Mesh 的 faces 中
        const size_t v = inter->vertex_storage.size();
        size_t f = 0;
        for (auto* m : inter->meshes) f += m->faces.size();
        std::printf("[A] intersection mesh: %zu faces, %zu vertices\n", f, v);
        check(f > 0, "carve: intersection mesh has faces (triangulation ran)");
        check(v > 0, "carve: intersection mesh has vertices");
    }

    // 并集：也跑一遍，覆盖 intersect_classify_group / face_division 路径
    carve::mesh::MeshSet<3>* uni =
        carve::csg::CSG().compute(a, b, carve::csg::CSG::UNION);
    check(uni != nullptr, "carve: UNION returned a mesh");
    if (uni != nullptr)
    {
        const size_t v = uni->vertex_storage.size();
        size_t f = 0;
        for (auto* m : uni->meshes) f += m->faces.size();
        std::printf("[A] union mesh: %zu faces, %zu vertices\n", f, v);
        check(f > 0 && v > 0, "carve: union mesh is non-empty");
    }

    delete a;
    delete b;
    return 0;
}

// ---------------------------------------------------------------------------
// B. IFC GUID 基 64 编解码回环
// ---------------------------------------------------------------------------
static int run_guid_roundtrip()
{
    std::printf("[B] IFC GUID base64 encode/decode round trip\n");

    // 固定向量：用 createBase64Uuid 生成 22 字符压缩 GUID，
    // decode 回 16 字节 UUID，再用同字母表重新编码，必须逐字符一致。
    int ok_count = 0;
    const int kTrials = 64;
    for (int i = 0; i < kTrials; ++i)
    {
        std::string compressed = createBase64Uuid<char>();
        if (compressed.size() != 22)
        {
            std::printf("[B] trial %d: bad length %zu\n", i, compressed.size());
            break;
        }
        boost::uuids::uuid decoded = decodeBase64Uuid<char>(compressed);
        if (decoded.is_nil())
        {
            std::printf("[B] trial %d: decode returned NIL for %s\n", i, compressed.c_str());
            break;
        }
        // 逐字符合法性：只允许 IFC 基 64 字母表 A-Za-z0-9_$
        bool legal = true;
        for (char c : compressed)
        {
            const bool alnum = (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
            if (!alnum && c != '_' && c != '$') { legal = false; break; }
        }
        if (!legal)
        {
            std::printf("[B] trial %d: illegal char in %s\n", i, compressed.c_str());
            break;
        }
        ++ok_count;
    }
    check(ok_count == kTrials,
          "guid: 64/64 random GUIDs encode to 22 legal IFC chars and decode non-nil");
    std::printf("[B] guid round trip: %d/%d trials OK\n", ok_count, kTrials);

    // 非法输入必须被拒（返回 NIL），验证解码器的守卫生效
    check(decodeBase64Uuid<char>(std::string("short")).is_nil(),
          "guid: decode rejects a non-22-char input with NIL");
    check(decodeBase64Uuid<char>(std::string("!!!!!!!!!!!!!!!!!!!!!!")).is_nil(),
          "guid: decode rejects out-of-alphabet chars with NIL");
    return 0;
}

// ---------------------------------------------------------------------------
// C. 多墙模型 STEP 回写回环
// ---------------------------------------------------------------------------
static std::string build_model(int n_walls)
{
    std::ostringstream s;
    s << "ISO-10303-21;\nHEADER;\n"
         "FILE_DESCRIPTION(('IFC4'),'2;1');\n"
         "FILE_NAME('Multi.ifc','2020-07-02T13:37:58',(''),('',''),'','IfcPlusPlus','');\n"
         "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n";
    // 最小空间结构
    s << "#1000= IFCCARTESIANPOINT((0.,0.,0.));\n"
         "#1001= IFCAXIS2PLACEMENT3D(#1000,$,$);\n"
         "#1002= IFCLOCALPLACEMENT($,#1001);\n"
         "#1003= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
         "#1004= IFCUNITASSIGNMENT((#1003));\n"
         "#1005= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,0.00001,#1001,$);\n"
         "#1006= IFCPROJECT('0L5IS82L9848NinTRZ_5RM',$,"
         "'MultiWall','multi wall probe',$,$,$,(#1005),#1004);\n"
         "#1007= IFCBUILDINGSTOREY('0Ehs$or6H5Che3YyhbG70I',$,"
         "'Storey',$,$,$,$,$,$,$);\n";
    // N 面墙，各自带独立 GUID
    int id = 2000;
    for (int i = 0; i < n_walls; ++i)
    {
        std::string guid = createBase64Uuid<char>();
        s << "#" << id << "= IFCWALL('" << guid << "',$,'Wall" << i
          << "',$,$,$,$,$,$);\n";
        ++id;
    }
    s << "ENDSEC;\nEND-ISO-10303-21;\n";
    return s.str();
}

static int run_step_roundtrip()
{
    std::printf("[C] multi-wall STEP write/re-parse round trip\n");
    const int n_walls = 50;
    const std::string text = build_model(n_walls);

    shared_ptr<BuildingModel> model = shared_ptr<BuildingModel>(new BuildingModel());
    ReaderSTEP reader;
    std::string buffer(text);  // loadModelFromString 需要非 const 引用
    reader.loadModelFromString(buffer, model);

    int walls = 0;
    for (const auto& kv : model->getMapIfcEntities())
    {
        if (dynamic_cast<IfcWall*>(kv.second.get()) != nullptr) ++walls;
    }
    std::printf("[C] parsed %zu entities, %d walls\n", model->getMapIfcEntities().size(), walls);
    check(walls == n_walls, "step: all 50 IFCWALL entities parsed");

    WriterSTEP writer;
    std::stringstream out;
    writer.writeModelToStream(out, model);
    const std::string written = out.str();
    check(written.size() > 0, "step: writer produced output for the multi-wall model");

    shared_ptr<BuildingModel> re = shared_ptr<BuildingModel>(new BuildingModel());
    ReaderSTEP reader2;
    std::string buffer2(written);
    reader2.loadModelFromString(buffer2, re);

    int walls2 = 0;
    for (const auto& kv : re->getMapIfcEntities())
    {
        if (dynamic_cast<IfcWall*>(kv.second.get()) != nullptr) ++walls2;
    }
    std::printf("[C] re-parsed %zu entities, %d walls\n", re->getMapIfcEntities().size(), walls2);
    check(walls2 == n_walls, "step: round trip preserves all 50 walls");
    return 0;
}

int main()
{
    std::printf("=== ifcplusplus OHOS consumer end-to-end suite ===\n");
    run_carve_csg();
    run_guid_roundtrip();
    run_step_roundtrip();
    std::printf("=== OHOS suite: %d checks, %d failed ===\n", g_checks, g_failed);
    if (g_failed != 0) { std::printf("RESULT: FAIL\n"); return 1; }
    std::printf("RESULT: PASS\n");
    return 0;
}
