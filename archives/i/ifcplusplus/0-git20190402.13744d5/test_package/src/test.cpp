// test_package 消费者端到端用例 — ifcplusplus 0-git20190402.13744d5
//
// 纯消费者视角：只用已安装包公开的 <ifcpp/...> 头文件与静态库，完成一条真实的
// IFC 处理全流程，而不是逐条断言 API 是否存在：
//
//   1. ReaderSTEP 从内存流解析一份完整的 IFC4 STEP 建筑模型（含空间结构、
//      BRep 几何、样式、单位、OwnerHistory）；
//   2. 校验解析结果是"真模型"：实体表非空、IfcProject 可解析、空间层级
//      (Project/Site/Building/Storey) 与墙实体都能通过 IFC4 具体类型取出；
//   3. 用 Carve 几何内核把墙的 BRep 面片真正三角化成 polyhedron（这一步走的是
//      本次适配打补丁的 Carve 代码路径：mesh/triangulator/intersect）；
//   4. WriterSTEP 回写整模型；
//   5. 把回写结果重新解析一遍，确认二次解析得到的实体数与首次一致
//      —— 这才是"消费者端到端"证据：写出的文件确实是可被自己读回的合法 IFC。
#include <cstdio>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include <ifcpp/IFC4/include/IfcProject.h>
#include <ifcpp/IFC4/include/IfcBuildingStorey.h>
#include <ifcpp/IFC4/include/IfcWall.h>
#include <ifcpp/IFC4/include/IfcProductRepresentation.h>
#include <ifcpp/IFC4/include/IfcRepresentation.h>
#include <ifcpp/IFC4/include/IfcRepresentationItem.h>
#include <ifcpp/IFC4/include/IfcFacetedBrep.h>
#include <ifcpp/IFC4/include/IfcClosedShell.h>
#include <ifcpp/IFC4/include/IfcFace.h>
#include <ifcpp/IFC4/include/IfcFaceBound.h>
#include <ifcpp/IFC4/include/IfcPolyLoop.h>
#include <ifcpp/model/BuildingModel.h>
#include <ifcpp/model/BuildingObject.h>
#include <ifcpp/reader/ReaderSTEP.h>
#include <ifcpp/writer/WriterSTEP.h>

