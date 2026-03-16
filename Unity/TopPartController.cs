using UnityEngine;
using UnityEngine.UI;

public class TopPartController : MonoBehaviour
{
    [Header("运动参数")]
    public float moveSpeed = 0.5f; // 单位：cm/s（在Unity中按单位使用，开发者可按比例调整）
    public float rotateSpeed = 30f; // 度/s
    public float maxUpDistance = 12f; // 最大上升距离（cm）
    public float minDownDistance = 0f; // 最低位置（cm，基于originalPos）

    [Header("按钮绑定（可在 Inspector 绑定）")]
    public Button btnUp;
    public Button btnDown;
    public Button btnRotateLeft;
    public Button btnRotateRight;
    public Button btnStop;

    [Header("状态文本（可选）")]
    public Text statusText;

    // 状态变量
    private bool isMovingUp = false;
    private bool isMovingDown = false;
    private bool isRotatingLeft = false;
    private bool isRotatingRight = false;
    private Vector3 originalPos;

    void Start()
    {
        originalPos = transform.localPosition;

        // 绑定按钮（若在 Inspector 已绑定，则不重复绑定）
        if (btnUp != null) btnUp.onClick.AddListener(StartMoveUp);
        if (btnDown != null) btnDown.onClick.AddListener(StartMoveDown);
        if (btnRotateLeft != null) btnRotateLeft.onClick.AddListener(StartRotateLeft);
        if (btnRotateRight != null) btnRotateRight.onClick.AddListener(StartRotateRight);
        if (btnStop != null) btnStop.onClick.AddListener(StopAllMotion);

        UpdateStatus("就绪");
    }

    void Update()
    {
        // 注意：脚本中使用的单位为 Unity 单位（默认米），如果你的 FBX 按 cm 导入，请根据比例调整 moveSpeed 和 maxUpDistance。

        // 上移
        if (isMovingUp)
        {
            float targetY = originalPos.y + maxUpDistance;
            if (transform.localPosition.y < targetY)
            {
                float step = moveSpeed * Time.deltaTime;
                transform.Translate(Vector3.up * step, Space.Self);
                UpdateStatus($"上升中，当前高度：{(transform.localPosition.y - originalPos.y):F2}cm");
            }
            else
            {
                StopAllMotion();
                UpdateStatus("达到最大上升高度");
            }
        }

        // 下移
        if (isMovingDown)
        {
            float targetY = originalPos.y + minDownDistance;
            if (transform.localPosition.y > targetY)
            {
                float step = moveSpeed * Time.deltaTime;
                transform.Translate(Vector3.down * step, Space.Self);
                UpdateStatus($"下降中，当前高度：{(transform.localPosition.y - originalPos.y):F2}cm");
            }
            else
            {
                StopAllMotion();
                UpdateStatus("达到最低高度");
            }
        }

        // 旋转
        if (isRotatingLeft)
        {
            transform.Rotate(Vector3.forward * rotateSpeed * Time.deltaTime, Space.Self);
            UpdateStatus($"左转中，当前角度：{transform.localEulerAngles.z:F0}°");
        }
        if (isRotatingRight)
        {
            transform.Rotate(Vector3.back * rotateSpeed * Time.deltaTime, Space.Self);
            UpdateStatus($"右转中，当前角度：{transform.localEulerAngles.z:F0}°");
        }
    }

    // 公共命令（可被外部脚本调用）
    public void StartMoveUp() { ResetMotionStatus(); isMovingUp = true; }
    public void StartMoveDown() { ResetMotionStatus(); isMovingDown = true; }
    public void StartRotateLeft() { ResetMotionStatus(); isRotatingLeft = true; }
    public void StartRotateRight() { ResetMotionStatus(); isRotatingRight = true; }
    public void StopAllMotion()
    {
        ResetMotionStatus();
        UpdateStatus("停止");
    }

    void ResetMotionStatus()
    {
        isMovingUp = false;
        isMovingDown = false;
        isRotatingLeft = false;
        isRotatingRight = false;
    }

    void UpdateStatus(string status)
    {
        if (statusText != null)
        {
            statusText.text = "上表面部件 - " + status;
        }
    }
}
