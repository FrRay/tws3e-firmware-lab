# TWS 3e：从原包到手机的操作流程

## 1. 先确认型号与原包

在耳机 App 中核对型号为 **TWS 3e**，记录左右耳版本。保留官方原包和每个实验包的文件名、SHA-256、校验记录。不同型号的 BIN 不能混用。

当前工具绑定的是 v2.6.3、项目 DPD2321A、芯片 best1306 的这一个官方原包。不能把另一个版本改名为 `original_2.6.3.bin` 来代替；工具会核对完整哈希。

按 README 安装 Python 依赖和 7-Zip，再运行：

```powershell
.venv/Scripts/python.exe fwtool.py inspect input/original_2.6.3.bin
.venv/Scripts/python.exe fwtool.py unpack input/original_2.6.3.bin --output work/original
```

## 2. 制作并复核

先验证 1.00 的中性重建。实验时每次从**官方原包**重新制作，不在前一份实验包上叠加修改。

```powershell
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.0 --output output/control_1.00.bin
.venv/Scripts/python.exe fwtool.py build --original input/original_2.6.3.bin --scale 1.25 --output output/experiment_1.25.bin
```

第二条是复现既有研究包的示例，不是推荐倍率。1.25 的声学稳定性未验证。需要验证已有文件时：

```powershell
.venv/Scripts/python.exe fwtool.py verify --original input/original_2.6.3.bin --candidate output/experiment_1.25.bin --scale 1.25 --report output/verify_again_1.25.json
```

打开校验 JSON，确认：

- `checks_complete` 为 `true`，且请求的 `scale` 正确。
- 镜像只有 `0x1c3e20` 浮点字段和内部 CRC 文本变化；中性包应完全无变化。
- 没有型号、版本、地址、代码或其他系数变化。
- 7-Zip、原始 CRC、原始应用验包及增益函数检查通过。

安装前可用 `Get-FileHash output/experiment_1.25.bin -Algorithm SHA256` 与 JSON 中的 `candidate.sha256` 核对。

## 3. 本地固件版 APK 的操作

原研究资料中有 `vivotws_local_FW.apk`。已静态核对的 APK SHA-256：

```text
5336b406ee17451e5af3033183ec03d127eb76786fcce395d75b6c104b3f02a0
```

这只是识别研究样本，不是安全认证。不同哈希的 APK 不在这份代码核对的范围内；不要照搬资料里“报毒正常，直接绕过”的说法。仓库未提供下载地址或完整安全审计。

1. 在安卓手机安装你自行取得的该 APK。若与官方版发生签名冲突，先确认提示；卸载官方 App 会清除它的应用数据。不要为了安装去修改手机系统组件。
2. 把选定的**完整 OTA BIN**复制一份，命名为 `update.bin`，不要解压。
3. 放到手机内部存储最外层的 `vivotws` 文件夹。完整路径为 `/sdcard/vivotws/update.bin`，不是 `/sdcard/Download/vivotws/update.bin`。
4. 核对手机上的文件大小和哈希，防止选错包；如果手机文件管理器不支持哈希，可通过 USB 复制回电脑核对。保留原实验文件名的备份，避免多个 `update.bin` 混淆。
5. 完全退出并重新打开 App，允许正常连接蓝牙所需权限；如果提示文件访问权限，允许读取。确认识别到 TWS 3e 和双耳状态。
6. 进入耳机固件更新页面，按 App 对电量及耳机放置的提示操作，点击开始更新。保持连接，等待明确的完成结果和重新连接。

这个 APK 把更新元数据中的目标版本设成 `2147483647`，使 App 侧认为有新版本；实际文件来源固定为上述本地路径。**页面上的版本、长度或更新说明不能用来证明选对了文件。** App 侧通过不代表耳机已通过验包或安装完成。

## 4. 成功与失败怎么记录

至少记录：原版及候选哈希、倍率、App 样本哈希、手机系统、双耳升级前后版本、是否恢复连接、左右耳播放及 ANC 是否正常。

同型号、同设备、同噪声、相同佩戴与降噪模式下比较。先确认没有异常声，再做听感对照；尖锐声、啸叫或不适出现时取下耳机并停止该实验。听感记录不能直接换算成降噪 dB。

若失败，保存阶段、百分比和完整错误信息。不要在不知道失败原因时改版本号或换其他型号包继续刷。

## 5. 重置与救砖的区别

3e 说明书给出的重置方式：双耳放盒内、开盖，同时长按双耳触控区 15 秒，直到橙灯快速闪烁；完成后白灯闪烁并进入配对。它可用于连接异常排查，说明书没有把它描述成固件重刷或回滚入口。

本项目未获得实际启动程序备份，未验证启动失败回退、安装阶段断电恢复或可用硬件救砖路径。传输中断后能重试，也不能证明坏程序启动失败后能恢复。保留官方包很重要，但仅有官方包并不构成救砖办法。
