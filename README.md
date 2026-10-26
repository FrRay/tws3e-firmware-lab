# vivo / iQOO TWS 固件研究

从一次 TWS 3e 的升级推送开始，追踪耳机固件的下载、解包、ANC 参数和本地刷写。

项目起初想弄清楚一件事：耳机更新后，降噪到底改了什么？为此收集了 vivo 多款耳机的不同版本固件，比较参数和程序，随后在 3e 上找到前馈 ANC 增益，做出了完整修改包。1.01 倍固件已经刷入；换成 0.50 倍后，实验者听到降噪明显减弱。

这里保存这一路的研究经过、可复现的工具，以及从原包制作到手机安装的操作方法。读者可以直接复现 3e 实验，也可以沿着同样的方法研究其他 vivo / iQOO 耳机。

## 项目里有什么

| 内容 | 入口 |
|---|---|
| 从抓包到刷入的完整经过，包括走过的弯路 | [研究经过](docs/progress.md) |
| 准备环境、制作固件、使用本地固件 App | [3e 操作流程](docs/3e-workflow.md) |
| 包头、LZMA、CRC、SDK 符号和机器码对照 | [解包与参数定位](docs/research.md) |
| 跨型号分析、增益实验、签名和恢复的后续研究 | [研究问题](docs/boundaries.md) |
| 已制作包的哈希与校验结果 | [实验记录](evidence/known-builds.json) |

## 从 3e 出发，研究其他型号

资料中的本地固件 App 教程覆盖了 TWS5 之前的 vivo / iQOO 产品。对这些耳机，抓取升级请求、保存原包、识别封装、比较版本、寻找校验函数和分析安装流程，都可以沿用这次的思路。

现有样本分成两条路线：TWS 3e 使用 BES best1306，包头为 `oviV`；TWS3、TWS3 Pro、TWS4 的样本使用 QCC 封装，包头为 `APPUHDR5`。解析从文件头和芯片信息入手，再选择对应的解包方法。系列名称和上市先后可以帮助找资料，真正决定解析方式的是拿到的文件。

3e v2.6.3 是工具里的第一个固件配置，记录了源文件哈希、镜像布局、参数位置和函数入口。后续型号可以继续补充自己的配置和解析器。

## 已经做成的事情

- 拆开了 3e 的 512 字节包头、十段 LZMA 和多层 CRC，并做到了原包无修改重建后逐字节一致。
- 通过 BEST1306 SDK 的符号和编译对象，将 `g_ff_adaptive_gain` 对应到 3e 的实际机器码及启动数据。
- 制作了 `0.50 / 0.99 / 1.00 / 1.01 / 1.25 / 1.50` 六个倍率的完整包，并交叉核对解压、校验和增益计算。
- 分析了本地固件版 App 的固定文件入口与版本判断，完成了 1.01、0.50 的实机尝试和反馈记录。
- 比较了 TWS3、TWS3 Pro、TWS4 的 12 份固件，追到了 ANC 初始化、增益恢复、DSP 时钟和音乐链增益等具体变化。

## 快速开始

准备 Python 3.10+ 和 7-Zip 命令行。在 Windows PowerShell 中运行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force input
```

把官方 TWS 3e v2.6.3 原包放到 `input/original_2.6.3.bin`，依次检查、解包并重建：

```powershell
.venv/Scripts/python.exe fwtool.py inspect input/original_2.6.3.bin
.venv/Scripts/python.exe fwtool.py unpack input/original_2.6.3.bin --output work/original
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.0 --output output/control_1.00.bin
```

`1.0` 重建包应与原包完全相同。再制作一个 0.50 倍对照：

```powershell
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 0.5 --output output/control_0.50.bin
```

每次构建都会运行字节差异检查、7-Zip 独立解压、原始 ARM CRC、应用验包函数和增益函数，生成 BIN 及同名 `.verification.json`。`7z` 的路径设置、原包哈希和其他倍率的命令见[操作流程](docs/3e-workflow.md)。

手机端安装时，把完整 BIN 命名为 `update.bin`，放到 `/sdcard/vivotws/update.bin`，通过本地固件版 App 的更新页面安装。

## ANC 实验进展

这次修改的是前馈通路的一个增益比例，原始值为 `1.0`。0.50 倍实验提供了明显的听感变化：降噪减弱，说明继续研究这个字段有实际价值。1.25 和 1.50 已完成制作及离线检查，后续将比较它们对低频噪声、底噪和佩戴状态的影响。

前馈幅度、反噪声相位和耳机声学结构共同决定残余噪声。下一步会追踪运行时增益更新，并结合低频滤波实验寻找更合适的调法。完整记录见[研究经过](docs/progress.md)。

## 运行测试

```powershell
$env:TWS3E_ORIGINAL = (Resolve-Path input/original_2.6.3.bin).Path
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

七项测试覆盖原包重建、参数变化、错误型号字段、损坏载荷、异常 LZMA 和输入检查。六个倍率的产物已与早期工具的结果逐字节对照，哈希保存在[实验记录](evidence/known-builds.json)。

欢迎补充其他型号的文件格式、版本对比、安装日志和听感记录。提交前将设备标识与账号信息脱敏，讨论时附上型号、版本、文件哈希和复现步骤。

工具与文档采用 MIT 许可证。固件、APK 和 SDK 文件自行准备；引用项目与资料见[资料出处](docs/sources.md)。
