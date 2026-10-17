# test_package 断言输出留档

> 来源：`reports/conan-create-evidence.md`（采信轮干净构建日志）中 test_package 段落。
> 提取命令：`grep -E '^(PASS|FAIL|dicom3tools test_package)' reports/conan-create.log`

| 属性 | 值 |
| --- | --- |
| PASS 行数 | 22 |
| FAIL 行数 | 0 |
| 汇总行 | `dicom3tools test_package: 22 passed, 0 failed` |
| 采信轮提交 | `48813722e1ccb489db358f51e973a6376ced5c03` |

```
PASS: found dccreate
PASS: found dcdump
PASS: found dciodvfy
PASS: found dckey
PASS: found dcdict
PASS: found dcstats
PASS: found dccp
PASS: dccreate wrote a DICOM file (rc=0)
PASS: created file is non-empty (658 bytes)
PASS: file has the Part 10 DICM magic at offset 128
PASS: dcdump read back the Patient ID that was set
PASS: dcdump read back the Patient Name that was set
PASS: explicit VR little endian transfer syntax recorded in the meta header
PASS: dcdict resolved PatientName to (0x0010,0x0010)
PASS: dcdict reports the PN value representation
PASS: dckey described the PatientName tag
PASS: dciodvfy produced a validation report
PASS: dciodvfy read the file dccreate produced
PASS: dcstats reported the missing pixel data
PASS: dcdump rejected a truncated data set (rc=1)
PASS: dciodvfy rejected a non-DICOM file (rc=1)
PASS: dccp re-encoded the file meta information (394 bytes)
dicom3tools test_package: 22 passed, 0 failed
```
