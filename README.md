# vivo TWS 3e 固件研究与实验工具

这个项目记录一次从 vivo TWS 3e 官方 OTA 出发，解包、定位 ANC 增益、制作单参数实验包并交叉校验的过程。目标是让别人能复现工具和判断依据，也能看清目前没有验证的部分。

**当前编辑工具只适用于本文指定的 TWS 3e v2.6.3 官方原包。** TWS3、TWS3 Pro、TWS4 的固件不能互刷；其他 3e 版本也不能直接套用偏移。

仓库提供原创 Python 工具、操作说明和研究摘要。官方固件、修改固件、第三方 APK、SDK 库、抓包、手机数据都由使用者自行保管，不放进 Git。

## 从哪里开始

- 想了解已经做了什么：[研究进展](docs/progress.md)。
- 想自己解包和制作：[3e 操作流程](docs/3e-workflow.md)。
- 想了解格式、定位和校验经验：[解包与交叉验证](docs/research.md)。
- 想讨论参数、签名、恢复和结论范围：[讨论边界](docs/boundaries.md)。

## 已有的关键结果

已解析 `oviV` 包头、十段 LZMA、累计 CRC 表及内部镜像 CRC。定位到前馈 ANC 的 `g_ff_adaptive_gain` 启动初值，并通过同芯片 SDK 符号与产品机器码对应。

实验修改的是该初值，原版为 `1.0`。它参与前馈增益计算，不代表整套降噪的总强度。`1.5` 不等于降噪提高 50%。参考 SDK 的相关赋值接口把输入限制在 0～1；vivo 的全部运行时写入路径尚未恢复，超过 1 的实验没有已知安全上限。

使用者反馈：1.01 包刷入后没有变砖；0.50 包的降噪明显减弱。反馈支持参数有实机作用，但不是入耳声学测量，也没有证明提高倍率能持续改善效果。1.25、1.50 目前只有制作和离线验证记录，没有相应实机结果记录。

## 快速复现

需要 Python 3.10+、7-Zip 命令行及 Unicorn 2.1.4。Windows PowerShell 示例：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force input
```

自行取得官方原包，复制为 `input/original_2.6.3.bin`。原包 SHA-256 必须为：

```text
8c83d3492e1a45b1240f5e15e2a2a46745b0954fb123a17af9b102bd96fb4182
```

```powershell
# 检查格式与 CRC，不修改文件
.venv/Scripts/python.exe fwtool.py inspect input/original_2.6.3.bin

# 解包到新的目录
.venv/Scripts/python.exe fwtool.py unpack input/original_2.6.3.bin --output work/original

# 先做中性重建：结果必须与原包逐字节相同
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.0 --output output/control_1.00.bin

# 下例仅展示如何复现已做过的 0.50 对照，不是增强建议
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 0.5 --output output/control_0.50.bin
```

若 `7z` 不在 PATH，给 `build` 或 `verify` 追加 `--sevenzip "C:/Program Files/7-Zip/7z.exe"`。工具只生成本地文件，不连接蓝牙，不刷写设备。

每次 `build` 都执行：

1. 官方原包和解压镜像 SHA-256 检查。
2. 全镜像字节差异白名单检查；包头只允许长度与相关 CRC 字段变化。
3. 原包及候选的全部 20 段数据由 7-Zip 独立解压对照。
4. 用用户提供的原镜像执行原始 CRC 指令、两段应用验包函数和增益设置函数。
5. 破坏载荷、魔数及长度的反例检查。

检查通过后才写出 BIN 和同名 `.verification.json`。已有文件不会覆盖。示例允许的倍率为 `0.50 / 0.99 / 1.00 / 1.01 / 1.25 / 1.50`，这是历史实验列表，不是安全范围。

## 关于安装

本项目没有实现可用的 PC 蓝牙刷写器。[3e 操作流程](docs/3e-workflow.md) 记录了资料中本地固件 APK 的固定文件路径及使用方法；仓库不分发该 APK，也不承诺其安全或适配。数字签名、真正启动程序的行为及失败恢复仍有缺口。

检查通过只证明列出的离线条件成立。它不证明耳内降噪改善、不会啸叫、可以恢复，也不代表包已经适合别人日常使用。

## 本地验证工具

```powershell
$env:TWS3E_ORIGINAL = (Resolve-Path input/original_2.6.3.bin).Path
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

测试需要本地原包；没有原包时相关测试会明确跳过。原始研究的示例哈希见 [已知产物](evidence/known-builds.json)。跨 Python/liblzma 版本的压缩输出可能不同，应同时核对解压内容和差异记录，不能只凭文件名判断。

原创工具和文档采用 MIT 许可证。第三方固件、APK、SDK 及参考资料的权利不因此改变，来源见 [资料出处](docs/sources.md)。
