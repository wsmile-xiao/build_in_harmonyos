// test_package for xrootd: exercises the real XrdCl client API.
//  1. XrdCl::URL parsing (public client-side API)
//  2. Local-to-local file copy through the XrdCl copy machinery
//     (CopyProcess + LocalFileHandler data path, no server required)
// The copied content is verified byte by byte.
#include <fcntl.h>
#include <unistd.h>

#include <cstdio>
#include <cstring>
#include <string>

#include "XrdCl/XrdClCopyProcess.hh"
#include "XrdCl/XrdClURL.hh"

static bool write_file(const std::string &path, const std::string &content)
{
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return false;
    bool ok = write(fd, content.data(), content.size()) == (ssize_t)content.size();
    close(fd);
    return ok;
}

static bool read_file(const std::string &path, std::string &out)
{
    int fd = open(path.c_str(), O_RDONLY);
    if (fd < 0) return false;
    char buf[512];
    ssize_t n = read(fd, buf, sizeof(buf));
    close(fd);
    if (n < 0) return false;
    out.assign(buf, (size_t)n);
    return true;
}

int main()
{
    // 1. URL parsing
    XrdCl::URL url("root://example.org:1094//store/data/file.root?svc=1");
    if (!url.IsValid() || url.GetHostId() != "example.org:1094"
        || url.GetPathWithParams() != "/store/data/file.root?svc=1")
    {
        std::printf("FAIL: URL parse (host=%s path=%s)\n",
                    url.GetHostId().c_str(), url.GetPathWithParams().c_str());
        return 1;
    }
    std::printf("OK: URL parse (%s)\n", url.GetHostId().c_str());

    // 2. Local copy through XrdCl copy machinery
    char cwdbuf[1024];
    if (!getcwd(cwdbuf, sizeof(cwdbuf)))
    {
        std::printf("FAIL: getcwd\n");
        return 1;
    }
    const std::string base(cwdbuf);
    const std::string src = base + "/xrdcl_test_src.txt";
    const std::string dst = base + "/xrdcl_test_dst.txt";
    const std::string payload = "hello xrootd on openharmony";
    unlink(dst.c_str());
    if (!write_file(src, payload))
    {
        std::printf("FAIL: cannot prepare source file\n");
        return 1;
    }

    XrdCl::CopyProcess process;
    XrdCl::PropertyList props;
    props.Set("source", "file://" + src);
    props.Set("target", "file://" + dst);
    XrdCl::PropertyList results;
    process.AddJob(props, &results);
    XrdCl::XRootDStatus st = process.Prepare();
    if (!st.IsOK())
    {
        std::printf("FAIL: Prepare: %s\n", st.ToString().c_str());
        return 1;
    }
    st = process.Run(0);
    if (!st.IsOK())
    {
        std::printf("FAIL: Copy Run: %s\n", st.ToString().c_str());
        return 1;
    }
    std::string got;
    if (!read_file(dst, got) || got != payload)
    {
        std::printf("FAIL: copied content mismatch\n");
        return 1;
    }
    std::printf("OK: XrdCl local copy (%zu bytes verified)\n", got.size());

    unlink(src.c_str());
    unlink(dst.c_str());
    std::printf("ALL TESTS PASSED\n");
    return 0;
}
