# nuclei

ProjectDiscovery nuclei — 快速、可定制的漏洞扫描器，基于模板驱动的自动化安全测试框架。

## 基本信息
- **官网**: https://github.com/projectdiscovery/nuclei
- **许可证**: MIT
- **语言**: Go
- **类别**: security/scanner

## 已编译版本
- v3.8.0 (2026-06-01) — published

## 编译要点
- CGO_ENABLED=0 静态编译（鸿蒙铁律）
- Go 1.26.3 toolchain（go.mod要求1.25.7+）
- 入口点在 cmd/nuclei（非根目录）
- 输出到 /data/storage/el2/base/cache/（避开HMDFS mmap限制）
- 必须ELF签名才能执行
