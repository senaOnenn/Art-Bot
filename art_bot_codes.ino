// ============================================
// ART BOT v8.1 - Açı düzeltmesi + büyük çizim
// ============================================

#include <ESP8266WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

const char* AP_SSID = "ArtBot";
const char* AP_PASS = "12345678";

#define IN1 D0
#define IN2 D7
#define IN3 D5
#define IN4 D6

#define ILERI_SURE   500     // 5 cm
#define DON90_SURE   320     // gerçek 90° — TEK REFERANS
// Diğerleri DON90_SURE'den türetiliyor:
#define DON45_SURE   200     // 400 * 45/90
#define DON60_SURE   213     // 400 * 60/90
#define DON120_SURE  426    // 400 * 120/90
#define DON180_SURE  620     // 400 * 180/90
#define GECİKME      250

#define KONUM_PERIYOT 50
#define ADIM_CM       5.0f
#define MAX_KUYRUK    20

char kuyruk[MAX_KUYRUK][10];
int  kuyrukBas = 0, kuyrukSon = 0, kuyrukSayi = 0;

float posX = 0, posY = 0, yon = 0;
float basX = 0, basY = 0, basYon = 0;
float hedefX = 0, hedefY = 0, hedefYon = 0;

enum Durum { BEKLE, HAREKET, BEKLEME_SONRASI };
Durum durum        = BEKLE;
char  aktifCmd[10] = "";
unsigned long hareketBas    = 0;
unsigned long hareketSure   = 0;
unsigned long sonKonumYayin = 0;
bool  acilStop  = false;
bool  calisiyor = false;

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

void motorIleri() { digitalWrite(IN1,LOW);  digitalWrite(IN2,HIGH); digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH); }
void motorGeri()  { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);  digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW);  }
void motorSaga() { digitalWrite(IN1,LOW);  digitalWrite(IN2,HIGH); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW);  }
void motorSola() { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);  digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH); }
void motorDur()   { digitalWrite(IN1,LOW);  digitalWrite(IN2,LOW);  digitalWrite(IN3,LOW);  digitalWrite(IN4,LOW);  }

void kuyrukEkle(const char* cmd) {
  if (kuyrukSayi >= MAX_KUYRUK) return;
  strncpy(kuyruk[kuyrukSon], cmd, 9); kuyruk[kuyrukSon][9] = '\0';
  kuyrukSon = (kuyrukSon + 1) % MAX_KUYRUK; kuyrukSayi++;
}
void kuyrukTemizle() { kuyrukBas = kuyrukSon = kuyrukSayi = 0; }

void kuyrukYayinla() {
  StaticJsonDocument<512> doc;
  doc["type"] = "queue";
  JsonArray arr = doc.createNestedArray("items");
  for (int i = 0; i < kuyrukSayi; i++)
    arr.add(kuyruk[(kuyrukBas + i) % MAX_KUYRUK]);
  String out; serializeJson(doc, out); ws.textAll(out);
}

void konumYayinla(float x, float y, float y_yon) {
  StaticJsonDocument<128> doc;
  doc["type"] = "pos"; doc["x"] = x; doc["y"] = y; doc["yon"] = y_yon;
  String out; serializeJson(doc, out); ws.textAll(out);
}

void statusYayinla(const char* mod) {
  StaticJsonDocument<64> doc;
  doc["type"] = "status"; doc["mod"] = mod;
  String out; serializeJson(doc, out); ws.textAll(out);
}

