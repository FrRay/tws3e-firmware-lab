# 资料出处与复现线索

仓库没有打包第三方二进制或 SDK 源码。下面是定位字段和核对接口时用过的公开资料，不代表对应厂商认可本项目的修改。

- **BES 同芯片符号参考**：[sprlightning/audio_prj_collections](https://github.com/sprlightning/audio_prj_collections/tree/2549bb7583b6554763b12ae7c58805e14e597fda/BES2700IHC/2700-src)，固定提交 `2549bb7583b6554763b12ae7c58805e14e597fda`。其中 `lib/bes/best1306_libmultimedia_romaac_rom_reduce_aac_cp_anc.a` 的 `anc_process_best1306.o` 提供函数及数据符号；`services/multimedia/audio/process/anc/include/anc_process.h` 提供接口声明。参考仓库名称与设备芯片名称不可混为一谈。
- **OTA 头及压缩复制对照**：上述固定提交下的 `services/ota/bes_ota/inc/ota_control.h`、`utils/lzma/bes_lzma_utils.c`。其结构与 vivo 已追踪实现存在差异，只作参考，不作救砖依据。
- **QCC 字段参考**：[TrellixVulnTeam/QCC3040_Earbud_3ZLT](https://github.com/TrellixVulnTeam/QCC3040_Earbud_3ZLT/tree/6573778809e5f6794d496933a2d9ecaf45f2b422)，固定提交 `6573778809e5f6794d496933a2d9ecaf45f2b422`。用于其他型号参数和模块身份核对，不能移植到 BES 3e。
- **控制协议参考**：[Zhaoyi-ya/TWS-Pods-PC](https://github.com/Zhaoyi-ya/TWS-Pods-PC)。其控制功能不等于已实现完整 3e OTA 与恢复流程；当前仓库没有复制其代码。
- **3e 使用说明**：[制造商说明书的 PDF 镜像](https://object.pscloud.io/cms/cms/Uploads/product_630700_instruction_dyCY6q.pdf)。核对了双耳触控 15 秒重置方式，不把它解释成固件回滚。
- **ANC 声学路径解释**：[MathWorks ANC 示例](https://www.mathworks.com/help/audio/ug/active-noise-control-using-a-filtered-x-lms-fir-adaptive-filter.html)。用于解释次级声学路径的重要性，不代表 3e 使用示例的 FxLMS 算法。

原包 SHA-256 和既有产物的校验结果摘要保存在 `evidence/known-builds.json`。地址均绑定该原包，不是通用 BES 调参地址。
