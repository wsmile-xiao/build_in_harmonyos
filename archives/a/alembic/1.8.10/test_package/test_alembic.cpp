// Consumer smoke test for alembic 1.8.10.
// Exercises the real Alembic API together with the vendored Imath types:
// writes an Ogawa archive with a child object holding an Imath V3f property,
// then reads it back through AbcCoreFactory and verifies the structure.
#include <cstdio>
#include <string>

#include <Alembic/Abc/All.h>
#include <Alembic/AbcCoreOgawa/All.h>
#include <Alembic/AbcCoreFactory/All.h>

namespace Abc = Alembic::Abc;
using namespace Abc;

static const char* kPath = "alembic_smoke.abc";

int main(void)
{
    // --- Write side: create an archive, an object, an Imath V3f property. ---
    {
        OArchive archive(Alembic::AbcCoreOgawa::WriteArchive(), kPath,
                         ErrorHandler::kThrowPolicy);
        OObject top(archive, kTop);
        OObject child(top, "smoke_child");

        OV3fProperty vecProp(OCompoundProperty(child, kTop), "vec", 0);
        vecProp.set(Imath::V3f(1.0f, 2.0f, 3.0f));
    }

    // --- Read side: reopen via the factory and verify. ---
    Alembic::AbcCoreFactory::IFactory factory;
    IArchive archive = factory.getArchive(std::string(kPath));
    if (!archive.valid()) {
        std::printf("FAIL: reopened archive is not valid\n");
        return 1;
    }

    IObject top = archive.getTop();
    if (top.getNumChildren() != 1) {
        std::printf("FAIL: expected 1 child, got %zu\n", top.getNumChildren());
        return 1;
    }

    IObject child = top.getChild(0);
    if (child.getName() != "smoke_child") {
        std::printf("FAIL: wrong child name: %s\n", child.getName().c_str());
        return 1;
    }

    std::printf("alembic 1.8.10 smoke test OK: wrote and read back '%s'\n", kPath);
    return 0;
}