void odometriGuncelle(const char* cmd) {
  if      (strcmp(cmd,"ILERI")  == 0) { float r=yon*PI/180.0f; posX+=ADIM_CM*sin(r); posY+=ADIM_CM*cos(r); }
  else if (strcmp(cmd,"GERI")   == 0) { float r=yon*PI/180.0f; posX-=ADIM_CM*sin(r); posY-=ADIM_CM*cos(r); }
  else if (strcmp(cmd,"SAG90")  == 0) { yon = fmod(yon+ 90.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SOL90")  == 0) { yon = fmod(yon- 90.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SAG60")  == 0) { yon = fmod(yon+ 60.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SOL60")  == 0) { yon = fmod(yon- 60.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SAG45")  == 0) { yon = fmod(yon+ 45.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SOL45")  == 0) { yon = fmod(yon- 45.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SAG120") == 0) { yon = fmod(yon+120.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SOL120") == 0) { yon = fmod(yon-120.0f+360.0f,360.0f); }
  else if (strcmp(cmd,"SAG180") == 0) { yon = fmod(yon+180.0f+360.0f,360.0f); }
}

void hareketBaslat(const char* cmd) {
  strncpy(aktifCmd, cmd, 9); aktifCmd[9] = '\0';
  hareketBas = millis();
  basX = posX; basY = posY; basYon = yon;
  hedefX = posX; hedefY = posY; hedefYon = yon;

  if (strcmp(cmd,"ILERI") == 0) {
    float r=yon*PI/180.0f; hedefX+=ADIM_CM*sin(r); hedefY+=ADIM_CM*cos(r);
    motorIleri(); hareketSure = ILERI_SURE;
  } else if (strcmp(cmd,"GERI") == 0) {
    float r=yon*PI/180.0f; hedefX-=ADIM_CM*sin(r); hedefY-=ADIM_CM*cos(r);
    motorGeri(); hareketSure = ILERI_SURE;
  } else if (strcmp(cmd,"SAG90")  == 0) { hedefYon=fmod(yon+ 90.0f+360.0f,360.0f); motorSaga(); hareketSure=DON90_SURE;  }
  else if   (strcmp(cmd,"SOL90")  == 0) { hedefYon=fmod(yon- 90.0f+360.0f,360.0f); motorSola(); hareketSure=DON90_SURE;  }
  else if   (strcmp(cmd,"SAG60")  == 0) { hedefYon=fmod(yon+ 60.0f+360.0f,360.0f); motorSaga(); hareketSure=DON60_SURE;  }
  else if   (strcmp(cmd,"SOL60")  == 0) { hedefYon=fmod(yon- 60.0f+360.0f,360.0f); motorSola(); hareketSure=DON60_SURE;  }
  else if   (strcmp(cmd,"SAG45")  == 0) { hedefYon=fmod(yon+ 45.0f+360.0f,360.0f); motorSaga(); hareketSure=DON45_SURE;  }
  else if   (strcmp(cmd,"SOL45")  == 0) { hedefYon=fmod(yon- 45.0f+360.0f,360.0f); motorSola(); hareketSure=DON45_SURE;  }
  else if (strcmp(cmd,"SAG120") == 0) { hedefYon=fmod(yon+120.0f+360.0f,360.0f); motorSaga(); hareketSure=DON120_SURE; }
  else if (strcmp(cmd,"SOL120") == 0) { hedefYon=fmod(yon-120.0f+360.0f,360.0f); motorSola(); hareketSure=DON120_SURE; }
  else if   (strcmp(cmd,"SAG180") == 0) { hedefYon=fmod(yon+180.0f+360.0f,360.0f); motorSaga(); hareketSure=DON180_SURE; }
  else { hareketSure = 0; }

  durum = HAREKET;
}

void interpolasyonYayinla() {
  if (hareketSure == 0) return;
  float t = (float)(millis()-hareketBas) / (float)hareketSure;
  if (t > 1.0f) t = 1.0f;
  float dy = hedefYon - basYon;
  if (dy >  180.0f) dy -= 360.0f;
  if (dy < -180.0f) dy += 360.0f;
  konumYayinla(
    basX + (hedefX-basX)*t,
    basY + (hedefY-basY)*t,
    fmod(basYon + dy*t + 360.0f, 360.0f)
  );
}

void durumGuncelle() {
  if (acilStop) { motorDur(); durum = BEKLE; return; }
  unsigned long now = millis();

  if (durum == HAREKET) {
    if (now - sonKonumYayin >= KONUM_PERIYOT) {
      sonKonumYayin = now;
      interpolasyonYayinla();
    }
    if (now - hareketBas >= hareketSure) {
      motorDur();
      odometriGuncelle(aktifCmd);
      konumYayinla(posX, posY, yon);
      hareketBas = now;
      durum = BEKLEME_SONRASI;
    }
  } else if (durum == BEKLEME_SONRASI) {
    if (now - hareketBas >= GECİKME) {
      if (kuyrukSayi > 0) {
        const char* cmd = kuyruk[kuyrukBas];
        kuyrukBas = (kuyrukBas+1) % MAX_KUYRUK; kuyrukSayi--;
        kuyrukYayinla(); hareketBaslat(cmd);
      } else {
        durum = BEKLE; calisiyor = false;
        statusYayinla("Tamamlandi"); kuyrukYayinla();
      }
    }
  }
}

void onWsEvent(AsyncWebSocket* svr, AsyncWebSocketClient* client,
               AwsEventType type, void* arg, uint8_t* data, size_t len) {
  if (type == WS_EVT_CONNECT) {
    statusYayinla(calisiyor ? "Calisiyor" : "Bekliyor");
    kuyrukYayinla(); konumYayinla(posX, posY, yon); return;
  }
  if (type == WS_EVT_DATA) {
    char buf[128]; size_t n=min(len,(size_t)127);
    memcpy(buf,data,n); buf[n]='\0';
    StaticJsonDocument<128> doc;
    if (deserializeJson(doc,buf) != DeserializationError::Ok) return;
    const char* t = doc["type"] | "";

    if (strcmp(t,"stop")==0) {
      acilStop=true; motorDur(); kuyrukTemizle();
      durum=BEKLE; calisiyor=false; acilStop=false;
      statusYayinla("Durduruldu"); kuyrukYayinla();
    } else if (strcmp(t,"add")==0) {
      if (durum==BEKLE) { kuyrukEkle(doc["cmd"]|""); kuyrukYayinla(); }
    } else if (strcmp(t,"run")==0) {
      if (durum==BEKLE && kuyrukSayi>0) {
        calisiyor=true; statusYayinla("Calisiyor");
        const char* cmd=kuyruk[kuyrukBas];
        kuyrukBas=(kuyrukBas+1)%MAX_KUYRUK; kuyrukSayi--;
        kuyrukYayinla(); hareketBaslat(cmd);
      }
    } else if (strcmp(t,"clear")==0) {
      if (durum==BEKLE) { kuyrukTemizle(); kuyrukYayinla(); statusYayinla("Bekliyor"); }
    } else if (strcmp(t,"reset")==0) {
      posX=0; posY=0; yon=0; 
      Serial.println("RESET ALINDI");
      konumYayinla(posX,posY,yon);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT);
  pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);
  motorDur();
  WiFi.mode(WIFI_AP); WiFi.softAP(AP_SSID,AP_PASS);
  Serial.print("AP IP: "); Serial.println(WiFi.softAPIP());
  ws.onEvent(onWsEvent);
  server.addHandler(&ws);
  server.on("/",HTTP_GET,[](AsyncWebServerRequest* req){
    req->send_P(200,"text/html","ARTBOT v8.1");
  });
  server.begin();
  Serial.println("Hazir! v8.1");
}

void loop() {
  ws.cleanupClients();
  durumGuncelle();
}