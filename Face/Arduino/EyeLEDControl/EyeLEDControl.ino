#include <FastLED.h>

// 定义引脚和LED数量
#define LEFT_LED_PIN     6
#define RIGHT_LED_PIN    7
#define LED_COUNT        16

// 创建LED数组
CRGB leftLeds[LED_COUNT];
CRGB rightLeds[LED_COUNT];

// 定义效果类型
enum Effect {
  OFF,             // 关闭
  SOLID_BLUE,      // 蓝色常亮(默认)
  SOLID_WHITE,     // 白色常亮
  LEFT_EYE_ONLY,   // 仅左眼亮
  RIGHT_EYE_ONLY,  // 仅右眼亮
  BREATH_RED,      // 红色呼吸
  LEFT_FLOW,       // 向左流水
  RIGHT_FLOW,      // 向右流水
  RAINBOW,         // 彩虹效果
  BLINKING,        // 闪烁模式
  // 语音交互专用效果
  VOICE_OFF_ALL,       // 关闭所有LED
  VOICE_ON_FADE,       // 渐亮效果
  VOICE_THINK_BLINK,   // 快速闪烁思考效果
  VOICE_RAINBOW_WAVE   // 彩虹波浪效果
};

Effect currentEffect = SOLID_BLUE;
unsigned long previousMillis = 0;
int flowPosition = 0;
int hue = 0;
int breathBrightness = 0;
int breathDirection = 1;
int fadeStep = 0;        // 渐亮步骤
bool blinkState = false; // 闪烁状态

void setup() {
  // 初始化LED
  FastLED.addLeds<WS2812, LEFT_LED_PIN, GRB>(leftLeds, LED_COUNT);
  FastLED.addLeds<WS2812, RIGHT_LED_PIN, GRB>(rightLeds, LED_COUNT);
  FastLED.setBrightness(200);  // 提高亮度使效果更明显
  
  // 初始化串口通信
  Serial.begin(9600);
  
  // 启动提示
  setAllLeds(CRGB::Green);
  FastLED.show();
  delay(1000);
  setAllLeds(CRGB::Black);
  delay(300);
}

void loop() {
  // 检查串口指令
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // 执行当前效果
  unsigned long currentMillis = millis();
  switch(currentEffect) {
    case OFF:
      setAllLeds(CRGB::Black);
      FastLED.show();
      break;
      
    case SOLID_BLUE:
      setAllLeds(CRGB::Blue);
      FastLED.show();
      break;
      
    case SOLID_WHITE:
      setAllLeds(CRGB::White);
      FastLED.show();
      break;
      
    case LEFT_EYE_ONLY:
      setLeds(leftLeds, CRGB::Cyan);
      setLeds(rightLeds, CRGB::Black);
      FastLED.show();
      break;
      
    case RIGHT_EYE_ONLY:
      setLeds(leftLeds, CRGB::Black);
      setLeds(rightLeds, CRGB::Cyan);
      FastLED.show();
      break;
      
    case BREATH_RED:
      breathEffect(CRGB::Red);
      break;
      
    case LEFT_FLOW:
      if (currentMillis - previousMillis > 80) {
        previousMillis = currentMillis;
        flowEffect(true, CRGB::Magenta);
      }
      break;
      
    case RIGHT_FLOW:
      if (currentMillis - previousMillis > 80) {
        previousMillis = currentMillis;
        flowEffect(false, CRGB::Magenta);
      }
      break;
      
    case RAINBOW:
      if (currentMillis - previousMillis > 40) {
        previousMillis = currentMillis;
        rainbowEffect();
      }
      break;
      
    case BLINKING:
      if (currentMillis - previousMillis > 200) {
        previousMillis = currentMillis;
        blinkingEffect(CRGB::Yellow);
      }
      break;

    // 语音交互专用效果
    case VOICE_OFF_ALL:
      setAllLeds(CRGB::Black);
      FastLED.show();
      break;
      
    case VOICE_ON_FADE:
      if (currentMillis - previousMillis > 50) {
        previousMillis = currentMillis;
        fadeInEffect();
      }
      break;
      
    case VOICE_THINK_BLINK:
      if (currentMillis - previousMillis > 100) {  // 快速闪烁
        previousMillis = currentMillis;
        blinkingEffect(CRGB::White);
      }
      break;

    case VOICE_RAINBOW_WAVE:
      if (currentMillis - previousMillis > 60) {
        previousMillis = currentMillis;
        rainbowWaveEffect();
      }
      break;
  }
}

