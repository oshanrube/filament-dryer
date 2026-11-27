// Renders the v2 touch screens on a PC with stub data, to check the 320 x 240 layout without the
// hardware. Built and run by run.sh; writes one PNG per screen (via ppm2png.py).
#define UI_SIM 1
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include "DryerCore.h"
using namespace dryer;

// ---- stand-ins for what ui_v2.h uses from main.cpp and the Arduino core
#define VERSION "0.2.0-sim"
namespace pin { constexpr int TFT_BL = 47; }
struct String {
  std::string s;
  String(const char* c = "") : s(c) {}
  explicit String(int v) : s(std::to_string(v)) {}
  String operator+(const char* o) const { String r; r.s = s + o; return r; }
  const char* c_str() const { return s.c_str(); }
};
static String g_name("filament-dryer-ab12");
#define WL_CONNECTED 3
struct IpStub { String toString() const { return String("10.0.68.90"); } };
struct WiFiStub { int st = WL_CONNECTED; int status() { return st; } IpStub localIP() { return IpStub(); } int RSSI() { return -58; } } WiFi;
static uint32_t simMillis = 1000;
static uint32_t millis() { return simMillis; }
static void ledcWrite(int, int) {}
enum class CmdType : uint8_t { SetMode, SetMaterial, ClearFault, Tare, Calibrate, SetEmptyReel, SetMmPerPulse, SetRunoutInvert, ResetMotion,
                              CalPoint, LearnDrift, SetTouchFlip, Beep };
enum class CalStep : int { Left = 0, Right = 1, Centre = 2 };
struct Cmd { CmdType type; Mode mode; int material; float value; };
static bool sendCmd(const Cmd&) { return true; }
static volatile bool g_wifiResetRequested = false;
static volatile uint8_t g_touchFlip = 0;
struct Snapshot {
  bool chamberOk = false; float chamberC = 0, chamberRh = 0; const char* chamberSensor = "none";
  bool bayOk = false; float bayC = 0, bayRh = 0;
  bool outletOk = false; float outletC = 0;
  bool scaleOk = false; float grams = 0, gramsLeft = 0, metresLeft = 0, emptyReelG = 0;
  uint32_t motionPulses = 0; float motionMm = 0; bool filamentPresent = false; bool runoutPinHigh = false;
  Mode mode = Mode::Off; Fault fault = Fault::None; bool boost = false; int material = 0;
  float setpointC = 0, duty = 0; bool heaterOn = false, blower = false, exhaust = false;
  uint32_t dryRemainingS = 0, modeElapsedS = 0;
  float mmPerPulse = 2.88f; bool runoutInvert = false;
  float cellG[2] = {0, 0}; bool scaleCalibrated = false; float refC = 25; float driftGPerC[2] = {0, 0};
  bool driftLearned = false, learning = false; uint32_t learnSamples = 0; float learnSpanC = 0;
  const char* calStatus = "";
};
static Snapshot g_sim;
static Snapshot snapshot() { return g_sim; }

#include "../../src/ui_v2.h"

// ---- a framebuffer display
static uint16_t fb[ui::W * ui::H];
static void simFlush(lv_disp_drv_t* drv, const lv_area_t* a, lv_color_t* px) {
  for (int y = a->y1; y <= a->y2; y++)
    for (int x = a->x1; x <= a->x2; x++) fb[y * ui::W + x] = (px++)->full;
  lv_disp_flush_ready(drv);
}
static void dump(const char* name) {
  lv_refr_now(nullptr);
  std::string path = std::string(name) + ".ppm";
  FILE* f = fopen(path.c_str(), "wb");
  fprintf(f, "P6\n%d %d\n255\n", ui::W, ui::H);
  for (int i = 0; i < ui::W * ui::H; i++) {
    uint16_t c = fb[i];
    unsigned char rgb[3] = {(unsigned char)(((c >> 11) & 31) * 255 / 31), (unsigned char)(((c >> 5) & 63) * 255 / 63), (unsigned char)((c & 31) * 255 / 31)};
    fwrite(rgb, 1, 3, f);
  }
  fclose(f);
  printf("wrote %s\n", path.c_str());
}
static void show(lv_obj_t* scr, const char* name) {
  lv_scr_load(scr);
  ui::refresh(nullptr);
  for (int i = 0; i < 5; i++) { simMillis += 50; lv_tick_inc(50); lv_timer_handler(); }
  dump(name);
}

int main() {
  lv_init();
  static lv_disp_draw_buf_t buf;
  static lv_color_t b1[ui::W * 40];
  lv_disp_draw_buf_init(&buf, b1, nullptr, ui::W * 40);
  static lv_disp_drv_t disp;
  lv_disp_drv_init(&disp);
  disp.hor_res = ui::W; disp.ver_res = ui::H; disp.flush_cb = simFlush; disp.draw_buf = &buf;
  lv_disp_t* d = lv_disp_drv_register(&disp);
  lv_disp_set_theme(d, lv_theme_default_init(d, lv_palette_main(LV_PALETTE_BLUE), lv_palette_main(LV_PALETTE_ORANGE), true, &lv_font_montserrat_14));
  ui::buildHome(); ui::buildMaterial(); ui::buildSettings(); ui::buildScale();

  // drying ABS, calibrated scale
  Snapshot& s = g_sim;
  s.chamberOk = true; s.chamberC = 63.2f; s.chamberRh = 11; s.outletOk = true; s.outletC = 78;
  s.scaleOk = true; s.scaleCalibrated = true; s.cellG[0] = 540; s.cellG[1] = 522; s.grams = 1062; s.emptyReelG = 250;
  s.gramsLeft = 812; s.metresLeft = 326; s.mode = Mode::Dry; s.material = materialIndex("ABS"); s.setpointC = 65;
  s.dryRemainingS = 9000; s.duty = 0.42f; s.heaterOn = true; s.blower = true; s.driftLearned = true;
  s.driftGPerC[0] = 0.12f; s.driftGPerC[1] = -0.05f; s.calStatus = "calibrated";
  show(ui::scrHome, "1-home");
  ui::pickFor = Mode::Dry; ui::fillMaterials();
  show(ui::scrMaterial, "2-material");
  show(ui::scrSettings, "3-settings");
  show(ui::scrScale, "4-scale");
  lv_obj_scroll_to_y(lv_obj_get_child(ui::scrScale, 2), 1000, LV_ANIM_OFF);
  show(ui::scrScale, "5-scale-bottom");
  ui::onTare(nullptr);
  show(ui::scrScale, "6-tare-confirm");
  lv_obj_del(lv_obj_get_child(lv_layer_top(), 0));   // dismiss the confirm box
  // a fault, no Wi-Fi, scale not calibrated
  s.fault = Fault::OutletOverTemp; s.mode = Mode::Off; s.duty = 0; s.scaleCalibrated = false; WiFi.st = 0;
  show(ui::scrHome, "7-home-fault");
  return 0;
}
