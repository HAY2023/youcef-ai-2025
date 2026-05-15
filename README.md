# ⏱ Nabtakir — RACE TIMER PRO (Controller Edition)

![Logo](icon.ico)

تطبيق احترافي لإدارة سباقات السرعة باستخدام تقنيات الأردوينو وحساسات المسافة. يتميز هذا الإصدار (v6.1) بواجهة مستخدم متطورة ونظام تحكم متكامل بالحساسات.

## ✨ المميزات (Features)
*   **لوحة تحكم ذكية (Controller Hub):** لإدارة الاتصال بالحساسات واختبارها برمجياً.
*   **توقيت عالي الدقة:** دقة تصل إلى جزء من الألف من الثانية.
*   **كود مدمج:** كود الأردوينو مدمج داخل التطبيق للبرمجة السهلة (بدون إنترنت).
*   **تعدد اللغات:** دعم كامل للغتين العربية والإنجليزية.
*   **تصدير النتائج:** حفظ النتائج تلقائياً في ملفات CSV للتحليل.

## 🛠 المتطلبات (Requirements)
1.  **لوحة أردوينو (Arduino Nano/Uno).**
2.  **حساسات مسافة (HC-SR04).**
3.  **كابل USB.**

## 📥 التحميل والتشغيل (Download & Run)
1.  قم بتحميل المستودع بالكامل (Download ZIP).
2.  تأكد من وجود برنامج Python مثبت على جهازك.
3.  قم بتثبيت المكتبات اللازمة:
    ```bash
    pip install -r requirements.txt
    ```
4.  قم بتشغيل الملف الرئيسي:
    ```bash
    python race_timer_v5.py
    ```
5.  **ملاحظة:** تأكد من ضبط سرعة الباود في الأردوينو على `115200`.

## 🔌 التوصيل (Wiring)
*   **حساس البداية (Start Sensor):** TRIG→D2, ECHO→D3
*   **حساس النهاية (Finish Sensor):** TRIG→D4, ECHO→D5
*   **الطاقة:** VCC→5V, GND→GND

## 💻 كود الأردوينو (Arduino Code)
قم بنسخ هذا الكود ورفعه على لوحة الأردوينو الخاصة بك:

```cpp
// RACE TIMER ARDUINO CODE v6.1 (ULTRA FAST)
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5
#define DETECT_CM 35
#define DEBOUNCE 100

void setup() {
  Serial.begin(115200);
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT); pinMode(ECHO2, INPUT);
  Serial.println("READY");
}

long readCM(int tr, int ec) {
  digitalWrite(tr, LOW); delayMicroseconds(2);
  digitalWrite(tr, HIGH); delayMicroseconds(5);
  digitalWrite(tr, LOW);
  long dur = pulseIn(ec, HIGH, 15000); 
  return (dur <= 0) ? -1 : dur * 0.034 / 2;
}

void loop() {
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if(cmd == "ARM")   { Serial.println("ARMED_OK"); while(true){
      if(readCM(TRIG1, ECHO1) < DETECT_CM && readCM(TRIG1, ECHO1) > 0){
        unsigned long t0 = millis();
        Serial.println("START");
        while(true){
          if(readCM(TRIG2, ECHO2) < DETECT_CM && readCM(TRIG2, ECHO2) > 0){
            Serial.print("TIME:"); Serial.println(millis()-t0);
            return; 
          }
          if(Serial.available()) return;
        }
      }
      if(Serial.available()) return;
    }}
  }
}
```

---
تم التطوير بواسطة **NABTAKIR** — جميع الحقوق محفوظة.
