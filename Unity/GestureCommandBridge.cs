using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;
using UnityEngine;

// 轻量 UDP 手势桥接：外部硬件/处理器可以向该端口发送简单文本命令（上移、下移、左转、右转、停止）
public class GestureCommandBridge : MonoBehaviour
{
    public int listenPort = 5005;
    public TopPartController controller;

    private UdpClient udpClient;
    private Thread udpThread;
    private bool running = false;
    private ConcurrentQueue<string> queue = new ConcurrentQueue<string>();

    void Start()
    {
        if (controller == null)
        {
            Debug.LogWarning("GestureCommandBridge: controller 未绑定");
        }

        try
        {
            udpClient = new UdpClient(listenPort);
            running = true;
            udpThread = new Thread(ReadLoop) { IsBackground = true };
            udpThread.Start();
            Debug.Log($"UDP 手势监听启动，端口 {listenPort}");
        }
        catch (Exception ex)
        {
            Debug.LogWarning("启动 UDP 监听失败：" + ex.Message);
        }
    }

    void ReadLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                var data = udpClient.Receive(ref remoteEP);
                var msg = Encoding.UTF8.GetString(data).Trim();
                if (!string.IsNullOrEmpty(msg)) queue.Enqueue(msg);
            }
            catch (SocketException) { }
            catch (Exception ex)
            {
                Debug.LogWarning("UDP 读取异常：" + ex.Message);
                Thread.Sleep(50);
            }
        }
    }

    void Update()
    {
        while (queue.TryDequeue(out var cmd))
        {
            ProcessCommand(cmd);
        }
    }

    void ProcessCommand(string cmd)
    {
        switch (cmd)
        {
            case "上移":
            case "UP": controller?.StartMoveUp(); break;
            case "下移":
            case "DOWN": controller?.StartMoveDown(); break;
            case "左转":
            case "LEFT": controller?.StartRotateLeft(); break;
            case "右转":
            case "RIGHT": controller?.StartRotateRight(); break;
            case "停止":
            case "STOP": controller?.StopAllMotion(); break;
            default:
                Debug.Log("收到未知手势命令：" + cmd);
                break;
        }
    }

    void OnDestroy()
    {
        running = false;
        try { udpClient?.Close(); } catch { }
        try { if (udpThread != null && udpThread.IsAlive) udpThread.Join(200); } catch { }
    }
}
