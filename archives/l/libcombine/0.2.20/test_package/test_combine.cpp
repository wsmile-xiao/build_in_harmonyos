// Consumer test for libcombine 0.2.20 (R34: must call real library APIs).
//
// Exercises:
//  1. KnownFormats::isFormat / lookupFormat (format registry)
//  2. Util::getExtension / temp-dir accessors (utility layer)
//  3. CombineArchive end-to-end roundtrip: addFileFromString + metadata,
//     writeToFile, initializeFromArchive, extractEntryToString, cleanUp
//  4. OmexDescription + VCard metadata model (write + read back)

#include <cstdio>
#include <string>

#include <combine/combinearchive.h>
#include <combine/knownformats.h>
#include <combine/util.h>
#include <combine/omexdescription.h>
#include <combine/vcard.h>
#include <omex/CaOmexManifest.h>
#include <omex/common/CaOperationReturnValues.h>

LIBCOMBINE_CPP_NAMESPACE_USE

namespace {

int g_failures = 0;

void check(bool ok, const char* name)
{
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", name);
    if (!ok)
        ++g_failures;
}

} // namespace

int main()
{
    // 1. KnownFormats registry (pure API, no I/O).
    check(KnownFormats::isFormat(
              "sbml", "http://identifiers.org/combine.specifications/sbml"),
          "KnownFormats::isFormat sbml");
    check(!KnownFormats::isFormat("sbml", "something else"),
          "KnownFormats::isFormat negative");
    check(!KnownFormats::lookupFormat("sedml").empty()
          && KnownFormats::lookupFormat("sedml").find("combine.specifications/sed") != std::string::npos,
          "KnownFormats::lookupFormat sedml");

    // 2. Util helpers.
    check(Util::getExtension("model.xml") == "xml", "Util::getExtension xml");
    check(!Util::getDefaultTempDir().empty(), "Util::getDefaultTempDir non-empty");

    // 3. Fresh archive starts without a manifest.
    CombineArchive archive;
    check(archive.getManifest() == NULL, "new archive has null manifest");

    static const char* kModel = "<?xml version=\"1.0\"?><sbml/>";
    static const char* kLocation = "./model/model.xml";
    static const char* kFormat = "http://identifiers.org/combine.specifications/sbml";
    archive.addFileFromString(kModel, kLocation, kFormat);
    check(archive.getManifest() != NULL, "manifest created after addFile");
    check(archive.getManifest()->getNumContents() == 1, "manifest has 1 content");

    // 4. Metadata model: VCard creator + description roundtrip through OMEX.
    VCard creator;
    creator.setEmail("hmbs@example.org");
    creator.setFamilyName("Gan");
    creator.setGivenName("Dui");
    creator.setOrganization("OHOS");
    check(!creator.isEmpty(), "VCard populated");

    OmexDescription desc;
    desc.setAbout(".");
    desc.setDescription("hmbs consumer test");
    desc.setCreated(OmexDescription::getCurrentDateAndTime());
    desc.addCreator(creator);
    check(archive.addMetadata(".", desc) == LIBCOMBINE_OPERATION_SUCCESS,
          "addMetadata success");
    check(archive.hasMetadataForLocation("."), "hasMetadataForLocation");

    // 5. Persist + reload + verify content and metadata.
    static const char* kFile = "hmbs_roundtrip.omex";
    std::remove(kFile);
    check(archive.writeToFile(kFile), "writeToFile");

    CombineArchive second;
    check(second.initializeFromArchive(kFile), "initializeFromArchive");
    check(second.getManifest() != NULL, "reloaded manifest non-null");
    check(second.getManifest()->getNumContents() == 1, "reloaded manifest has 1 content");
    check(second.extractEntryToString(kLocation) == kModel, "roundtrip content equal");

    OmexDescription back = second.getMetadataForLocation(".");
    check(!back.isEmpty(), "reloaded metadata non-empty");
    check(back.getDescription() == "hmbs consumer test", "reloaded description equal");
    check(back.getNumCreators() == 1, "reloaded creator count");
    check(back.getNumCreators() == 1
          && back.getCreator(0).getEmail() == "hmbs@example.org",
          "reloaded creator email");

    check(second.cleanUp(), "cleanUp");
    std::remove(kFile);

    if (g_failures == 0)
        std::printf("ALL TESTS PASSED\n");
    else
        std::printf("FAILURES: %d\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
