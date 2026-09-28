// test_package — 消费者视角验证：实际调用 libSavitar 公开 API
// 使用 Savitar::ThreeMFParser 解析最小 3MF 模型字符串，验证解析与序列化闭环。
#include <Savitar/ThreeMFParser.h>
#include <Savitar/Scene.h>
#include <Savitar/SceneNode.h>
#include <Savitar/Types.h>

#include <iostream>
#include <string>
#include <vector>

int main() {
    // 最小 3MF 模型 XML（3D/3dmodel.model 内容），对应上游 tests/test_model.xml 结构
    const std::string model_xml =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<model unit=\"millimeter\" xmlns=\"http://schemas.microsoft.com/3dmanufacturing/core/2015/02\">\n"
        "  <resources>\n"
        "    <object id=\"1\" type=\"model\">\n"
        "      <mesh>\n"
        "        <vertices>\n"
        "          <vertex x=\"0\" y=\"0\" z=\"0\"/>\n"
        "          <vertex x=\"10\" y=\"0\" z=\"0\"/>\n"
        "          <vertex x=\"0\" y=\"10\" z=\"0\"/>\n"
        "        </vertices>\n"
        "        <triangles>\n"
        "          <triangle v1=\"0\" v2=\"1\" v3=\"2\"/>\n"
        "        </triangles>\n"
        "      </mesh>\n"
        "    </object>\n"
        "  </resources>\n"
        "  <build>\n"
        "    <item objectid=\"1\"/>\n"
        "  </build>\n"
        "</model>\n";

    Savitar::ThreeMFParser parser;
    Savitar::Scene scene = parser.parse(model_xml);  // 实际调用库 API
    const std::vector<Savitar::SceneNode*>& nodes = scene.getSceneNodes();
    if (nodes.empty()) {
        std::cerr << "FAIL: scene has no scene nodes\n";
        return 1;
    }
    std::cout << "parse OK, scene nodes=" << nodes.size() << "\n";

    std::string out = parser.sceneToString(scene);  // 序列化闭环
    if (out.find("<model") == std::string::npos) {
        std::cerr << "FAIL: serialized output missing <model\n";
        return 1;
    }
    std::cout << "serialize OK\n";
    return 0;
}