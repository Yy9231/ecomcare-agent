from dataclasses import dataclass


@dataclass(frozen=True)
class ProductKnowledge:
    introduction: str
    specifications: str


# 以 SKU 为稳定键维护合成商品资料，启动时会转成产品介绍和详细参数两类知识文档。
PRODUCT_KNOWLEDGE: dict[str, ProductKnowledge] = {
    "EC-SKU-001": ProductKnowledge(
        "Aurora X1 是面向日常影像、社交和移动办公的轻薄 5G 手机，主打高刷直屏、全天续航与多设备协同。",
        "屏幕：6.55 英寸 OLED，2400×1080，120Hz；处理器：Aster A8；内存：8GB；存储：256GB；后置相机：5000 万主摄+1200 万超广角；前置相机：1600 万；电池：4700mAh；充电：66W 有线；网络：双卡 5G、Wi-Fi 6、蓝牙 5.3；防护：IP54；重量：约 186g。",
    ),
    "EC-SKU-002": ProductKnowledge(
        "Aurora X1 Pro 是强调性能、长焦影像和户外可靠性的旗舰 5G 手机，适合重度应用与视频创作。",
        "屏幕：6.78 英寸 LTPO OLED，2800×1260，1-120Hz；处理器：Aster X9；内存：12GB；存储：512GB；后置相机：5000 万主摄+5000 万超广角+6400 万潜望长焦；前置相机：3200 万；电池：5100mAh；充电：100W 有线、50W 无线；网络：双卡 5G、Wi-Fi 7、蓝牙 5.4、NFC；防护：IP68；重量：约 212g。",
    ),
    "EC-SKU-003": ProductKnowledge(
        "NovaPad 11 是适合影音娱乐、网课和轻办公的 11 英寸平板，支持手写笔与分屏多任务。",
        "屏幕：11 英寸 LCD，2560×1600，120Hz；处理器：Nova N7；内存：8GB；存储：256GB；电池：8300mAh；充电：45W USB-C；摄像头：后置 1300 万、前置 800 万；音频：四扬声器；连接：Wi-Fi 6、蓝牙 5.2；扩展：支持磁吸键盘和 4096 级压感笔；重量：约 490g。",
    ),
    "EC-SKU-004": ProductKnowledge(
        "NovaPad Mini 是便携阅读、游戏和差旅使用的小尺寸平板，可单手握持并支持蜂窝网络版本。",
        "屏幕：8.7 英寸 LCD，2400×1504，90Hz；处理器：Nova M6；内存：6GB；存储：128GB；扩展：microSD 最高 1TB；电池：6500mAh；充电：30W USB-C；摄像头：后置 1200 万、前置 800 万；连接：Wi-Fi 6、蓝牙 5.2、可选 5G；重量：约 335g。",
    ),
    "EC-SKU-005": ProductKnowledge(
        "EchoBuds 3 是主打舒适佩戴与通勤降噪的真无线耳机，支持双设备连接和低延迟模式。",
        "单元：11mm 动圈；降噪：最高 42dB 主动降噪；麦克风：每侧 3 麦；编解码：AAC、SBC；连接：蓝牙 5.3；单次续航：约 7 小时，关闭降噪约 9 小时；综合续航：约 32 小时；充电：USB-C，充电 10 分钟播放约 2 小时；防护：IP54；单耳重量：约 4.8g。",
    ),
    "EC-SKU-006": ProductKnowledge(
        "EchoBuds Pro 是面向高品质音乐和频繁会议的旗舰真无线耳机，提供自适应降噪与空间音频。",
        "单元：10.8mm 双磁路动圈；降噪：最高 50dB 自适应主动降噪；麦克风：骨传导+三麦阵列；编解码：LDAC、AAC、SBC；连接：蓝牙 5.4、双设备；单次续航：约 6.5 小时，关闭降噪约 8.5 小时；综合续航：约 30 小时；充电：USB-C、Qi 无线；防护：IP55；单耳重量：约 5.2g。",
    ),
    "EC-SKU-007": ProductKnowledge(
        "VisionBook 14 是兼顾便携和生产力的 14 英寸轻薄本，适合编程、文档与移动办公。",
        "屏幕：14 英寸 IPS，2880×1800，120Hz，100% sRGB；处理器：Core Ultra 5 级；内存：16GB LPDDR5X；硬盘：1TB PCIe 4.0 SSD；显卡：集成显卡；电池：70Wh；接口：雷电 4×2、USB-A×2、HDMI 2.1、3.5mm；无线：Wi-Fi 6E、蓝牙 5.3；摄像头：1080p；重量：约 1.35kg。",
    ),
    "EC-SKU-008": ProductKnowledge(
        "VisionBook 16 是为内容创作和多任务设计的大屏性能本，配备独立显卡与双风扇散热。",
        "屏幕：16 英寸 IPS，2560×1600，165Hz，100% DCI-P3；处理器：Core Ultra 7 级；内存：32GB DDR5；硬盘：1TB PCIe 4.0 SSD，预留 M.2；显卡：8GB 独立显卡；电池：85Wh；接口：雷电 4、USB-C、USB-A×2、HDMI 2.1、RJ45、SD 卡槽；无线：Wi-Fi 7；重量：约 2.05kg。",
    ),
    "EC-SKU-009": ProductKnowledge(
        "Pulse Watch 5 是支持运动记录、睡眠分析和消息提醒的智能手表，适合日常健康管理。",
        "屏幕：1.43 英寸 AMOLED，466×466；材质：铝合金表壳；定位：双频 GPS；传感器：心率、血氧、加速度、陀螺仪、气压计；运动模式：100+；续航：典型 10 天，重度 5 天；充电：磁吸无线；防水：5ATM；连接：蓝牙 5.3、NFC；兼容：Android 9/iOS 13 及以上。",
    ),
    "EC-SKU-010": ProductKnowledge(
        "Pulse Band 是轻量化健康手环，面向步数、睡眠和基础运动监测，适合长时间佩戴。",
        "屏幕：1.62 英寸 AMOLED，192×490；传感器：心率、血氧、加速度；运动模式：120；续航：典型 14 天；充电：磁吸触点；防水：5ATM；连接：蓝牙 5.2；腕带：可拆卸 TPU，适配 135-210mm 腕围；重量：不含腕带约 16g。",
    ),
    "EC-SKU-011": ProductKnowledge(
        "PixelCam 4K 是适合旅行、直播和短视频创作的可换镜头相机，支持机身防抖和 4K 高帧率视频。",
        "传感器：APS-C 2600 万像素；卡口：PC-M；防抖：五轴机身防抖；视频：4K 60fps、1080p 120fps；对焦：相位+对比度混合，425 点；连拍：最高 15 张/秒；屏幕：3 英寸侧翻触控；取景器：236 万点 OLED；存储：UHS-II SD；接口：USB-C、Micro HDMI、3.5mm 麦克风；重量：约 510g。",
    ),
    "EC-SKU-012": ProductKnowledge(
        "PixelCam Mini 是面向随手记录与视频博客的口袋相机，提供翻转屏和智能追踪对焦。",
        "传感器：1 英寸 2000 万像素；镜头：等效 24-70mm F1.8-2.8；防抖：光学+电子；视频：4K 30fps、1080p 120fps；对焦：眼部与人脸追踪；屏幕：3 英寸上翻触控；存储：microSD UHS-I；连接：Wi-Fi 5、蓝牙 5.1；接口：USB-C、3.5mm 麦克风；重量：约 295g。",
    ),
    "EC-SKU-013": ProductKnowledge(
        "AirHub AX6000 是适合千兆宽带、多人游戏和智能家居的双频 Wi-Fi 6 路由器。",
        "无线规格：Wi-Fi 6 AX6000；频段：2.4GHz 1148Mbps+5GHz 4804Mbps；天线：8 根高增益；处理器：四核 2.0GHz；内存：512MB；网口：2.5GbE WAN/LAN×1、千兆 LAN×3；并发设备：约 256 台；功能：OFDMA、MU-MIMO、160MHz、WPA3、访客网络；尺寸：约 270×180×55mm。",
    ),
    "EC-SKU-014": ProductKnowledge(
        "AirHub Mesh 是用于大户型覆盖的双节点 Mesh 套装，支持有线回程和无缝漫游。",
        "无线规格：双频 Wi-Fi 6 AX3000；单节点速率：2.4GHz 574Mbps+5GHz 2402Mbps；套装：2 节点；覆盖：开放环境约 300㎡；网口：每节点千兆自适应网口×3；回程：无线或以太网；并发设备：约 150 台；功能：802.11k/v/r、WPA3、家长控制；单节点尺寸：约 110×110×185mm。",
    ),
    "EC-SKU-015": ProductKnowledge(
        "PowerGo 65W 是适合手机、平板和轻薄本出行使用的氮化镓充电器，可同时为三台设备供电。",
        "总功率：65W；接口：USB-C×2、USB-A×1；单口输出：USB-C1 最高 65W，USB-C2 最高 30W，USB-A 最高 22.5W；协议：PD 3.0、PPS、QC 3.0；输入：100-240V 50/60Hz；插脚：可折叠；保护：过压、过流、过温、短路；尺寸：约 66×38×31mm；重量：约 120g。",
    ),
    "EC-SKU-016": ProductKnowledge(
        "PowerGo 100W 是面向高性能笔记本和多设备桌面的四口氮化镓充电器，支持动态功率分配。",
        "总功率：100W；接口：USB-C×3、USB-A×1；单口输出：USB-C1/C2 最高 100W，USB-C3 最高 30W，USB-A 最高 22.5W；协议：PD 3.1、PPS、QC 4+；输入：100-240V 50/60Hz；功率分配：双口 65W+35W；保护：过压、过流、过温、短路；尺寸：约 75×48×32mm；重量：约 210g。",
    ),
    "EC-SKU-017": ProductKnowledge(
        "KeyFlow 是适合办公和游戏的三模机械键盘，支持热插拔、自定义灯效与多系统键位。",
        "布局：87 键 TKL；轴体：线性轴，约 45gf；结构：Gasket；键帽：PBT 双色；连接：USB-C、2.4GHz、蓝牙 5.1；设备切换：最多 3 台蓝牙设备；电池：4000mAh；续航：关闭灯效约 180 小时；热插拔：支持 3/5 脚轴；回报率：有线/2.4GHz 1000Hz；系统：Windows、macOS、Linux。",
    ),
    "EC-SKU-018": ProductKnowledge(
        "ClickPro 是兼顾人体工学和精准操控的无线鼠标，支持跨设备切换与静音按键。",
        "传感器：最高 26000 DPI；按键：7 个可编程；连接：2.4GHz、蓝牙 5.2、USB-C 有线；回报率：最高 1000Hz；电池：500mAh；续航：蓝牙约 90 天；充电：USB-C；微动：静音机械微动；板载配置：3 组；重量：约 78g；兼容：Windows、macOS。",
    ),
    "EC-SKU-019": ProductKnowledge(
        "ViewMax 27 是面向设计、编程和影音的 27 英寸 4K 显示器，支持 USB-C 一线连接。",
        "面板：27 英寸 IPS；分辨率：3840×2160；刷新率：60Hz；色域：100% sRGB、95% DCI-P3；色准：平均 ΔE<2；亮度：400nit；HDR：DisplayHDR 400；接口：USB-C 90W、HDMI 2.0×2、DP 1.4、USB-A×3；支架：升降、旋转、俯仰；VESA：100×100mm。",
    ),
    "EC-SKU-020": ProductKnowledge(
        "ViewMax 32 是适合多窗口办公和专业内容查看的 32 英寸 4K 显示器，内置 KVM 与多画面功能。",
        "面板：31.5 英寸 IPS；分辨率：3840×2160；刷新率：75Hz；色域：100% sRGB、98% DCI-P3；色准：平均 ΔE<2；亮度：450nit；HDR：DisplayHDR 600；接口：USB-C 100W、HDMI 2.1×2、DP 1.4、USB-A×4、RJ45；功能：KVM、PBP/PIP；VESA：100×100mm。",
    ),
    "EC-SKU-021": ProductKnowledge(
        "SoundBar S2 是面向电视影音和客厅音乐的 2.1 声道回音壁，配有无线低音炮。",
        "声道：2.1；总功率：240W；单元：全频单元×4、高音单元×2、6.5 英寸无线低音炮；音效：虚拟环绕、对白增强、夜间模式；输入：HDMI eARC、光纤、AUX、USB；无线：蓝牙 5.3；格式：PCM、Dolby Audio；回音壁尺寸：约 900×65×95mm；壁挂：支持。",
    ),
    "EC-SKU-022": ProductKnowledge(
        "GameDock 是为笔记本、掌机和多屏桌面设计的 USB-C 扩展坞，可同时连接显示器、网络和外设。",
        "上行接口：USB-C 10Gbps；视频：HDMI 2.1×1、DP 1.4×1，单屏最高 4K 120Hz；数据：USB-C 10Gbps×1、USB-A 10Gbps×2、USB-A 5Gbps×2；网络：2.5GbE；读卡：SD/microSD UHS-I；音频：3.5mm；供电：PD 输入最高 100W，向主机输出最高 85W；系统：Windows、macOS、Linux。",
    ),
    "EC-SKU-023": ProductKnowledge(
        "PocketSSD 1TB 是用于照片、视频和项目文件高速传输的便携固态硬盘，采用抗摔金属机身。",
        "容量：1TB；接口：USB 3.2 Gen 2 Type-C；顺序读取：最高 1050MB/s；顺序写入：最高 1000MB/s；闪存：3D NAND；加密：AES-256 软件加密；防护：IP55，约 2 米抗跌落；线材：USB-C to C、USB-C to A；系统：Windows、macOS、Android；尺寸：约 88×48×10mm；重量：约 58g。",
    ),
    "EC-SKU-024": ProductKnowledge(
        "PocketSSD 2TB 是面向 4K 素材和大容量备份的高速便携固态硬盘，支持 USB 20Gbps。",
        "容量：2TB；接口：USB 3.2 Gen 2×2 Type-C；顺序读取：最高 2000MB/s；顺序写入：最高 1900MB/s；闪存：3D NAND；加密：AES-256 软件加密；防护：IP55，约 2 米抗跌落；线材：USB-C to C；系统：Windows、macOS、Android；尺寸：约 92×52×12mm；重量：约 72g。",
    ),
    "EC-SKU-025": ProductKnowledge(
        "HomeEye 是支持远程看家、移动侦测和双向通话的室内智能摄像头，具备隐私遮蔽功能。",
        "分辨率：2560×1440；镜头：F1.6，水平视角 110°；云台：水平 360°、垂直 105°；夜视：940nm 红外，无红光；检测：人形、移动、哭声；音频：双向通话；存储：microSD 最高 256GB、可选云存储；网络：2.4GHz Wi-Fi；供电：5V/2A USB-C；隐私：物理镜头遮蔽。",
    ),
    "EC-SKU-026": ProductKnowledge(
        "PrintGo 是适合家庭作业和小型办公的彩色喷墨一体机，支持自动双面与无线打印。",
        "功能：打印、复印、扫描；打印方式：四色墨仓喷墨；最高分辨率：4800×1200dpi；速度：黑白约 15ipm、彩色约 8ipm；双面：自动；进纸：150 张；扫描：1200×2400dpi 平板；纸张：A4、A5、照片纸；连接：USB、2.4/5GHz Wi-Fi、Wi-Fi Direct；移动打印：iOS、Android；显示：2.4 英寸彩屏。",
    ),
    "EC-SKU-027": ProductKnowledge(
        "CleanBot 是集扫地、拖地、自动集尘与拖布清洗于一体的智能清洁机器人。",
        "导航：激光雷达+结构光避障；吸力：最高 8000Pa；尘盒：350mL；水箱：80mL；基站集尘袋：3L；拖地：双旋转拖布，自动抬升 10mm；电池：5200mAh；续航：约 180 分钟；越障：最高 20mm；噪声：标准档约 65dB；连接：2.4GHz Wi-Fi；功能：分区、禁区、多楼层地图。",
    ),
    "EC-SKU-028": ProductKnowledge(
        "AirPure 是面向卧室和客厅的智能空气净化器，可监测颗粒物并自动调节净化强度。",
        "适用面积：35-60㎡；颗粒物 CADR：500m³/h；甲醛 CADR：250m³/h；滤芯：初效+活性炭+H13 HEPA；传感器：PM2.5、温度、湿度；噪声：睡眠档约 22dB；功率：最高 55W；显示：OLED；连接：2.4GHz Wi-Fi；功能：自动模式、童锁、滤芯寿命提醒；尺寸：约 270×270×600mm。",
    ),
    "EC-SKU-029": ProductKnowledge(
        "CookVision 是带可视窗和智能菜单的家用空气炸锅，支持烘烤、复热与预约。",
        "容量：6L；额定功率：1700W；温度范围：40-200℃；定时：1-60 分钟，低温模式最长 12 小时；加热：顶部热风循环；菜单：12 种预设；操控：触控屏+旋钮；内胆：食品接触级不粘涂层，可拆洗；功能：预约、保温、翻面提醒、断电记忆；尺寸：约 330×280×310mm。",
    ),
    "EC-SKU-030": ProductKnowledge(
        "SmartLamp Pro 是用于阅读、学习和桌面办公的智能台灯，支持自动调光与多设备控制。",
        "光源：全光谱 LED；额定功率：18W；照度：中心最高 1800lx；色温：2700-6500K；显色指数：Ra≥95、R9≥90；调光：无级亮度与色温；频闪：通过无可视频闪测试；控制：触控、App、语音；连接：2.4GHz Wi-Fi、蓝牙；定时：番茄钟、延时关灯；灯臂：三轴调节；供电：24V DC。",
    ),
}


def product_documents(sku: str, name: str) -> list[dict[str, str]]:
    knowledge = PRODUCT_KNOWLEDGE[sku]
    return [
        {
            "title": f"{name} 产品介绍",
            "source": f"商品介绍/{sku}",
            "content": knowledge.introduction,
        },
        {
            "title": f"{name} 详细参数",
            "source": f"详细参数/{sku}",
            "content": knowledge.specifications,
        },
    ]


def product_embedding_text(document: dict[str, str]) -> str:
    return (document["title"] + "。") * 3 + document["content"]
