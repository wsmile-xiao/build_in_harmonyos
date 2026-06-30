# fabric-installer

Hyperledger Fabric installation tool that simplifies the setup of Fabric development environment.

## Overview

fabric-installer is a bash script that automates downloading and installing Hyperledger Fabric components:

- Fabric Docker images
- Fabric CLI binaries (peer, orderer, configtxgen, cryptogen, etc.)
- Fabric CA binaries
- Fabric samples repository

## Installation

Download the latest version from the archives and run:

```bash
tar -xzf fabric-installer-latest-ohos-aarch64.tar.gz
cd fabric-installer
./install-fabric.sh docker binary samples
```

## Available Versions

- latest (default version: Fabric 2.5.15, CA 1.5.17)

## Platform Support

- Linux (x86_64, arm64)
- macOS
- Windows (via Git Bash/WSL)

## License

Apache-2.0

## Links

- [Hyperledger Fabric Documentation](https://hyperledger-fabric.readthedocs.io)
- [Fabric Samples](https://github.com/hyperledger/fabric-samples)
