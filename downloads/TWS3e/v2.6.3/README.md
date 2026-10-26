# TWS 3e v2.6.3

| 文件 | 参数倍率 | 记录 |
|---|---|---|
| [original.bin](original.bin?raw=true) | 1.00，官方原版 | [重建及校验](checks/original.verification.json) |
| [ff-0.50.bin](ff-0.50.bin?raw=true) | 0.50 | [校验](checks/ff-0.50.verification.json)，刷入后反馈降噪减弱 |
| [ff-0.99.bin](ff-0.99.bin?raw=true) | 0.99 | [校验](checks/ff-0.99.verification.json) |
| [ff-1.01.bin](ff-1.01.bin?raw=true) | 1.01 | [校验](checks/ff-1.01.verification.json)，已刷入，反馈没有变砖 |
| [ff-1.25.bin](ff-1.25.bin?raw=true) | 1.25 | [校验](checks/ff-1.25.verification.json) |
| [ff-1.50.bin](ff-1.50.bin?raw=true) | 1.50 | [校验](checks/ff-1.50.verification.json) |

修改包调整同一前馈降噪比例初值，并更新长度和 CRC。型号、版本、程序和滤波系数与原包一致。

选择一份完整 BIN，复制到手机并命名为 `/sdcard/vivotws/update.bin`，使用[本地固件版 App](../../app/vivotws_local_FW.apk?raw=true)安装。完整步骤见[安装说明](../../../docs/3e-workflow.md)。
