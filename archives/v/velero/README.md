# velero

Velero is an open source tool to safely backup and restore, perform disaster recovery, and migrate Kubernetes cluster resources and persistent volumes.

## Features
- Backup and restore Kubernetes cluster resources and persistent volumes
- Disaster recovery
- Cluster migration
- Support for multiple cloud providers (AWS, Azure, GCP)

## Compilation Notes
- Requires Go 1.22+ compiler
- Built with CGO_ENABLED=0 for musl compatibility
- Use `go mod vendor` to avoid HMDFS module cache issues
- All Go tool binaries must be ELF-signed on 鸿蒙

## Usage
```
velero version --client-only
velero backup create <name>
velero restore create <name> --from-backup <backup>
```
