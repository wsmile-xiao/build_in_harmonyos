# protoc-gen-go-grpc

Protoc plugin that generates Go gRPC service code from `.proto` files.

## Usage

```bash
protoc --go-grpc_out=. path/to/file.proto
```

This generates Go service definitions (`_grpc.pb.go`) for the protocol buffer
defined by `file.proto`.

## Version

- **1.6.2**: Current version, compiled for OpenHarmony arm64

## Links

- [GitHub](https://github.com/grpc/grpc-go/tree/master/cmd/protoc-gen-go-grpc)
- [Homebrew #712](https://github.com/Homebrew/homebrew-core/blob/master/Formula/p/protoc-gen-go-grpc.rb)

## License

Apache-2.0
