# 参考项目与资料

## 固件与协议研究

- [TWS-Pods-PC](https://github.com/Zhaoyi-ya/TWS-Pods-PC)：vivo / iQOO 等耳机的 PC 控制和协议记录。研究安装入口时参考其 vivo 协议文档；README 的品牌总览和快速开始也为本仓库的文档组织提供了参考。
- [Binwalk](https://github.com/ReFirmLabs/binwalk)：固件内容识别与提取。README 先介绍工具用途，再给安装与使用入口，本仓库沿用了这种面向使用者的介绍顺序。
- [Firmware Mod Kit](https://github.com/rampageX/firmware-mod-kit)：固件提取和重建工具集合。参考其按解包、修改、重建展开的使用流程。

本地资料中的 `VIVOTWS/readme.txt` 介绍了 TWS5 之前 vivo / iQOO 耳机的本地固件 App 使用方法。研究时将这条安装线索与实际文件头、芯片和镜像结构结合，分别整理 BES 与 QCC 路线。

## BES 芯片、ANC 和 OTA

[sprlightning/audio_prj_collections](https://github.com/sprlightning/audio_prj_collections/tree/2549bb7583b6554763b12ae7c58805e14e597fda/BES2700IHC/2700-src)，固定提交 `2549bb7583b6554763b12ae7c58805e14e597fda`。

其中 `lib/bes/best1306_libmultimedia_romaac_rom_reduce_aac_cp_anc.a` 的 `anc_process_best1306.o` 保留函数及数据符号，用于对应 3e 中的增益函数和 `g_ff_adaptive_gain`。接口声明位于 `services/multimedia/audio/process/anc/include/anc_process.h`。

`services/ota/bes_ota/inc/ota_control.h` 和 `utils/lzma/bes_lzma_utils.c` 用于对照 OTA 交接及压缩复制，结构差异记录在[解包与参数定位](research.md)。

## QCC 参数与模块

[TrellixVulnTeam/QCC3040_Earbud_3ZLT](https://github.com/TrellixVulnTeam/QCC3040_Earbud_3ZLT/tree/6573778809e5f6794d496933a2d9ecaf45f2b422)，固定提交 `6573778809e5f6794d496933a2d9ecaf45f2b422`。用于核对 TWS3、TWS3 Pro、TWS4 样本中的参数字段、模块身份和音频处理结构。

## 使用说明与声学资料

- [TWS 3e 说明书 PDF](https://object.pscloud.io/cms/cms/Uploads/product_630700_instruction_dyCY6q.pdf)：配对、15 秒触控重置及 App 更新入口。
- [MathWorks ANC 示例](https://www.mathworks.com/help/audio/ug/active-noise-control-using-a-filtered-x-lms-fir-adaptive-filter.html)：了解扬声器到误差麦克风的声学路径，以及控制器与残余噪声之间的关系。

原包哈希和既有构建结果见[实验记录](../evidence/known-builds.json)。本仓库的原创代码与文档采用 MIT 许可证，引用项目保留各自许可证。
