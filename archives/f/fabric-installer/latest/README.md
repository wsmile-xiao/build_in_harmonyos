# fabric-installer

Hyperledger Fabric installation script that automates the process of setting up a Fabric development environment.

## Description

This script downloads and installs Hyperledger Fabric components including:
- Fabric Docker images
- Fabric CLI tool binaries (peer, orderer, configtxgen, etc.)
- Fabric CA client and server binaries
- Fabric samples repository

## Usage

```bash
./install-fabric.sh [docker|binary|samples] [-f|--fabric-version VERSION] [-c|--ca-version VERSION]
```

### Components
- `docker`: Download Fabric Docker images
- `binary`: Download Fabric binaries
- `samples`: Clone fabric-samples repository

### Options
- `-f, --fabric-version`: Fabric version (default: 2.5.15)
- `-c, --ca-version`: CA version (default: 1.5.17)

## Dependencies

- Bash shell
- curl or wget
- Docker (for downloading images)

## License

Apache-2.0
