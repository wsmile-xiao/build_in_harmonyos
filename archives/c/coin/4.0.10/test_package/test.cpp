// coin 4.0.10 test_package —— 纯 CPU 路径：SoDB::init + .iv 解析 + 字段断言。
// 不创建 GL 上下文、不做离屏渲染（解析/字段读写不触发渲染），避开离屏环境依赖；
// 渲染链路由上游 CoinTests 与 gl4es 栈另行验证（见 notes.md）。
// 注意：结尾不调用 SoDB::finish()——真机实证 finish() 在 gl4es 栈下析构 GL glue
// 时 SIGSEGV；不调则所有断言通过且 exit 0（静态析构自身干净）。
#include <Inventor/SoDB.h>
#include <Inventor/SoInput.h>
#include <Inventor/nodes/SoSeparator.h>
#include <Inventor/nodes/SoCone.h>
#include <Inventor/nodes/SoMaterial.h>
#include <Inventor/SbLinear.h>
#include <cstdio>
#include <cstring>

static int failures = 0;
#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

static const char *kIv = "#Inventor V2.1 ascii\n"
                         "\n"
                         "Separator {\n"
                         "  Material { diffuseColor 0.2 0.4 0.9 }\n"
                         "  Cone { bottomRadius 1.5 height 3.0 }\n"
                         "}\n";

int main() {
  SoDB::init();

  // ① 内存解析 .iv（Open Inventor 2.1 ASCII 场景）
  SoInput in;
  in.setBuffer((void *)kIv, std::strlen(kIv));
  SoSeparator *root = SoDB::readAll(&in);
  CHECK(root != nullptr, "SoDB::readAll 解析 .iv 场景成功");
  if (!root) {
    std::fprintf(stderr, "coin: 解析失败，终止\n");
    return 1;
  }
  root->ref();

  // ② 场景结构断言：Separator -> {Material, Cone}
  CHECK(root->getNumChildren() == 2, "根 Separator 子节点数 = 2");
  SoMaterial *mat = nullptr;
  SoCone *cone = nullptr;
  for (int i = 0; i < root->getNumChildren(); ++i) {
    if (!mat) mat = dynamic_cast<SoMaterial *>(root->getChild(i));
    if (!cone) cone = dynamic_cast<SoCone *>(root->getChild(i));
  }
  CHECK(mat != nullptr, "子节点含 SoMaterial");
  CHECK(cone != nullptr, "子节点含 SoCone");

  // ③ 字段值断言（证明解析出的是真实数据，不是零填充）
  if (mat) {
    const SbColor &rgb = mat->diffuseColor[0];
    CHECK(rgb[0] > 0.19f && rgb[0] < 0.21f, "Material.diffuseColor.r = 0.2");
    CHECK(rgb[1] > 0.39f && rgb[1] < 0.41f, "Material.diffuseColor.g = 0.4");
    CHECK(rgb[2] > 0.89f && rgb[2] < 0.91f, "Material.diffuseColor.b = 0.9");
  }
  if (cone) {
    CHECK(cone->bottomRadius.getValue() > 1.49f &&
              cone->bottomRadius.getValue() < 1.51f,
          "Cone.bottomRadius = 1.5");
    CHECK(cone->height.getValue() > 2.99f && cone->height.getValue() < 3.01f,
          "Cone.height = 3.0");
  }

  // ④ 字段写回（SoSFColor/SoSFFloat set 路径 + 通知机制）
  if (mat && cone) {
    mat->diffuseColor.setValue(SbColor(1.0f, 0.0f, 0.0f));
    cone->bottomRadius = 2.0f;
    const SbColor &rgb2 = mat->diffuseColor[0];
    CHECK(rgb2[0] > 0.99f, "字段写回生效 diffuseColor.r = 1.0");
    CHECK(cone->bottomRadius.getValue() > 1.99f, "字段写回生效 bottomRadius = 2.0");
  }

  // ⑤ 错误路径：垃圾输入必须解析失败
  {
    SoInput bad;
    const char *garbage = "this is #not an inventor file \x01\x02";
    bad.setBuffer((void *)garbage, std::strlen(garbage));
    SoSeparator *badroot = SoDB::readAll(&bad);
    CHECK(badroot == nullptr, "垃圾输入解析必须失败");
  }

  // ⑥ 运行时版本号
  const char *ver = SoDB::getVersion();
  std::printf("     Coin version: %s\n", ver ? ver : "(null)");
  CHECK(ver != nullptr && std::strstr(ver, "4.0.10") != nullptr,
        "SoDB::getVersion() 含 4.0.10");

  root->unref();
  // 不调用 SoDB::finish()（理由见文件头注释）

  if (failures) {
    std::fprintf(stderr, "\ncoin 4.0.10: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\ncoin 4.0.10: 全部断言通过\n");
  return 0;
}
