# mongodb-tools (r4.3.2) Build Notes

## Project Identity
- **Actual project**: MongoDB Go Driver (mongo-driver), not the traditional mongo-tools (bsondump/mongodump etc.)
- **Module path**: `go.mongodb.org/mongo-driver`
- **Language**: Go
- **Original dependency manager**: dep (Gopkg.toml/Gopkg.lock)

## Build Environment
- **Go version**: 1.26.4 linux/arm64
- **GOROOT**: /storage/Users/currentUser/usr/local/go
- **GOPATH**: /storage/Users/currentUser/tmp/go-gopath
- **GOCACHE**: /storage/Users/currentUser/tmp/go-build-cache2
- **GOPROXY**: https://goproxy.cn,direct
- **Clang**: /data/service/hnp/bin/clang (OpenHarmony SDK)

## Patches Applied
1. **0001-add-go-mod.patch**: Creates `go.mod` file (project used dep, not Go modules)
2. **0002-add-go-sum.patch**: Creates `go.sum` file (dependency checksums)

## Build Method
Since the original project uses `dep` (Gopkg.toml/Gopkg.lock), we need to manually create `go.mod` and `go.sum` files to enable Go module-based compilation.

```bash
# Apply patches to create go.mod and go.sum
patch -p1 < 0001-add-go-mod.patch
patch -p1 < 0002-add-go-sum.patch

# Download dependencies
go mod download

# Build library packages as .a archives
go build -buildmode=archive ./bson ./bson/bsoncodec ./bson/bsonrw ./bson/bsontype ./bson/primitive ...
```

## Known Issue: Go Linker mmap on HMDFS
The Go linker (`go tool link`) uses `mmap(MAP_SHARED)` for output file creation. On HMDFS (HarmonyOS distributed filesystem), this operation fails with EPERM ("mapping output file failed: permission denied"). This prevents building any Go executables on this platform.

C-level mmap tests show that basic mmap operations work fine on HMDFS. The issue appears to be specific to the Go linker's internal mmap usage pattern.

**Impact**: The three cmd executables (docbuilder, godriver-benchmark, operationgen) cannot be built. These are secondary utility tools, not the primary library.

## Build Output
- **gosrc/**: Full source code of the MongoDB Go Driver (for Go module consumption)
- **gopkg/**: 28 compiled .a archive files for all library packages
- **bin/**: Empty (no executables due to linker mmap limitation)

## Packages Compiled (28 .a files)
```
go.mongodb.org/mongo-driver/bson.a
go.mongodb.org/mongo-driver/bson/bsoncodec.a
go.mongodb.org/mongo-driver/bson/bsonrw.a
go.mongodb.org/mongo-driver/bson/bsontype.a
go.mongodb.org/mongo-driver/bson/primitive.a
go.mongodb.org/mongo-driver/event.a
go.mongodb.org/mongo-driver/internal.a
go.mongodb.org/mongo-driver/mongo.a
go.mongodb.org/mongo-driver/mongo/gridfs.a
go.mongodb.org/mongo-driver/mongo/options.a
go.mongodb.org/mongo-driver/mongo/readconcern.a
go.mongodb.org/mongo-driver/mongo/readpref.a
go.mongodb.org/mongo-driver/mongo/writeconcern.a
go.mongodb.org/mongo-driver/tag.a
go.mongodb.org/mongo-driver/version.a
go.mongodb.org/mongo-driver/x/bsonx.a
go.mongodb.org/mongo-driver/x/bsonx/bsoncore.a
go.mongodb.org/mongo-driver/x/mongo/driver.a
go.mongodb.org/mongo-driver/x/mongo/driver/address.a
go.mongodb.org/mongo-driver/x/mongo/driver/auth.a
go.mongodb.org/mongo-driver/x/mongo/driver/connstring.a
go.mongodb.org/mongo-driver/x/mongo/driver/description.a
go.mongodb.org/mongo-driver/x/mongo/driver/dns.a
go.mongodb.org/mongo-driver/x/mongo/driver/operation.a
go.mongodb.org/mongo-driver/x/mongo/driver/session.a
go.mongodb.org/mongo-driver/x/mongo/driver/topology.a
go.mongodb.org/mongo-driver/x/mongo/driver/uuid.a
go.mongodb.org/mongo-driver/x/mongo/driver/wiremessage.a
```
---

**编译结束**: 2026-06-08 21:34
**最终状态**: built
