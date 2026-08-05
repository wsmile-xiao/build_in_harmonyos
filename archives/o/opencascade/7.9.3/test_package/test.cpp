/* OpenCASCADE 7.9.3 真实功能断言（几何内核 + STEP 数据交换）。
 *
 * 本包**刻意只做几何内核那一半**：Visualization / Draw 与 OpenGL/GLES/X11/VTK 全关。
 * 理由是那些绑桌面图形栈（cadquery-ocp 的 wheel 里 external_needed 明确含
 * libGL.so.1 / libX11.so.6 / libvtkRenderingOpenGL2.so），在鸿蒙 PC 上不可行；
 * 而几何内核与 STEP/IGES 读写是纯可移植 C++，本身就是有用的交付。
 *
 * 断言全部**可手算**：
 *   长方体 10×20×30            体积 = 6000
 *   挖掉角上 5×5×5 立方         体积 = 6000 − 125 = 5875
 *   面数：长方体 6 面；挖角后 9 面（3 面被切出缺口各分裂，另加 3 个新面）——
 *         面数不写死，只断言「变多了」，避免因布尔实现细节产生假失败。
 *
 * STEP 往返是 DataExchange 模块真接入的判据：写出去再读回来，体积必须一致。
 *
 * 用 C++ 直接链接而非 dlopen 探针：OCCT 是 C++ 库，名字修饰让 dlsym 没有意义，
 * 且「漏装头 / 符号没导出」这类缺陷只在链接期暴露。
 */
#include <Standard_Version.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopAbs_ShapeEnum.hxx>
#include <TopoDS_Shape.hxx>
#include <gp_Pnt.hxx>
#include <STEPControl_Writer.hxx>
#include <STEPControl_Reader.hxx>
#include <IFSelect_ReturnStatus.hxx>

#include <cstdio>
#include <cmath>
#include <cstdlib>

static const double EPS = 1e-6;

static double volume_of(const TopoDS_Shape& s)
{
    GProp_GProps props;
    BRepGProp::VolumeProperties(s, props);
    return props.Mass();
}

static int count_faces(const TopoDS_Shape& s)
{
    int n = 0;
    for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next())
        n++;
    return n;
}

static int test_version()
{
    std::printf("OCCT 版本: %s（宏 %d.%d.%d）\n", OCC_VERSION_COMPLETE,
                OCC_VERSION_MAJOR, OCC_VERSION_MINOR, OCC_VERSION_MAINTENANCE);
    if (OCC_VERSION_MAJOR != 7 || OCC_VERSION_MINOR != 9 || OCC_VERSION_MAINTENANCE != 3) {
        std::printf("FAIL 版本 %d.%d.%d 不是 7.9.3\n",
                    OCC_VERSION_MAJOR, OCC_VERSION_MINOR, OCC_VERSION_MAINTENANCE);
        return 1;
    }
    return 0;
}

/* 建长方体并算体积 —— 结果是定值 6000 */
static int test_box(TopoDS_Shape& out)
{
    BRepPrimAPI_MakeBox mk(10.0, 20.0, 30.0);
    TopoDS_Shape box = mk.Shape();
    if (box.IsNull()) { std::printf("FAIL MakeBox 产出空形状\n"); return 1; }

    int nf = count_faces(box);
    if (nf != 6) { std::printf("FAIL 长方体面数 %d != 6\n", nf); return 1; }

    double v = volume_of(box);
    if (std::fabs(v - 6000.0) > EPS) {
        std::printf("FAIL 体积 %.6f != 6000\n", v); return 1;
    }
    std::printf("建模 OK: 10×20×30 长方体，6 个面，体积 %.1f\n", v);
    out = box;
    return 0;
}