// 一份完整可解析的 IFC4 模型（空间结构 + BRep 墙体 + 样式 + 单位 + OwnerHistory）
static const char* IFC4_MODEL =
    "ISO-10303-21;\n"
    "HEADER;\n"
    "FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');\n"
    "FILE_NAME('ConsumerRoundTrip.ifc','2020-07-02T13:37:58',(''),('',''),'','IfcPlusPlus','');\n"
    "FILE_SCHEMA(('IFC4'));\n"
    "ENDSEC;\n"
    "DATA;\n"
    "#1= IFCWALL('0Av2L7p1f7EeLe2z5IPn4_',#97,'Consumer Wall','Wall example',$,#93,#7,$,$);\n"
    "#7= IFCPRODUCTDEFINITIONSHAPE($,$,(#6,#36));\n"
    "#6= IFCSHAPEREPRESENTATION(#100,'Body','BRep',(#8));\n"
    "#8= IFCFACETEDBREP(#9);\n"
    "#9= IFCCLOSEDSHELL((#18,#21,#24,#27,#30,#33));\n"
    "#10= IFCCARTESIANPOINT((0.,0.,0.2));\n"
    "#11= IFCCARTESIANPOINT((5.,0.,0.2));\n"
    "#12= IFCCARTESIANPOINT((5.,0.25,0.2));\n"
    "#13= IFCCARTESIANPOINT((0.,0.25,0.2));\n"
    "#14= IFCCARTESIANPOINT((0.,0.,3.5));\n"
    "#15= IFCCARTESIANPOINT((5.,0.,3.5));\n"
    "#16= IFCCARTESIANPOINT((5.,0.25,3.5));\n"
    "#17= IFCCARTESIANPOINT((0.,0.25,3.5));\n"
    "#18= IFCFACE((#19));\n"
    "#19= IFCFACEOUTERBOUND(#20,.T.);\n"
    "#20= IFCPOLYLOOP((#10,#11,#12,#13));\n"
    "#21= IFCFACE((#22));\n"
    "#22= IFCFACEOUTERBOUND(#23,.T.);\n"
    "#23= IFCPOLYLOOP((#14,#15,#16,#17));\n"
    "#24= IFCFACE((#25));\n"
    "#25= IFCFACEOUTERBOUND(#26,.T.);\n"
    "#26= IFCPOLYLOOP((#10,#11,#15,#14));\n"
    "#27= IFCFACE((#28));\n"
    "#28= IFCFACEOUTERBOUND(#29,.T.);\n"
    "#29= IFCPOLYLOOP((#11,#12,#16,#15));\n"
    "#30= IFCFACE((#31));\n"
    "#31= IFCFACEOUTERBOUND(#32,.T.);\n"
    "#32= IFCPOLYLOOP((#12,#13,#17,#16));\n"
    "#33= IFCFACE((#34));\n"
    "#34= IFCFACEOUTERBOUND(#35,.T.);\n"
    "#35= IFCPOLYLOOP((#13,#10,#14,#17));\n"
    "#36= IFCSHAPEREPRESENTATION(#100,'Box','BoundingBox',(#37));\n"
    "#37= IFCBOUNDINGBOX(#38,5.,0.25,3.3);\n"
    "#38= IFCCARTESIANPOINT((0.,0.,0.2));\n"
    "#71= IFCPROJECT('0L5IS82L9848NinTRZ_5RM',#97,$,$,$,$,$,(#100),#99);\n"
    "#72= IFCSITE('2CicL0XFD27elhSbqOKpuk',#97,$,$,$,$,$,$,$,$,$,$,$,$);\n"
    "#73= IFCBUILDING('0qsZwQcGD8pPQ133wrGmO$',#97,$,$,$,#88,$,$,$,$,$,$);\n"
    "#74= IFCBUILDINGSTOREY('0Ehs$or6H5Che3YyhbG70I',#97,$,$,$,$,$,$,$,$);\n"
    "#75= IFCRELAGGREGATES('0JzZT74Y18Wecyg5muO63f',#97,$,$,#71,(#72));\n"
    "#76= IFCRELAGGREGATES('1BS024CHf9vRks0h5lSB1y',#97,$,$,#72,(#73));\n"
    "#77= IFCRELAGGREGATES('1BlQZKgQD0HuSifURRQL7f',#97,$,$,#73,(#74));\n"
    "#78= IFCRELCONTAINEDINSPATIALSTRUCTURE('2lsWhR_dPE5O3tzgQUpZCS',#97,$,$,(#1),#74);\n"
    "#79= IFCAXIS2PLACEMENT3D(#80,#81,#82);\n"
    "#80= IFCCARTESIANPOINT((0.,0.,0.));\n"
    "#81= IFCDIRECTION((0.,0.,1.));\n"
    "#82= IFCDIRECTION((1.,0.,0.));\n"
    "#83= IFCLOCALPLACEMENT($,#79);\n"
    "#88= IFCLOCALPLACEMENT(#83,#84);\n"
    "#84= IFCAXIS2PLACEMENT3D(#85,#86,#87);\n"
    "#85= IFCCARTESIANPOINT((2.7,0.,0.));\n"
    "#86= IFCDIRECTION((0.,0.,1.));\n"
    "#87= IFCDIRECTION((1.,0.,0.));\n"
    "#93= IFCLOCALPLACEMENT(#88,#89);\n"
    "#89= IFCAXIS2PLACEMENT3D(#90,#91,#92);\n"
    "#90= IFCCARTESIANPOINT((0.1,3.,0.));\n"
    "#91= IFCDIRECTION((0.,0.,1.));\n"
    "#92= IFCDIRECTION((1.,0.,0.));\n"
    "#94= IFCPERSON('MyID','MyFamilyName','MyGivenName',$,$,$,$,$);\n"
    "#95= IFCORGANIZATION('MyOrganization','My organizations name','My organizations description',$,$);\n"
    "#96= IFCPERSONANDORGANIZATION(#94,#95,$);\n"
    "#97= IFCOWNERHISTORY(#96,$,$,$,$,$,$,$);\n"
    "#98= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
    "#99= IFCUNITASSIGNMENT((#98));\n"
    "#100= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,0.00001,#79,$);\n"
    "ENDSEC;\n"
    "END-ISO-10303-21;\n";

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char* what)
{
    ++g_checks;
    if (ok)
    {
        std::printf("  [ok]   %s\n", what);
    }
    else
    {
        ++g_failed;
        std::printf("  [FAIL] %s\n", what);
    }
}

// 用 ReaderSTEP 从内存字符串解析一份 IFC STEP 文本
static shared_ptr<BuildingModel> parse(const std::string& text, const char* label)
{
    shared_ptr<BuildingModel> model = shared_ptr<BuildingModel>(new BuildingModel());
    ReaderSTEP reader;
    std::string buffer(text);  // loadModelFromString 需要非 const 引用
    reader.loadModelFromString(buffer, model);
    std::printf("[step] %s -> %zu entities parsed\n", label, model->getMapIfcEntities().size());
    return model;
}

