#include <iostream>
#include <string>

#include <kolabxml/kolabformat.h>
#include <kolabxml/kolabnote.h>

int main()
{
    // Exercise the Kolab XML serialization round-trip: build a Note,
    // serialize it to Kolab v3 XML, read it back and compare fields.
    Kolab::Note note;
    note.setUid("test-uid-1234");
    note.setSummary("HarmonyOS PC conan test_package summary");
    note.setDescription("Round-trip through Kolab::writeNote/readNote");
    note.setCreated(Kolab::cDateTime(2026, 9, 19, 12, 0, 0, true));
    note.setLastModified(Kolab::cDateTime(2026, 9, 19, 12, 0, 0, true));

    const std::string xml = Kolab::writeNote(note);
    if (Kolab::error() != Kolab::NoError) {
        std::cerr << "writeNote failed: " << Kolab::errorMessage() << std::endl;
        return 1;
    }
    if (xml.empty()) {
        std::cerr << "writeNote produced empty XML" << std::endl;
        return 1;
    }

    const Kolab::Note re = Kolab::readNote(xml, false);
    if (Kolab::error() != Kolab::NoError) {
        std::cerr << "readNote failed: " << Kolab::errorMessage() << std::endl;
        return 1;
    }
    if (re.uid() != "test-uid-1234"
        || re.summary() != "HarmonyOS PC conan test_package summary"
        || re.description() != "Round-trip through Kolab::writeNote/readNote") {
        std::cerr << "round-trip mismatch: uid=" << re.uid()
                  << " summary=" << re.summary() << std::endl;
        return 1;
    }

    std::cout << "libkolabxml note round-trip OK (xml bytes: " << xml.size() << ")" << std::endl;
    return 0;
}
