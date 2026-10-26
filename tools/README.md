# 解包、制作和校验工具

现成固件与 App 在[下载目录](../downloads/README.md)。这里用于重新制作 3e 的倍率包，或研究其他型号的文件。

## 准备环境

安装 Python 3.10+ 和 7-Zip 命令行，在仓库的 `tools` 目录打开 PowerShell：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

如果 `7z` 不在 PATH，在制作或验证命令后追加 `--sevenzip "C:/Program Files/7-Zip/7z.exe"`。

## TWS 3e

原包随仓库提供，位置为 `../downloads/TWS3e/v2.6.3/original.bin`。

```powershell
.venv/Scripts/python.exe fwtool.py inspect ../downloads/TWS3e/v2.6.3/original.bin
.venv/Scripts/python.exe fwtool.py unpack ../downloads/TWS3e/v2.6.3/original.bin --output work/original
.venv/Scripts/python.exe fwtool.py build --original ../downloads/TWS3e/v2.6.3/original.bin --scale 1.0 --output output/control_1.00.bin
.venv/Scripts/python.exe fwtool.py build --original ../downloads/TWS3e/v2.6.3/original.bin --scale 1.25 --output output/experiment_1.25.bin
```

`1.0` 做原包重建，结果应逐字节相同。其余倍率修改镜像中的同一个前馈比例初值，每次从原包重新生成。

检查已有文件：

```powershell
.venv/Scripts/python.exe fwtool.py verify --original ../downloads/TWS3e/v2.6.3/original.bin --candidate ../downloads/TWS3e/v2.6.3/ff-1.25.bin --scale 1.25 --report output/verify_1.25.json
```

工具通过源哈希选择 3e v2.6.3 的数据位置。增加新版本配置时，一起补充原包重建、字节差异和坏包测试。

## QCC 历史固件

`qcc_inspect.py` 使用 Python 标准库，列出 `APPUHDR5` 记录、分区、文件名和哈希，也可以比较两个版本：

```powershell
python qcc_inspect.py ../library/firmware/TWS3/2.12.2.bin
python qcc_inspect.py ../library/firmware/TWS3/2.12.2.bin --compare ../library/firmware/TWS3/2.12.6.bin
python qcc_inspect.py ../library/firmware/TWS4/2.58.5.bin --extract work/tws4-2.58.5
```

`--extract` 把分区及可解析的 `File` 文件系统写到新目录。两种封装的后续研究见[资料索引](../library/research-index.md)。

## 构建时做的检查

每份 3e 修改包都会经过全镜像字节比较、7-Zip 独立解压、原始 ARM CRC、两段应用验包函数及原始增益函数的检查，并生成 `.verification.json`。

执行环境提供模拟 RAM 和 Flash，拦截日志及外部回调，增益测试的硬件输出通道设为零。记录中的输出值用于核对参数计算，实际听感在安装后另外比较。

## 测试

```powershell
$env:TWS3E_ORIGINAL = (Resolve-Path ../downloads/TWS3e/v2.6.3/original.bin).Path
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

测试会检查无修改重建、倍率差异、输入哈希、损坏载荷、型号字段和异常 LZMA。构建器完成检查后写入 BIN 及记录，已有文件保留，重复操作时使用新的输出文件名。
