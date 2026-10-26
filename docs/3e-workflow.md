# TWS 3e 固件制作与安装

下面用本次研究的 3e v2.6.3 演示：准备原包、解包、修改前馈增益、校验，再通过本地固件 App 安装。

## 准备环境和原包

电脑安装 Python 3.10+、7-Zip 命令行。在仓库目录打开 PowerShell：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force input
```

把官方原包复制为 `input/original_2.6.3.bin`。这份文件大小为 1,079,790 字节，SHA-256 为：

```text
8c83d3492e1a45b1240f5e15e2a2a46745b0954fb123a17af9b102bd96fb4182
```

构建器通过这个哈希选择本次的镜像布局和参数位置。研究其他版本时，先补充对应的原包配置。

## 检查和解包

```powershell
.venv/Scripts/python.exe fwtool.py inspect input/original_2.6.3.bin
.venv/Scripts/python.exe fwtool.py unpack input/original_2.6.3.bin --output work/original
```

`inspect` 显示包大小、项目字段、分段数量和 CRC 结果。`unpack` 在新目录生成镜像、包头及摘要，供反汇编和参数分析。

## 制作倍率包

先做 1.00 倍重建，再制作需要比较的倍率。每次都从官方原包开始：

```powershell
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.0 --output output/control_1.00.bin
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.25 --output output/experiment_1.25.bin
```

`--scale` 可选 `0.5`、`0.99`、`1.0`、`1.01`、`1.25`、`1.5`。它修改前馈增益比例的启动初值；各倍率的研究进展见[实验经过](progress.md)。

工具会检查完整镜像差异，运行 7-Zip 解压对照、原始 CRC 和验包函数，再执行原始增益函数。完成后生成 BIN 和 `.verification.json`。已有输出会保留，重复构建时换一个文件名即可。

如果 `7z` 不在 PATH，在命令末尾添加 `--sevenzip "C:/Program Files/7-Zip/7z.exe"`。

## 复核已有文件

```powershell
.venv/Scripts/python.exe fwtool.py verify --original input/original_2.6.3.bin --candidate output/experiment_1.25.bin --scale 1.25 --report output/verify_again_1.25.json
```

在 JSON 中核对倍率、SHA-256、字节差异和各项执行结果。此次修改位置为镜像 `0x1c3e20` 的 float32，另有内部 CRC 与外层包头的长度、CRC 字段变化。型号、版本、地址、代码及其他系数与原包保持一致。

电脑上也可运行 `Get-FileHash output/experiment_1.25.bin -Algorithm SHA256`，与 JSON 的 `candidate.sha256` 比较。

## 安装到手机和耳机

资料中的 `vivotws_local_FW.apk` 提供本地文件入口。本次分析的 APK SHA-256 为：

```text
5336b406ee17451e5af3033183ec03d127eb76786fcce395d75b6c104b3f02a0
```

1. 在安卓手机安装本地固件版 App。若手机提示与官方版签名冲突，先处理应用安装冲突；卸载官方版会清除它的应用数据。
2. 将选定的完整 BIN 复制一份，命名为 `update.bin`，保留电脑上的原文件名和校验记录。
3. 在手机内部存储最外层建立 `vivotws` 文件夹，把文件放到 `/sdcard/vivotws/update.bin`。
4. 核对手机文件大小和哈希。手机文件管理器没有哈希功能时，可通过 USB 复制回电脑比较。
5. 完全退出并重新打开 App，授予蓝牙连接和文件读取所需权限，连接 TWS 3e，查看双耳状态。
6. 进入耳机固件更新页面，按 App 提示满足电量和耳机放置要求，开始更新，等待完成并重新连接。

App 会把更新信息的目标版本设为 `2147483647`，实际读取上面的本地文件。因此选择哪个倍率，要以 `update.bin` 的内容和哈希为准。完成后检查双耳连接、播放与降噪，并记录安装结果。

## 做一次可比较的听感测试

先用同一个噪声源和相同佩戴方式比较原版与一个倍率。记录低频嗡声、背景嘶声、左右耳差异，以及切换降噪时的变化。出现尖锐声、啸叫或不适时取下耳机，结束该次测试。

保存倍率、固件哈希、App 哈希、手机系统、双耳升级前后版本和反馈。安装出错时，把阶段、百分比及错误原文一起记下，便于追踪原因。

## 重置连接

3e 说明书的步骤是：双耳放入充电盒、保持开盖，同时长按双耳触控区 15 秒，直到橙灯快速闪烁。完成后白灯闪烁，重新进入配对。

升级中的文件传输、重启安装和固件恢复分别记录在[研究问题](boundaries.md)中，可按实际发生的阶段补充日志。
