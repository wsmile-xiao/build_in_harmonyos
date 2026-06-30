# golang-migrate

Database migrations CLI tool for Go.

## Description

golang-migrate is a database migration tool written in Go. It supports multiple
database drivers (PostgreSQL, MySQL, SQLite, etc.) and source formats (file,
Go bindata, GitHub, etc.). The CLI tool allows you to create, apply, and roll
back database migrations from the command line.

## Version

- **homebrew**: v4.19.1 (latest from GitHub)

## Build System

- Go (CGO_ENABLED=1, cross-compiled for linux/arm64)

## Build Details

- Build command: `CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w -X main.Version=v4.19.1" -tags "postgres mysql sqlite sqlite3 file" -o migrate ./cmd/migrate/`
- Version injection: `-X main.Version=v4.19.1` via ldflags
- SSL workaround: Use `codeload.github.com` when `github.com` fails

## Sources

- GitHub: https://github.com/golang-migrate/migrate
- Homebrew: golang-migrate formula
