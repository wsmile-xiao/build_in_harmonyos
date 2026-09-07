// test_package/test_boost_iostreams.cpp — boost1.84-iostreams 1.84.0 L1 smoke test.
// Exercises the Boost.Iostreams component the way a downstream consumer does:
// filtering_stream pipeline + the three compression backends linked from this
// package (zlib, gzip-on-zlib, bzip2) + file_descriptor device + mapped_file
// memory-mapped device.
#include <boost/iostreams/filtering_stream.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filter/bzip2.hpp>
#include <boost/iostreams/filter/zlib.hpp>
#include <boost/iostreams/device/file_descriptor.hpp>
#include <boost/iostreams/device/mapped_file.hpp>
#include <boost/iostreams/copy.hpp>

#include <cassert>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <string>

namespace io = boost::iostreams;

static const std::string payload(5000, 'x');

// Decompress a std::string buffer through the named filter and compare
// against the original payload. Returns the decompressed size (or -1).
static bool decompress_and_check(const std::string& name,
                                 const std::string& compressed) {
    io::filtering_istream in;
    if (name == "gzip") {
        in.push(io::gzip_decompressor());
    } else if (name == "zlib") {
        in.push(io::zlib_decompressor());
    } else if (name == "bzip2") {
        in.push(io::bzip2_decompressor());
    } else {
        std::cerr << "unknown filter: " << name << std::endl;
        return false;
    }
    std::istringstream source(compressed);
    in.push(source);
    std::string back;
    io::copy(in, std::back_inserter(back));
    if (back != payload) {
        std::cerr << name << ": round-trip mismatch (" << back.size()
                  << " != " << payload.size() << ")" << std::endl;
        return false;
    }
    return true;
}

int main() {
    // 1) gzip compression round-trip (zlib backend through gzip filter)
    {
        std::ostringstream compressed;
        {
            io::filtering_ostream out;
            out.push(io::gzip_compressor());
            out.push(compressed);
            io::write(out, payload.data(), payload.size());
            io::close(out);
        }
        if (!decompress_and_check("gzip", compressed.str())) {
            return 1;
        }
        std::cout << "gzip round-trip OK (" << compressed.str().size()
                  << " bytes compressed)" << std::endl;
    }

    // 2) raw zlib compression round-trip
    {
        std::ostringstream compressed;
        {
            io::filtering_ostream out;
            out.push(io::zlib_compressor());
            out.push(compressed);
            io::write(out, payload.data(), payload.size());
            io::close(out);
        }
        if (!decompress_and_check("zlib", compressed.str())) {
            return 1;
        }
        std::cout << "zlib round-trip OK (" << compressed.str().size()
                  << " bytes compressed)" << std::endl;
    }

    // 3) bzip2 compression round-trip (bzip2 backend compiled into
    //    libboost_iostreams.a from this package)
    {
        std::ostringstream compressed;
        {
            io::filtering_ostream out;
            out.push(io::bzip2_compressor());
            out.push(compressed);
            io::write(out, payload.data(), payload.size());
            io::close(out);
        }
        if (!decompress_and_check("bzip2", compressed.str())) {
            return 1;
        }
        std::cout << "bzip2 round-trip OK (" << compressed.str().size()
                  << " bytes compressed)" << std::endl;
    }

    // 4) file_descriptor device + chain composition + copy through a real file
    {
        const char* path = "iostreams_smoke_fd.bin";
        {
            io::file_descriptor_sink sink(path, std::ios_base::binary);
            io::filtering_ostream out;
            out.push(io::gzip_compressor());
            out.push(sink);
            io::write(out, payload.data(), payload.size());
            io::close(out);
        }
        io::file_descriptor_source source(path, std::ios_base::binary);
        io::filtering_istream in;
        in.push(io::gzip_decompressor());
        in.push(source);
        std::string back;
        io::copy(in, std::back_inserter(back));
        if (back != payload) {
            std::cerr << "file_descriptor gzip pipeline mismatch" << std::endl;
            return 1;
        }
        io::close(in);
        std::remove(path);
        std::cout << "file_descriptor + gzip pipeline OK" << std::endl;
    }

    // 5) mapped_file memory-mapped device
    {
        const char* path = "iostreams_smoke_mmap.bin";
        {
            io::file_descriptor_sink sink(path, std::ios_base::binary);
            io::write(sink, payload.data(), payload.size());
        }
        io::mapped_file_source mf(path);
        if (!mf.is_open() || mf.size() != payload.size()
            || std::string(mf.data(), mf.size()) != payload) {
            std::cerr << "mapped_file source mismatch" << std::endl;
            return 1;
        }
        mf.close();
        std::remove(path);
        std::cout << "mapped_file source OK" << std::endl;
    }

    std::cout << "boost1.84-iostreams 1.84.0: gzip/zlib/bzip2 + "
                 "file_descriptor + mapped_file OK" << std::endl;
    return 0;
}
