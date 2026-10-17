#include <cstdio>
#include <cstdlib>
#include "libdxfrw.h"

/*
 * test_package 实质测试（R34/PF3）：
 * 1) 写路径：用 dxfRW::write 写出 DXF，校验返回 true 且产物非空；
 * 2) 读路径：用 dxfRW::read 解析内嵌的最小合法 DXF，校验返回 true 且回调被触发。
 */

// 最小 DRW_Interface 实现：只计数，验证读写回调真实发生
class TestInterface : public DRW_Interface {
public:
    TestInterface() : headerCount(0), readOk(0) {}
    int headerCount;
    int readOk;
    void addHeader(const DRW_Header* data) override { (void)data; headerCount++; }
    void addLType(const DRW_LType& data) override { (void)data; }
    void addLayer(const DRW_Layer& data) override { (void)data; }
    void addDimStyle(const DRW_Dimstyle& data) override { (void)data; }
    void addVport(const DRW_Vport& data) override { (void)data; }
    void addTextStyle(const DRW_Textstyle& data) override { (void)data; }
    void addBlock(const DRW_Block& data) override { (void)data; }
    void setBlock(const int handle) override { (void)handle; }
    void endBlock() override {}
    void addPoint(const DRW_Point& data) override { (void)data; }
    void addLine(const DRW_Line& data) override { (void)data; }
    void addRay(const DRW_Ray& data) override { (void)data; }
    void addXline(const DRW_Xline& data) override { (void)data; }
    void addArc(const DRW_Arc& data) override { (void)data; }
    void addCircle(const DRW_Circle& data) override { (void)data; }
    void addEllipse(const DRW_Ellipse& data) override { (void)data; }
    void addLWPolyline(const DRW_LWPolyline& data) override { (void)data; }
    void addPolyline(const DRW_Polyline& data) override { (void)data; }
    void addSpline(const DRW_Spline* data) override { (void)data; }
    void addKnot(const DRW_Entity& data) override { (void)data; }
    void addInsert(const DRW_Insert& data) override { (void)data; }
    void addTrace(const DRW_Trace& data) override { (void)data; }
    void add3dFace(const DRW_3Dface& data) override { (void)data; }
    void addSolid(const DRW_Solid& data) override { (void)data; }
    void addMText(const DRW_MText& data) override { (void)data; }
    void addText(const DRW_Text& data) override { (void)data; }
    void addDimAlign(const DRW_DimAligned *data) override { (void)data; }
    void addDimLinear(const DRW_DimLinear *data) override { (void)data; }
    void addDimRadial(const DRW_DimRadial *data) override { (void)data; }
    void addDimDiametric(const DRW_DimDiametric *data) override { (void)data; }
    void addDimAngular(const DRW_DimAngular *data) override { (void)data; }
    void addDimAngular3P(const DRW_DimAngular3p *data) override { (void)data; }
    void addDimOrdinate(const DRW_DimOrdinate *data) override { (void)data; }
    void addLeader(const DRW_Leader *data) override { (void)data; }
    void addHatch(const DRW_Hatch *data) override { (void)data; }
    void addViewport(const DRW_Viewport& data) override { (void)data; }
    void addImage(const DRW_Image *data) override { (void)data; }
    void linkImage(const DRW_ImageDef *data) override { (void)data; }
    void addComment(const char* comment) override { (void)comment; }
    void writeHeader(DRW_Header& data) override { (void)data; }
    void writeBlocks() override {}
    void writeBlockRecords() override {}
    void writeEntities() override {}
    void writeLTypes() override {}
    void writeLayers() override {}
    void writeTextstyles() override {}
    void writeVports() override {}
    void writeDimstyles() override {}
};

int main(void) {
    // ---- 写路径 ----
    const char* path = "test_libdxfrw_out.dxf";
    TestInterface wif;
    dxfRW wdxf(path);
    bool wrote = wdxf.write(&wif, DRW::AC1015, false);
    if (!wrote) {
        printf("FAIL: dxfRW::write returned false\n");
        return 1;
    }
    std::FILE* fp = std::fopen(path, "rb");
    if (!fp) {
        printf("FAIL: write output file %s not found\n", path);
        return 1;
    }
    std::fseek(fp, 0, SEEK_END);
    long sz = std::ftell(fp);
    std::fclose(fp);
    if (sz <= 0) {
        printf("FAIL: write output file %s is empty\n", path);
        return 1;
    }

    // ---- 读路径（内嵌最小合法 DXF：HEADER 段 + EOF）----
    const char* minDxf = "0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n0\nENDSEC\n0\nEOF\n";
    const char* inPath = "test_libdxfrw_in.dxf";
    fp = std::fopen(inPath, "wb");
    if (!fp) {
        printf("FAIL: cannot create input dxf\n");
        return 1;
    }
    std::fwrite(minDxf, 1, std::strlen(minDxf), fp);
    std::fclose(fp);

    TestInterface rif;
    dxfRW rdxf(inPath);
    bool read = rdxf.read(&rif, false);
    if (!read) {
        printf("FAIL: dxfRW::read returned false\n");
        return 1;
    }
    if (rif.headerCount == 0) {
        printf("FAIL: read did not invoke addHeader callback\n");
        return 1;
    }

    std::remove(path);
    std::remove(inPath);
    printf("libdxfrw 0.5.12 round-trip OK (write=%d read=%d header_cb=%d)\n",
           (int)wrote, (int)read, rif.headerCount);
    return 0;
}