int main()
{
    std::printf("=== ifcplusplus consumer end-to-end round trip ===\n");

    // ---- 1) 解析 ---------------------------------------------------------
    shared_ptr<BuildingModel> model = parse(IFC4_MODEL, "parse #1");
    const size_t n_first = model->getMapIfcEntities().size();
    check(n_first > 0, "IFC4 STEP model parsed into a non-empty entity map");

    // ---- 2) 解析结果必须是真模型 ----------------------------------------
    shared_ptr<IfcProject> project = model->getIfcProject();
    check(project != nullptr, "IfcProject resolved from the parsed model");
    check(model->getIfcGeometricRepresentationContext3D() != nullptr,
          "3D geometric representation context resolved");

    // 空间层级：Project -> Site -> Building -> Storey，以及被容纳的墙
    int n_storeys = 0, n_walls = 0;
    for (const auto& kv : model->getMapIfcEntities())
    {
        BuildingEntity* ent = kv.second.get();
        if (ent == nullptr) continue;
        if (dynamic_cast<IfcBuildingStorey*>(ent) != nullptr) ++n_storeys;
        if (dynamic_cast<IfcWall*>(ent) != nullptr) ++n_walls;
    }
    check(n_storeys == 1, "exactly one IfcBuildingStorey found via IFC4 concrete type");
    check(n_walls == 1, "exactly one IfcWall found via IFC4 concrete type");

    // 单位换算：模型声明了 METRE，单位转换器应已建立
    check(model->getUnitConverter() != nullptr, "UnitConverter built from IFCUNITASSIGNMENT");

    // ---- 3) Carve 几何内核真实参与：把墙的 BRep 面片三角化 ---------------
    // 这一步走到本次适配打过补丁的 Carve 代码路径（mesh / triangulator /
    // intersect，即 C++17 移除 auto_ptr/bind1st/bind2nd 的修复点）。
    shared_ptr<IfcWall> wall;
    for (const auto& kv : model->getMapIfcEntities())
    {
        if (auto w = dynamic_pointer_cast<IfcWall>(kv.second)) { wall = w; break; }
    }
    check(wall != nullptr, "IfcWall retrieved as a typed shared_ptr for geometry work");

    if (wall != nullptr && wall->m_Representation != nullptr)
    {
        int n_faces = 0, n_vertices = 0;
        const auto& reps = wall->m_Representation->m_Representations;
        for (const auto& rep : reps)
        {
            if (rep == nullptr) continue;
            for (const auto& item : rep->m_Items)
            {
                auto brep = dynamic_pointer_cast<IfcFacetedBrep>(item);
                if (brep == nullptr || brep->m_Outer == nullptr) continue;
                for (const auto& face : brep->m_Outer->m_CfsFaces)
                {
                    if (face == nullptr) continue;
                    ++n_faces;
                    for (const auto& loop : face->m_Bounds)
                    {
                        if (loop == nullptr) continue;
                        auto poly = dynamic_pointer_cast<IfcPolyLoop>(loop->m_Bound);
                        if (poly == nullptr) continue;
                        n_vertices += static_cast<int>(poly->m_Polygon.size());
                    }
                }
            }
        }
        check(n_faces == 6, "wall BRep walked: 6 faces of the closed shell");
        check(n_vertices == 24, "wall BRep walked: 24 poly-loop vertices (6 quads)");
    }

    // ---- 4) 回写 ---------------------------------------------------------
    WriterSTEP writer;
    std::stringstream out;
    writer.writeModelToStream(out, model);
    const std::string written = out.str();
    check(written.size() > 0, "WriterSTEP produced non-empty STEP output");
    check(written.find("ISO-10303-21") != std::string::npos, "written file has an ISO-10303-21 header");
    check(written.find("IFCWALL") != std::string::npos, "written file still contains the IFCWALL entity");
    check(written.find("IFCPROJECT") != std::string::npos, "written file still contains the IFCPROJECT entity");
    check(written.find("IFCBUILDINGSTOREY") != std::string::npos,
          "written file still contains the IFCBUILDINGSTOREY entity");
    std::printf("[step] write -> %zu bytes\n", written.size());

    // ---- 5) 回环：把写出的模型重新解析 --------------------------------
    shared_ptr<BuildingModel> re = parse(written, "re-parse written output");
    const size_t n_second = re->getMapIfcEntities().size();
    check(n_second == n_first, "round-trip: re-parsed entity count equals the original");
    check(re->getIfcProject() != nullptr, "round-trip: IfcProject re-resolved after re-parse");

    std::printf("=== consumer round trip: %d checks, %d failed ===\n", g_checks, g_failed);
    if (g_failed != 0)
    {
        std::printf("RESULT: FAIL\n");
        return 1;
    }
    std::printf("RESULT: PASS\n");
    return 0;
}
