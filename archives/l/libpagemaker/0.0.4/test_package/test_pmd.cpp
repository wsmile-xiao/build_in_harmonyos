#include <libpagemaker/libpagemaker.h>
#include <librevenge-stream/librevenge-stream.h>
#include <librevenge-generators/librevenge-generators.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <sys/utsname.h>

static int assertions;
#define CHECK(x) do { assertions++; if (!(x)) { std::fprintf(stderr,"FAIL line=%d: %s\n",__LINE__,#x); return 1; } } while (0)
int main() {
    const char *fixture=std::getenv("PMD_TEST_FIXTURE"), *tmp=std::getenv("TMPDIR");
    CHECK(fixture && tmp && tmp[0]=='/');
    char path[4096];
    CHECK(std::snprintf(path,sizeof(path),"%s/pmd-XXXXXX",tmp)<(int)sizeof(path));
    int fd=mkstemp(path);
    CHECK(fd>=0);
    FILE *file=std::fopen(fixture,"rb");
    CHECK(file!=nullptr);
    unsigned char buffer[96257]; size_t bytes=std::fread(buffer,1,sizeof(buffer),file);
    CHECK(bytes==96256 && std::ferror(file)==0);
    CHECK(std::fclose(file)==0);
    CHECK(write(fd,buffer,bytes)==(ssize_t)bytes);
    CHECK(close(fd)==0);
    librevenge::RVNGFileStream input(path);
    CHECK(libpagemaker::PMDocument::isSupported(&input));
    librevenge::RVNGStringVector pages;
    librevenge::RVNGSVGDrawingGenerator generator(pages, "");
    CHECK(libpagemaker::PMDocument::parse(&input,&generator));
    CHECK(!pages.empty() && !pages[0].empty());
    CHECK(std::strstr(pages[0].cstr(),"svg")!=nullptr);
#ifdef __OHOS__
    struct utsname system;
    CHECK(uname(&system)==0 && std::strcmp(system.sysname,"HarmonyOS")==0);
#endif
    CHECK(unlink(path)==0);
    std::printf("CONSUMER_1_OF_1_PASS assertions=%d svg_pages=%u\n",assertions,pages.size());
    return 0;
}
