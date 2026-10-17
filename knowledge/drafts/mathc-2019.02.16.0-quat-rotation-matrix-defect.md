# mathc 2019.02.16.0 四元数旋转矩阵官方缺陷（草稿）

- **软件**：mathc 2019.02.16.0（https://github.com/felselva/mathc）
- **平台**：HarmonyOS PC / aarch64，编译器 `clang 15.0.4`（OHOS toolchain），Conan 2.29.1
- **状态**：DRAFT

## 现象

HarmonyOS 专项测试中，四元数绕 Z 轴 90° 旋转断言失败：

```
quat(q, 0, 0, 0.70710678, 0.70710678);      // 绕 Z 轴 90°
mat4_rotation_quat(rot, q);
vec4_multiply_mat4(out, (1,0,0,1), rot);    // 期望 (0,1,0,1)，实际错误
FAIL: quat 绕 Z 90° 旋转 (1,0,0)->(~0,1,0)
```

## 根因

官方 tag v2019.02.16.0 的 `mathc.c` 中 `mat3_rotation_quat` 与 `mat4_rotation_quat`
存在同一缺陷（已 `git clone --branch v2019.02.16.0` 官方源码逐字节核对
SHA-256 一致，确认是上游缺陷非下载污染）：

1. **越界读**：`mfloat_t xz = q0[8] * q0[0];` —— q0 是 4 元素四元数数组，`q0[8]` 越界
   （应为 `q0[2]`，即 xz = z·x）。
2. **对角项符号错误**：`result[0]=1-2*(yy-zz)`、`result[5]=1-2*(xx-zz)`、
   `result[10]=1-2*(xx-yy)` 应为 `yy+zz`、`xx+zz`、`xx+yy`（标准旋转矩阵
   m00=1-2(yy+zz)、m11=1-2(xx+zz)、m22=1-2(xx+yy)）。

## 修复

`patches/0001-mathc.c.patch`（+8/-8 行）：

```
-	mfloat_t xz = q0[8] * q0[0];
+	mfloat_t xz = q0[2] * q0[0];
-	result[0] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (yy - zz);
+	result[0] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (yy + zz);
-	result[4/5] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (xx - zz);
+	result[4/5] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (xx + zz);
-	result[8/10] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (xx - yy);
+	result[8/10] = MFLOAT_C(1.0) - MFLOAT_C(2.0) * (xx + yy);
```

## 验证

- 修复前：quat 断言 FAIL；修复后：12/12 断言 ALL PASS（退出码 0），
  含绕 Z 90° `(1,0,0)->(0,1,0)`、`mat4_perspective M*M^-1≈identity`、
  `vec3_cross`、`mat4_translation` 等。
- conan-verify G2：`conan create`（ohos-aarch64）PASS，test_package 消费者验证通过。

## 适用边界

- 消费 mathc v2019.02.16.0（或同源四元数旋转矩阵实现）的项目。
- 判别方法可复用：**官方 tag 缺陷必须 git clone 逐字节核对 SHA-256 排除下载污染**。
- 反例：版本号带适配后缀（如 .0.1）的修复版本已含此补丁，直接消费，不得重复打补丁。
