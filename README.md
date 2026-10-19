# lvgl帧率优化

版本：1.0.0。用于诊断和优化 LVGL 动画与界面实际帧率的项目技能。

显示名称为 **lvgl帧率优化**；工具调用标识和安装目录为 `lvgl-fps-optimization`。

## 安装到项目

在项目根目录运行：

```sh
git clone --branch v1.0.0 --depth 1 https://github.com/squid-232/lvgl-fps-optimization.git .agents/skills/lvgl-fps-optimization
```

也可以下载 Release 中的 `lvgl帧率优化-v1.0.0.zip`，将其中的 `lvgl-fps-optimization` 文件夹解压到项目的 `.agents/skills/` 下。已有同名目录时先比较并备份本地修改。重新打开项目或新建会话后使用：

```text
使用 $lvgl-fps-optimization 分析本项目的实际帧率瓶颈，实施优化并验证帧节拍、视觉与资源释放。
```

## 工作方法

1. 固定屏幕版本、初始化表和背光顺序，先消除花屏、闪屏。
2. 分别测量绘制、显存传输、同步等待和实际交付帧间隔。
3. 按瓶颈选择减少重绘、A8、DMA/PPA、缓存背景、内部SRAM分块或双缓冲。
4. 核实缓存一致性和缓冲所有权，让 VSYNC 调度与 LVGL 定时器协作。
5. 清理对象、动画、任务、定时器及临时内存；允许完全熄屏时再关闭显示链路，并保留恢复路径。
6. 独立验收节拍、完整区间FPS、阶段时序、画面一致性、内存与空闲CPU。

入口为 [SKILL.md](SKILL.md)，详细方法在 [references](references/)。案例中的硬件、依赖补丁和定时器设定必须在目标项目重新验证，不保证任意负载均达60FPS。

## 时间戳分析

Python 3.10+，仅依赖标准库。CSV 含 `timestamp_us` 列，或输入带 `[SPLASH_FRAME_TIMES] us=...` 的日志。

```sh
python scripts/analyze_frames.py frames.csv --target-fps 60 --expected-span-ms 4800 --output result.json
python scripts/analyze_frames.py serial.log --run 2 --target-fps 60 --output result.json
python -m unittest discover -s tests -v
```

多次播放日志必须指定 `--run`。默认平均节拍容差0.2%，最大帧间隔不得超过目标周期的1.08倍。退出码：0为节拍接受、1为不达标、2为输入错误。未指定覆盖时长时显示 `NOT_CHECKED`。

**脚本PASS仅证明输入时间戳的节拍及已请求的覆盖检查。** 它不验证打点语义、真实屏幕扫描、视觉一致性、退出释放或完整L2验收。

## 包内容与验证

包含技能入口、界面元数据、四份参考文档、一个分析脚本及九项单元测试。发布包不包含项目固件、品牌素材、私有原始日志或账号配置。ZIP校验值见 Release 附件 `SHA256SUMS.txt`。
