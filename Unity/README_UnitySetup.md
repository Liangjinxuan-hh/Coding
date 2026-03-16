# Unity 快速集成说明（轻量滴动仪交互界面）

概述：本说明给出在 Unity 2022.3 中快速搭建“模型展示 + 按钮控制 + 串口/手势联动”的最小可运行方案。

步骤：

1. 导入模型
   - 使用 Blender 将滴动仪拆分为两个物体：主体底座（Base）和上表面核心部件（TopPart）。
   - 导出为 FBX 并导入 Unity。将上表面命名为 `TopPart`（或将控制脚本挂到对应子物体）。

2. 场景搭建
   - 新建场景，放置模型，创建一个主相机并把 `CameraOrbit` 脚本挂到主相机上，设置 `target` 为模型中心或 `TopPart` 的父物体。
   - 创建一个 Canvas（Screen Space - Overlay），在底部横向放置 5 个按钮，分别命名为 Btn_Up、Btn_Down、Btn_RotateLeft、Btn_RotateRight、Btn_Stop。
   - 在右上角放一个 `Text`（或 TextMeshPro），用于显示状态，命名为 StatusText。

3. 挂载脚本与绑定
   - 将 `TopPartController.cs` 挂载到 `TopPart`（或其控制空物体）上。
     - 在 Inspector 中将按钮拖入 `btnUp`、`btnDown`、`btnRotateLeft`、`btnRotateRight`、`btnStop`。
     - 将右上角的 `StatusText` 拖入 `statusText`。
   - 若需要语音模块（LD3320）或其他串口设备，将 `SerialCommandBridge.cs` 挂到场景空物体上，并在 Inspector 中设置 `portName` 和 `baudRate`，把 `controller` 指向 `TopPartController`。
   - 若使用外部手势处理器可向 UDP 端口发送文本命令（例如“上移”/"UP"），则把 `GestureCommandBridge.cs` 挂到空物体上并设定 `listenPort` 与 `controller`。

4. 串口数据格式（建议）
   - 直接发送单行文本（带换行）：上移、下移、左转、右转、停止；也支持英文 UP/DOWN/LEFT/RIGHT/STOP。

5. 手势数据格式（UDP 占位实现）
   - 从外部设备向 Unity 运行机器发送 UDP 文本，例如向 192.168.1.100:5005 发送 “上移”。

6. 单元测试（在 Unity 编辑器中）
   - 运行场景，在 Inspector 手动点击按钮，验证 `TopPart` 上下移动与旋转。
   - 若连接串口，确认串口设备发送文本后 Unity 能触发对应动作。
   - 可用 `nc` 或 `socat` 等工具向 UDP 端口发送测试命令以验证手势桥接。

注意事项：
 - 脚本中统一使用主线程更新 Unity 对象（串口/UDP 读取在子线程入队，Update 中出队并调用 controller）。
 - Unity 单位与物理单位需约定（示例中参数以 cm 为语义，实际在 Unity 中按比例设置）。
 - 若使用 TextMeshPro，请将 `Text` 替换为 `TMP_Text` 并修改脚本引用。

可以的后续改进：
 - 使用更健壮的协议（JSON 包含参数）替代简单文本，便于扩展。
 - 在界面加入速度与行程调节滑条。
 - 把串口状态/错误信息展示在右上角状态区。

文件清单：
- Unity/TopPartController.cs
- Unity/SerialCommandBridge.cs
- Unity/GestureCommandBridge.cs
- Unity/CameraOrbit.cs

测试提示命令示例（Windows PowerShell）：

```
# 向 UDP 端口发送测试（需要 ncat 或类似工具）
ncat --udp 127.0.0.1 5005 -c "echo 上移"

# 或者使用 Python 快速发送测试包：
python -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.sendto('上移'.encode(),'127.0.0.1',5005)"
```

若需要我把这些脚本打包为 Unity 包（.unitypackage）或生成示例 Scene，我可以继续执行。告知是否要我生成一个最小示例场景文件（会包含新建 Scene 和简单 hierarchy）。
