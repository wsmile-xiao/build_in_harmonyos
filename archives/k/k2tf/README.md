# k2tf

Convert Kubernetes API objects (in YAML format) into HashiCorp's Terraform configuration (HCL). Go 实现的 Kubernetes YAML → Terraform HCL 转换 CLI 工具，输出可直接配合 Terraform Kubernetes Provider 使用。

- 上游: https://github.com/sl1pm4t/k2tf
- 版本: 0.8.0
- 许可证: MPL-2.0
- 构建: Go modules（无 vendor，依赖经 GOPROXY 拉取），`go build .`
- 典型用法: `kubectl get deploy -o yaml | k2tf > main.tf`
