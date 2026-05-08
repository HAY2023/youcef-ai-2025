# كود الأردوينو (Arduino Code)

هذا هو كود لوحة Arduino Nano المخصص لقراءة حساسات المسافة (HC-SR04) وإرسال النتائج إلى تطبيق بايثون.

```cpp
/* ═══════════════════════════════════════════════════════════
 *   RACE TIMER — Arduino Nano
 *   فقط: 2× HC-SR04 + Serial USB
 *
 *   التوصيل:
 *   حساس 1 (بداية):  TRIG→D2  ECHO→D3  VCC→5V  GND→GND
 *   حساس 2 (نهاية):  TRIG→D4  ECHO→D5  VCC→5V  GND→GND
 *   الحاسوب:          كابل USB مباشرة
 *
 *   بروتوكول Serial 9600 baud:
 *   Arduino→PC:  "READY"     عند التشغيل
 *                "START"     عند مرور الحساس 1
 *                "TIME:xxxx" الزمن بالملي ثانية
 *   PC→Arduino:  "ARM\n"     جهّز للمتسابق التالي
 *                "RESET\n"   إعادة تعيين
 * ═══════════════════════════════════════════════════════════ */

#define TRIG1       2
#define ECHO1       3
#define TRIG2       4
#define ECHO2       5
#define DETECT_CM   25      // مسافة الاكتشاف
#define DEBOUNCE_MS 400     // مكافحة الارتداد

enum State { ARMED, RUNNING, COOLDOWN };
State         state      = ARMED;
unsigned long startTime  = 0;
unsigned long lastDetect = 0;

// ─────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT); pinMode(ECHO2, INPUT);
  Serial.println("READY");
}

// ─────────────────────────────────────────────
void loop() {
  handleSerial();

  switch (state) {

    // ── ينتظر مرور الحساس 1 ──────────────────
    case ARMED: {
      long d1 = readCM(TRIG1, ECHO1);
      if (d1 > 0 && d1 < DETECT_CM &&
          millis() - lastDetect > DEBOUNCE_MS) {
        lastDetect = millis();
        startTime  = millis();
        state      = RUNNING;
        Serial.println("START");
      }
      break;
    }

    // ── يعدّ — ينتظر مرور الحساس 2 ──────────
    case RUNNING: {
      long d2 = readCM(TRIG2, ECHO2);
      if (d2 > 0 && d2 < DETECT_CM &&
          millis() - lastDetect > DEBOUNCE_MS) {
        lastDetect = millis();
        unsigned long elapsed = millis() - startTime;
        Serial.print("TIME:");
        Serial.println(elapsed);
        state = COOLDOWN;
      }
      break;
    }

    // ── ينتظر ARM من التطبيق ─────────────────
    case COOLDOWN:
      break;
  }
}

// ─────────────────────────────────────────────
void handleSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd == "ARM" || cmd == "RESET") {
    state      = ARMED;
    lastDetect = 0;
    Serial.println("ARMED_OK");
  }
}

// ─────────────────────────────────────────────
long readCM(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long dur = pulseIn(echo, HIGH, 25000);
  if (dur == 0) return -1;
  return dur * 0.034 / 2;
}
```
