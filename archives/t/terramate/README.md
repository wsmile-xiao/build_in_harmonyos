# terramate

Terramate is an Infrastructure as Code orchestration, observability and visibility platform for Terraform, OpenTofu and Terragrunt. It helps accelerate IaC projects with faster pipelines, reduced blast radius, drift and vulnerability detection.

## Build Information

- **Language**: Go
- **Build System**: go build
- **Source**: https://github.com/terramate-io/terramate
- **Latest Version**: 0.17.1

## Compilation Notes

- Go project, uses `go build -o terramate ./cmd/terramate`
- CGO disabled for static linking
- No patches required
- Builds cleanly on OpenHarmony aarch64 with Go 1.26.4