/* 布尔差集 —— 挖掉角上 5×5×5，体积必须正好少 125 */
static int test_boolean(const TopoDS_Shape& box, TopoDS_Shape& out)
{
    BRepPrimAPI_MakeBox mkTool(gp_Pnt(0, 0, 0), gp_Pnt(5, 5, 5));
    TopoDS_Shape tool = mkTool.Shape();
    if (std::fabs(volume_of(tool) - 125.0) > EPS) {
        std::printf("FAIL 工具立方体体积 %.6f != 125\n", volume_of(tool)); return 1;
    }

    /* 用 HasErrors() 而**不是** IsDone()：
     * BRepAlgoAPI_Cut 的继承链是
     *   Cut → BooleanOperation → BuilderAlgo → BRepAlgoAPI_Algo
     *   BRepAlgoAPI_Algo : public BRepBuilderAPI_MakeShape, **protected** BOPAlgo_Options
     * IsDone() 只存在于 BRepBuilderAPI_Command 上，而 MakeShape 并不继承它；
     * HasErrors() 来自 BOPAlgo_Options（protected 继承），
     * 靠 BRepAlgoAPI_Algo.hxx:19 的 `using BOPAlgo_Options::HasErrors;` 才提升为 public。
     * 写成 cut.IsDone() 会直接编译失败。 */
    BRepAlgoAPI_Cut cut(box, tool);
    if (cut.HasErrors()) { std::printf("FAIL 布尔差集报错\n"); return 1; }
    TopoDS_Shape res = cut.Shape();
    if (res.IsNull()) { std::printf("FAIL 差集结果为空\n"); return 1; }

    double v = volume_of(res);
    if (std::fabs(v - 5875.0) > EPS) {
        std::printf("FAIL 差集体积 %.6f != 5875（6000-125）\n", v); return 1;
    }
    /* 挖角后面数必然多于原来的 6 —— 只断言方向，不写死具体值：
     * 具体面数取决于布尔实现的边界处理，写死会产生与正确性无关的假失败。 */
    int nf = count_faces(res);
    if (nf <= 6) {
        std::printf("FAIL 挖角后面数 %d 未增加（差集没真做）\n", nf); return 1;
    }
    std::printf("布尔差集 OK: 6000−125 = %.1f，面数 6→%d\n", v, nf);
    out = res;
    return 0;
}

/* STEP 往返 —— DataExchange 模块真接入的判据。
 * 若 TKDESTEP 没编进来，Transfer/Write 会失败或写不出文件。 */
static int test_step_roundtrip(const TopoDS_Shape& shape)
{
    const char* path = "occt_test.stp";
    double v0 = volume_of(shape);

    {
        STEPControl_Writer w;
        if (w.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone) {
            std::printf("FAIL STEP Transfer 失败 —— TKDESTEP 未接入？\n"); return 1;
        }
        if (w.Write(path) != IFSelect_RetDone) {
            std::printf("FAIL STEP Write 失败\n"); return 1;
        }
    }
    /* 文件必须真写出来且非空 —— 只看返回码抓不到「返回成功但没落盘」 */
    {
        std::FILE* f = std::fopen(path, "rb");
        if (!f) { std::printf("FAIL STEP 文件没生成\n"); return 1; }
        std::fseek(f, 0, SEEK_END);
        long sz = std::ftell(f);
        std::fclose(f);
        if (sz < 100) { std::printf("FAIL STEP 文件只有 %ld 字节\n", sz); return 1; }
        std::printf("STEP 写出 %ld 字节\n", sz);
    }

    STEPControl_Reader r;
    if (r.ReadFile(path) != IFSelect_RetDone) {
        std::printf("FAIL STEP ReadFile 失败\n"); std::remove(path); return 1;
    }
    /* TransferRoots 返回 Standard_Boolean，必须查。部分失败时 OneShape() 会给出
     * **非空但残缺**的形状：体积若恰好落在下面 1e-3 的容差内就是假通过；
     * 落在容差外则报「体积偏差」，把排查引向精度问题而非转换失败这个真因。 */
    if (!r.TransferRoots()) {
        std::printf("FAIL STEP TransferRoots 失败（根实体未能转换为 OCCT 形状）\n");
        std::remove(path); return 1;
    }
    TopoDS_Shape back = r.OneShape();
    if (back.IsNull()) { std::printf("FAIL STEP 读回空形状\n"); std::remove(path); return 1; }

    double v1 = volume_of(back);
    std::remove(path);
    /* STEP 是精确 B-rep 表示，往返后体积应几乎不变；给 1e-3 的相对容差
     * 容纳文本格式的浮点round-trip，而不是掩盖真实误差。 */
    if (std::fabs(v1 - v0) / v0 > 1e-3) {
        std::printf("FAIL STEP 往返体积 %.6f vs 原 %.6f，相对偏差过大\n", v1, v0);
        return 1;
    }
    std::printf("STEP 往返 OK: 体积 %.4f → %.4f —— TKDESTEP 已接入\n", v0, v1);
    return 0;
}

int main()
{
    TopoDS_Shape box, cut;
    if (test_version())            return 1;
    if (test_box(box))             return 1;
    if (test_boolean(box, cut))    return 1;
    if (test_step_roundtrip(cut))  return 1;
    std::printf("opencascade 7.9.3: 全部断言通过\n");
    return 0;
}
