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
