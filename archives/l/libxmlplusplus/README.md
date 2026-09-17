# libxmlplusplus (libxml++)

C++ 封装库，提供 libxml2 的面向对象 API（DOM / SAX / 校验 / XPath / 序列化）。

## 归档版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.2.5 | published | NEW 3.0 API 线（pc `libxml++-3.0`），Meson 构建 |

## 依赖

- glibmm/2.66.9（glibmm-2.4 ABI 线；3.x 依赖 `glibmm-2.4 >= 2.32.0`）
- libxml2/2.15.3（`libxml-2.0 >= 2.7.7`）

## 说明

3.x 线（pc `libxml++-3.0`）与 2.x 旧线（pc `libxml++-2.6`，见 libxmlpp 归档）API 不兼容；
同仓库另有 5.x 线（libxml++/5.4.0）归档。