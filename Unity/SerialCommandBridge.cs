using System;
using System.IO.Ports;
using System.Threading;
using System.Collections.Concurrent;
using UnityEngine;

// 将串口命令转为 Unity 可调用命令（在 Update 中回调，避免在子线程访问 Unity API）
public class SerialCommandBridge : MonoBehaviour
{
    public string portName = "COM3";
    public int baudRate = 9600;
    public TopPartController controller; // 在 Inspector 关联

    private SerialPort serialPort;
    private Thread readThread;
    private bool running = false;
    private ConcurrentQueue<string> queue = new ConcurrentQueue<string>();

    void Start()
    {
        if (controller == null)
        {
            Debug.LogWarning("SerialCommandBridge: controller 未绑定");
            return;
        }

        try
        {
            serialPort = new SerialPort(portName, baudRate);
            serialPort.ReadTimeout = 500;
            serialPort.Open();
            running = true;
            readThread = new Thread(ReadLoop) { IsBackground = true };
            readThread.Start();
            Debug.Log($"已打开串口 {portName} @ {baudRate}");
        }
        catch (Exception ex)
        {
            Debug.LogWarning("打开串口失败：" + ex.Message);
        }
    }

    void ReadLoop()
    {
        while (running && serialPort != null && serialPort.IsOpen)
        {
            try
            {
                string line = serialPort.ReadLine();
                if (!string.IsNullOrEmpty(line))
                {
                    queue.Enqueue(line.Trim());
                }
            }
            catch (TimeoutException) { }
            catch (Exception ex)
            {
                Debug.LogWarning("串口读取异常：" + ex.Message);
                Thread.Sleep(100);
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
        // 支持中文指令和英文简写
        switch (cmd)
        {
            case "上移":
            case "UP":
            case "UP\r":
            case "上":
                controller?.StartMoveUp();
                break;
            case "下移":
            case "DOWN":
            case "下":
                controller?.StartMoveDown();
                break;
            case "左转":
            case "LEFT":
            case "左":
                controller?.StartRotateLeft();
                break;
            case "右转":
            case "RIGHT":
            case "右":
                controller?.StartRotateRight();
                break;
            case "停止":
            case "STOP":
            case "S":
                controller?.StopAllMotion();
                break;
            default:
                Debug.Log("收到未知串口命令：" + cmd);
                break;
        }
    }

    void OnDestroy()
    {
        running = false;
        try { serialPort?.Close(); } catch { }
        try { if (readThread != null && readThread.IsAlive) readThread.Join(200); } catch { }
    }
}
