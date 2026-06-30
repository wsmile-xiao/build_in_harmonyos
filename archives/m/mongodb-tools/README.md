# mongodb-tools

MongoDB Go Driver (mongo-driver) — the official Go driver for MongoDB.

## What It Is

The `mongodb-tools` r4.3.2 package is actually the **MongoDB Go Driver** (also known as `mongo-driver`), not the traditional mongo-tools command-line utilities (bsondump, mongodump, mongorestore, etc.). The module path is `go.mongodb.org/mongo-driver`.

This Go library provides:
- **bson**: BSON serialization/deserialization (codec, primitive types, reader/writer)
- **mongo**: MongoDB client API (connect, CRUD operations, gridfs, options, read/write concerns)
- **x/bsonx**: Extended BSON codec and core types
- **x/mongo/driver**: Low-level MongoDB wire protocol driver (auth, topology, sessions, operations)

## Dependencies

- **Go 1.26+** (required for compilation)
- **github.com/go-stack/stack** v1.8.1
- **github.com/golang/snappy** v1.0.0
- **github.com/xdg/scram** v1.0.5
- **golang.org/x/sync** v0.21.0

## OHOS Adaptation Notes

1. **dep → Go Modules**: The original project uses `dep` (Gopkg.toml/Gopkg.lock). Patches add `go.mod` and `go.sum` for module-based compilation.

2. **Go Linker mmap Limitation**: The Go linker cannot create executables on HMDFS due to `mmap(MAP_SHARED)` returning EPERM. Library packages are compiled as `.a` archives using `go build -buildmode=archive`.

3. **No Command Binaries**: The three cmd tools (docbuilder, godriver-benchmark, operationgen) cannot be built on this platform. These are secondary utility tools, not the primary library.

4. **Package Installation**: The `.a` archive files and source code are provided under `gopkg/` and `gosrc/` directories for Go module consumption.

## Usage

After installation, use the Go driver in your Go projects by importing:

```go
import "go.mongodb.org/mongo-driver/bson"
import "go.mongodb.org/mongo-driver/mongo"
import "go.mongodb.org/mongo-driver/mongo/options"
```

Set `GOPATH` and `GOROOT` environment variables to include the installed paths.