// 处理串口命令
void processCommand(String command) {
  // 表情交互命令
  if (command == "OPEN_EYES") currentEffect = SOLID_BLUE;
  else if (command == "CLOSE_EYES") currentEffect = OFF;
  else if (command == "LOOK_LEFT") currentEffect = LEFT_FLOW;
  else if (command == "LOOK_RIGHT") currentEffect = RIGHT_FLOW;
  else if (command == "OPEN_MOUTH") currentEffect = BREATH_RED;
  else if (command == "CLOSE_MOUTH") currentEffect = SOLID_BLUE;
  else if (command == "ALL_ON") currentEffect = SOLID_WHITE;
  else if (command == "ALL_OFF") currentEffect = OFF;
  else if (command == "RAINBOW") currentEffect = RAINBOW;
  else if (command == "BLINK") currentEffect = BLINKING;
  else if (command == "LEFT_ONLY") currentEffect = LEFT_EYE_ONLY;
  else if (command == "RIGHT_ONLY") currentEffect = RIGHT_EYE_ONLY;
  else if (command == "DEFAULT") currentEffect = SOLID_BLUE;
  
  // 语音交互命令
  else if (command == "VOICE_OFF_ALL") currentEffect = VOICE_OFF_ALL;
  else if (command == "VOICE_ON_FADE") {
    currentEffect = VOICE_ON_FADE;
    fadeStep = 0; // 重置渐亮步骤
  }
  else if (command == "VOICE_THINK_BLINK") currentEffect = VOICE_THINK_BLINK;
  else if (command == "VOICE_EXIT") currentEffect = SOLID_BLUE; // 退出时回到默认
}

// 设置所有LED为指定颜色
void setAllLeds(CRGB color) {
  setLeds(leftLeds, color);
  setLeds(rightLeds, color);
}

// 设置单个LED环颜色
void setLeds(CRGB* leds, CRGB color) {
  for(int i = 0; i < LED_COUNT; i++) {
    leds[i] = color;
  }
}

// 流水效果（增加颜色参数）
void flowEffect(bool left, CRGB color) {
  setAllLeds(CRGB::Black);
  
  if(left) {
    flowPosition--;
    if(flowPosition < 0) flowPosition = LED_COUNT - 1;
  } else {
    flowPosition++;
    if(flowPosition >= LED_COUNT) flowPosition = 0;
  }
  
  // 流水带尾迹效果
  for(int i=0; i<3; i++){
    int pos = (left) ? (flowPosition - i + LED_COUNT) % LED_COUNT : (flowPosition + i) % LED_COUNT;
    CRGB temp = color;
    temp.fadeToBlackBy(i * 60); // 尾迹渐暗
    leftLeds[pos] = temp;
    rightLeds[pos] = temp;
  }
  FastLED.show();
}

// 增强彩虹效果
void rainbowEffect() {
  hue++;
  fill_rainbow(leftLeds, LED_COUNT, hue, 256 / LED_COUNT);
  fill_rainbow(rightLeds, LED_COUNT, hue + 128, 256 / LED_COUNT); // 左右眼彩虹相位差
  FastLED.show();
}

// 彩虹波浪效果（语音专用）
void rainbowWaveEffect() {
  hue++;
  for(int i=0; i<LED_COUNT; i++){
    int pixelHue = hue + (i * 15);
    leftLeds[i] = CHSV(pixelHue % 256, 255, 200);
    rightLeds[LED_COUNT - 1 - i] = CHSV(pixelHue % 256, 255, 200); // 反向波浪
  }
  FastLED.show();
}

// 呼吸效果
void breathEffect(CRGB color) {
  breathBrightness += breathDirection;
  if(breathBrightness >= 255) breathDirection = -2;
  if(breathBrightness <= 0) breathDirection = 2;
  
  CRGB adjustedColor = color;
  adjustedColor.fadeToBlackBy(255 - breathBrightness);
  
  setAllLeds(adjustedColor);
  FastLED.show();
}

// 渐亮效果（语音专用）
void fadeInEffect() {
  if(fadeStep < 255) {
    fadeStep += 2;
    CRGB color = CRGB::White;
    color.fadeToBlackBy(255 - fadeStep);
    setAllLeds(color);
    FastLED.show();
  }
}

// 闪烁效果（增加颜色参数）
void blinkingEffect(CRGB color) {
  blinkState = !blinkState;
  setAllLeds(blinkState ? color : CRGB::Black);
  FastLED.show();
}