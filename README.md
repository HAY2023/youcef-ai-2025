# ⏱ Nabtakir — RACE TIMER PRO (Stable Edition)

![Logo](icon.ico)

تطبيق احترافي لإدارة سباقات السرعة باستخدام تقنيات الأردوينو وحساسات المسافة. يتميز هذا الإصدار (v6.2) بالاستقرار التام ومنطق العمل الصحيح.

## ✨ المميزات (Features)
*   **منطق سباق دقيق:** الحساس الأول (البداية) يطلق المؤقت، والحساس الثاني (النهاية) يوقف المؤقت ويحسب النتيجة.
*   **لوحة تحكم ذكية (Controller Hub):** لإدارة الاتصال بالحساسات واختبارها برمجياً.
*   **كود مدمج:** كود الأردوينو مدمج داخل التطبيق للبرمجة السهلة (بدون إنترنت).
*   **تعدد اللغات:** دعم كامل للغة العربية.

## 🛠 المتطلبات (Requirements)
1.  **لوحة أردوينو (Arduino Nano/Uno).**
2.  **حساسات مسافة (HC-SR04).**
3.  **كابل USB.**

## 📥 التحميل والتشغيل (Download & Run)
1.  قم بتحميل المستودع بالكامل (Download ZIP).
2.  تأكد من وجود برنامج Python مثبت على جهازك.
3.  قم بتثبيت المكتبات اللازمة: `pip install pyserial Pillow`
4.  قم بتشغيل الملف الرئيسي: `python race_timer_v5.py`
5.  **ملاحظة هامة:** تأكد من ضبط سرعة الباود في الأردوينو على `9600`.

## 🔌 التوصيل (Wiring)
*   **حساس البداية (Start Sensor):** TRIG→D2, ECHO→D3
*   **حساس النهاية (Finish Sensor):** TRIG→D4, ECHO→D5
*   **الطاقة:** VCC→5V, GND→GND

## 💻 كود الأردوينو (Arduino Code)
```cpp
// RACE TIMER ARDUINO CODE v6.2 (STABLE)
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5
#define DETECT_CM 30
#define DEBOUNCE 300

unsigned long start_ms = 0;
bool racing = false;
bool armed = false;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT); pinMode(ECHO2, INPUT);
  Serial.println("READY");
}

long readCM(int tr, int ec) {
  digitalWrite(tr, LOW); delayMicroseconds(2);
  digitalWrite(tr, HIGH); delayMicroseconds(10);
  digitalWrite(tr, LOW);
  long dur = pulseIn(ec, HIGH, 20000);
  return (dur <= 0) ? -1 : dur * 0.034 / 2;
}

void loop() {
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if(cmd == "ARM")   { armed = true; racing = false; Serial.println("ARMED_OK"); }
    if(cmd == "RESET") { armed = false; racing = false; Serial.println("RESET_OK"); }
  }

  if(armed && !racing){
    long d1 = readCM(TRIG1, ECHO1);
    if(d1 > 0 && d1 < DETECT_CM){
       start_ms = millis();
       racing = true;
       Serial.println("START");
       delay(DEBOUNCE);
    }
  }

  if(racing){
    long d2 = readCM(TRIG2, ECHO2);
    if(d2 > 0 && d2 < DETECT_CM){
       unsigned long total = millis() - start_ms;
       Serial.print("TIME:"); Serial.println(total);
       racing = false;
       armed = false;
       delay(DEBOUNCE);
    }
  }
}
```

---
تم التطوير بواسطة **NABTAKIR** — جميع الحقوق محفوظة.
