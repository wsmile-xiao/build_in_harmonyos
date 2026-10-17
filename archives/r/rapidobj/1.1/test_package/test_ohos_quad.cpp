#include "rapidobj/rapidobj.hpp"

#include <iostream>
#include <sstream>
#include <string>

// HarmonyOS 专项测试：验证 rapidobj 在 OHOS aarch64 平台默认构建下的
// quad 三角化几何等价性（本轮返工根因：sponza-triangulated 参考文件
// 索引差异源于 quad 对角线选择的 FMA 浮点收缩，见 reports/sponza-diag-r02.log）。
//
// 断言口径（与本轮根因判定一致）：Triangulate 前后属性数据必须逐位一致；
// 每个 quad 面必须恰好展开为 2 个三角形（6 个索引槽），面顶点数全部为 3；
// 不要求对角线选择与 x86 预生成参考文件逐位相同（两条对角线在几何上都合法）。

// 测试数据：一个平面 quad（4 顶点, 单面 f 1 2 3 4）+ 一个分离三角形（3 顶点）
static const char* kQuadObj = R"(o quad_patch

v  0.0  0.0  0.0
v  1.0  0.0  0.0
v  1.0  1.0  0.0
v  0.0  1.0  0.0
v  2.0  2.0  0.0
v  3.0  2.0  0.0
v  2.5  3.0  0.0

vt 0.0 0.0
vt 1.0 0.0
vt 0.0 1.0
vt 1.0 1.0
vt 0.5 0.5

f  1/1 2/2 3/3 4/4
f  5/5 6/5 7/5
)";

int main()
{
    // 1) ParseStream 兼容路径
    {
        std::istringstream stream(kQuadObj);
        rapidobj::Result result = rapidobj::ParseStream(stream);

        if (result.error) {
            std::cout << "OHOS test FAIL: ParseStream error: " << result.error.code.message() << '\n';
            return 1;
        }

        // 解析后: 7 顶点 x3 = 21 位置分量; 1 quad + 1 tri = 7 个索引槽
        if (result.attributes.positions.size() != 21 || result.shapes[0].mesh.indices.size() != 7) {
            std::cout << "OHOS test FAIL: pre-triangulate sizes positions="
                      << result.attributes.positions.size() << " indices="
                      << result.shapes[0].mesh.indices.size() << '\n';
            return 1;
        }

        // 记录三角化前属性字节级快照
        std::vector<float> positions_before(result.attributes.positions.begin(),
                                            result.attributes.positions.end());
        std::vector<float> texcoords_before(result.attributes.texcoords.begin(),
                                            result.attributes.texcoords.end());

        if (!rapidobj::Triangulate(result)) {
            std::cout << "OHOS test FAIL: Triangulate returned false\n";
            return 1;
        }

        // 2) 几何等价断言（本测试核心，对应本轮 R02 根因判定）
        std::vector<float> positions_after(result.attributes.positions.begin(),
                                           result.attributes.positions.end());
        std::vector<float> texcoords_after(result.attributes.texcoords.begin(),
                                           result.attributes.texcoords.end());

        if (positions_after != positions_before) {
            std::cout << "OHOS test FAIL: positions changed by Triangulate\n";
            return 1;
        }
        if (texcoords_after != texcoords_before) {
            std::cout << "OHOS test FAIL: texcoords changed by Triangulate\n";
            return 1;
        }

        // quad(1 面) -> 2 三角形(6 索引) + tri(1 面) -> 1 三角形(3 索引) = 9 索引槽
        if (result.shapes[0].mesh.indices.size() != 9) {
            std::cout << "OHOS test FAIL: post-triangulate indices="
                      << result.shapes[0].mesh.indices.size() << " expected 9\n";
            return 1;
        }
        for (auto nv : result.shapes[0].mesh.num_face_vertices) {
            if (nv != 3) {
                std::cout << "OHOS test FAIL: non-triangle face after triangulate nv="
                          << static_cast<int>(nv) << '\n';
                return 1;
            }
        }
        // 索引必须落在合法顶点范围 [0, 6]
        for (const auto& idx : result.shapes[0].mesh.indices) {
            if (idx.position_index < 0 || idx.position_index >= 7) {
                std::cout << "OHOS test FAIL: out-of-range position_index="
                          << idx.position_index << '\n';
                return 1;
            }
        }

        std::cout << "OHOS ParseStream+Triangulate OK: positions="
                  << result.attributes.positions.size() << " indices="
                  << result.shapes[0].mesh.indices.size()
                  << " faces=" << result.shapes[0].mesh.num_face_vertices.size() << '\n';
    }

    // 3) ParseFile 兼容路径（写入临时文件再读回，验证真实文件 I/O 路径）
    {
        const std::string tmpfile = "ohos_quad_tmp.obj";
        {
            std::ofstream ofs(tmpfile);
            ofs << kQuadObj;
        }
        rapidobj::Result result = rapidobj::ParseFile(tmpfile);
        std::remove(tmpfile.c_str());

        if (result.error) {
            std::cout << "OHOS test FAIL: ParseFile error: " << result.error.code.message() << '\n';
            return 1;
        }
        if (result.attributes.positions.size() != 21) {
            std::cout << "OHOS test FAIL: ParseFile positions="
                      << result.attributes.positions.size() << '\n';
            return 1;
        }
        std::cout << "OHOS ParseFile OK: positions=" << result.attributes.positions.size()
                  << " indices=" << result.shapes[0].mesh.indices.size() << '\n';
    }

    std::cout << "rapidobj 1.1 HarmonyOS quad-triangulation test OK\n";
    return 0;
}