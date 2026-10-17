// HarmonyOS 专项测试 for libsavitar 4.4.1 (conan test_package).
// 调用 libsavitar 真实 API：解析最小 3MF 模型、校验场景节点与对象结构、
// 序列化往返，验证 OHOS aarch64 平台上的行为正确性（非空壳）。
#include <Savitar/ThreeMFParser.h>
#include <Savitar/Scene.h>
#include <Savitar/SceneNode.h>
#include <Savitar/MeshData.h>
#include <Savitar/Types.h>

#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool cond, const std::string& name) {
  if (cond) {
    std::cout << "[PASS] " << name << std::endl;
  } else {
    std::cout << "[FAIL] " << name << std::endl;
    ++failures;
  }
}

std::string minimal_model() {
  return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
         "<model unit=\"millimeter\" "
         "xmlns=\"http://schemas.microsoft.com/3dmanufacturing/core/2015/02\">\n"
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
}

}  // namespace

int main() {
  // 1-2: 目标平台单元（OHOS aarch64：aarch64 指令集 + LP64 数据模型）
  check(sizeof(void*) == 8, "LP64 data model");
#if defined(__aarch64__)
  check(true, "aarch64 target");
#else
  check(false, "aarch64 target");
#endif

  // 3-4: 真实解析入口——ThreeMFParser::parse 消费 3MF XML
  Savitar::ThreeMFParser parser;
  Savitar::Scene scene = parser.parse(minimal_model());
  const std::vector<Savitar::SceneNode*>& nodes = scene.getSceneNodes();
  check(!nodes.empty(), "parse produces scene nodes");

  // 5-6: 模型单位元数据（3MF <model unit="millimeter">）
  check(scene.getUnit() == "millimeter", "scene unit parsed from 3MF header");

  // 7-8: 对象结构完整（build item → scene node → mesh data）
  Savitar::SceneNode* node = nodes.empty() ? nullptr : nodes[0];
  check(node != nullptr, "first scene node exists");
  if (node) {
    Savitar::MeshData& mesh = node->getMeshData();
    check(mesh.getVerticesAsBytes().size() >= 3 * 12,
          "mesh vertex list populated (>=3 verts x 3 floats x 4B)");
  }

  // 9-10: 序列化往返——sceneToString 输出仍可被解析且含 <model
  std::string out = parser.sceneToString(scene);
  check(out.find("<model") != std::string::npos, "serialize keeps <model");
  Savitar::Scene reparsed = parser.parse(out);
  check(!reparsed.getSceneNodes().empty(), "serialize round-trip reparses");

  std::cout << (failures == 0 ? "ALL PASS" : "HAS FAILURES") << " (failures="
            << failures << ")" << std::endl;
  return failures == 0 ? 0 : 1;
}