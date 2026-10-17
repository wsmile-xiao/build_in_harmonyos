#include "pxr/pxr.h"
#include "pxr/usd/kind/registry.h"
#include "pxr/base/plug/registry.h"
#include "pxr/base/tf/token.h"

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using namespace pxr;

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::cerr << "FAIL: " << #cond                              \
                      << " (line " << __LINE__ << ")" << std::endl;     \
            ++failures;                                                 \
        }                                                               \
    } while (0)

// Mirrors upstream pxr/usd/kind/testenv/testKindRegistry.py (adapted from
// Python to C++ because Python support is disabled in this build).
// The plugInfo.json shipped next to this binary registers two extra
// kinds via plug metadata, replicating the upstream TestKindModule.
int main(int argc, char** argv)
{
    // Register resource plugins from the directory holding this binary
    // (same as upstream: Plug.Registry().RegisterPlugins(...)).
    // PlugRegistry requires an absolute path; TEST_RESOURCE_DIR is baked
    // in by CMake (the binary dir, where plugInfo.json is copied).
    std::string dir = argc > 1 ? argv[1] : TEST_RESOURCE_DIR;
    PlugRegistry::GetInstance().RegisterPlugins(dir + "/");

    // Factory default kinds (upstream test_Basic checks 'group', 'model';
    // the full built-in hierarchy also includes component/assembly/
    // subcomponent, all registered in KindRegistry::_RegisterDefaults).
    CHECK(KindTokens->model == TfToken("model"));
    CHECK(KindRegistry::HasKind(KindTokens->model));
    CHECK(KindRegistry::HasKind(KindTokens->component));
    CHECK(KindRegistry::HasKind(KindTokens->group));
    CHECK(KindRegistry::HasKind(KindTokens->assembly));
    CHECK(KindRegistry::HasKind(KindTokens->subcomponent));
    CHECK(!KindRegistry::HasKind(TfToken("definitely_not_a_kind")));

    // Base kind hierarchy: component->model, group->model,
    // assembly->group, subcomponent and model are roots.
    CHECK(KindRegistry::GetBaseKind(KindTokens->component) == KindTokens->model);
    CHECK(KindRegistry::GetBaseKind(KindTokens->group) == KindTokens->model);
    CHECK(KindRegistry::GetBaseKind(KindTokens->assembly) == KindTokens->group);
    CHECK(KindRegistry::GetBaseKind(KindTokens->model).IsEmpty());
    CHECK(KindRegistry::GetBaseKind(KindTokens->subcomponent).IsEmpty());

    // IsA tests, including transitive lookup assembly->group->model.
    CHECK(KindRegistry::IsA(KindTokens->assembly, KindTokens->model));
    CHECK(KindRegistry::IsA(KindTokens->assembly, KindTokens->group));
    CHECK(KindRegistry::IsA(KindTokens->component, KindTokens->model));
    CHECK(!KindRegistry::IsA(KindTokens->component, KindTokens->group));
    CHECK(!KindRegistry::IsA(TfToken("definitely_not_a_kind"),
                             KindTokens->model));

    // Convenience predicates.
    CHECK(KindRegistry::IsModel(KindTokens->component));
    CHECK(KindRegistry::IsModel(KindTokens->group));
    CHECK(KindRegistry::IsGroup(KindTokens->assembly));
    CHECK(KindRegistry::IsAssembly(KindTokens->assembly));
    CHECK(KindRegistry::IsComponent(KindTokens->component));
    CHECK(KindRegistry::IsSubComponent(KindTokens->subcomponent));

    // GetAllKinds must contain every built-in kind.
    std::vector<TfToken> allKinds = KindRegistry::GetAllKinds();
    for (const TfToken& kind : { KindTokens->model, KindTokens->component,
                                  KindTokens->group, KindTokens->assembly,
                                  KindTokens->subcomponent }) {
        CHECK(std::find(allKinds.begin(), allKinds.end(), kind)
              != allKinds.end());
    }

    // Kinds contributed via plugInfo.json metadata (upstream
    // TestKindModule_plugInfo.json, adapted to a resource plugin).
    CHECK(KindRegistry::HasKind(TfToken("test_root_kind")));
    CHECK(KindRegistry::GetBaseKind(TfToken("test_root_kind")).IsEmpty());
    CHECK(KindRegistry::HasKind(TfToken("test_model_kind")));
    CHECK(KindRegistry::GetBaseKind(TfToken("test_model_kind"))
          == KindTokens->model);
    CHECK(KindRegistry::IsModel(TfToken("test_model_kind")));
    CHECK(std::find(allKinds.begin(), allKinds.end(),
                    TfToken("test_model_kind")) != allKinds.end());

    if (failures != 0) {
        std::cerr << failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "pxr-kind smoke test: OK" << std::endl;
    return 0;
}
