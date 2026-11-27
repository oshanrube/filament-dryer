// Touch screen for the 1-roll v2 board: a 2.8" 320x240 ILI9341 with an FT6336 capacitive touch
// controller, driven by LovyanGFX and LVGL 8. Included by main.cpp (DRYER_BOARD_V2 only), after the
// snapshot, the command queue and the network globals it uses.
//
// The UI runs in its own task. Like the web API it only reads snapshot() and sends commands to the
// control task, so a slow redraw can never hold up the heater. Screens:
//   home      big temperature and humidity, the reel, the mode, and mode buttons
//   material  pick a material for Dry or Print
//   settings  dryer name / address / version, touch flip, forget Wi-Fi, and the way to the scale
//   scale     tare, two-point calibration, empty reel weight, temperature-drift learning
//
// UI_SIM builds the screens on a PC (no LovyanGFX, no ESP-IDF) to check the layout: see
// tools/ui_sim/run.sh.
#pragma once
#include <lvgl.h>
#ifndef UI_SIM
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include <esp_heap_caps.h>
#endif

namespace ui {

static constexpr int W = 320, H = 240;

// ------------------------------------------------------------------------------------------------ hardware
#ifndef UI_SIM
class Lcd : public lgfx::LGFX_Device {
  lgfx::Panel_ILI9341 panel_;
  lgfx::Bus_SPI bus_;
  lgfx::Touch_FT5x06 touch_;   // the FT6336 speaks the same protocol

 public:
  Lcd() {
    {
      auto c = bus_.config();
      c.spi_host = SPI2_HOST;
      c.spi_mode = 0;
      c.freq_write = 40000000;
      c.freq_read = 16000000;
      c.pin_sclk = pin::TFT_SCK;
      c.pin_mosi = pin::TFT_MOSI;
      c.pin_miso = -1;
      c.pin_dc = pin::TFT_DC;
      c.dma_channel = SPI_DMA_CH_AUTO;
      bus_.config(c);
      panel_.setBus(&bus_);
    }
    {
      auto c = panel_.config();
      c.pin_cs = pin::TFT_CS;
      c.pin_rst = pin::TFT_RST;
      c.panel_width = 240;
      c.panel_height = 320;
      c.readable = false;
      panel_.config(c);
    }
    {
      auto c = touch_.config();
      c.i2c_port = 1;
      c.pin_sda = pin::TP_SDA;
      c.pin_scl = pin::TP_SCL;
      c.pin_int = pin::TP_INT;
      c.pin_rst = pin::TP_RST;
      c.i2c_addr = 0x38;
      c.freq = 400000;
      c.x_min = 0; c.x_max = 239;
      c.y_min = 0; c.y_max = 319;
      touch_.config(c);
      panel_.setTouch(&touch_);
    }
    setPanel(&panel_);
  }
};

static Lcd lcd;
#endif
static constexpr uint32_t kBacklightOffMs = 10UL * 60 * 1000;   // dark after 10 min untouched
static bool backlightOn = true;
static uint32_t lastTouchMs = 0;
[[maybe_unused]] static bool swallowTouch = false;

static void setBacklight(bool on) {
  ledcWrite(0, on ? 255 : 0);
  backlightOn = on;
}

// ------------------------------------------------------------------------------------------------ helpers
static void send(CmdType t, int material = 0, float value = 0, Mode mode = Mode::Off) {
  Cmd c{};
  c.type = t; c.material = material; c.value = value; c.mode = mode;
  sendCmd(c);
}
static void click() { send(CmdType::Beep, 0, 25); }

static lv_obj_t* label(lv_obj_t* parent, const lv_font_t* font, const char* text = "") {
  lv_obj_t* l = lv_label_create(parent);
  lv_obj_set_style_text_font(l, font, 0);
  lv_label_set_text(l, text);
  return l;
}

static lv_obj_t* button(lv_obj_t* parent, const char* text, lv_event_cb_t cb, void* data = nullptr, int w = LV_SIZE_CONTENT, int h = 40) {
  lv_obj_t* b = lv_btn_create(parent);
  lv_obj_set_size(b, w, h);
  lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, data);
  lv_obj_t* l = lv_label_create(b);
  lv_label_set_text(l, text);
  lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_center(l);
  return b;
}

static lv_obj_t* row(lv_obj_t* parent) {
  lv_obj_t* r = lv_obj_create(parent);
  lv_obj_remove_style_all(r);
  lv_obj_set_size(r, LV_PCT(100), LV_SIZE_CONTENT);
  lv_obj_set_flex_flow(r, LV_FLEX_FLOW_ROW);
  lv_obj_set_flex_align(r, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
  lv_obj_set_style_pad_column(r, 6, 0);
  return r;
}

static void onBackTo(lv_event_t* e);
// A screen with a title, a Back button in the title bar (to *backTo) and a scrolling column.
static lv_obj_t* page(const char* title, lv_obj_t** body, lv_obj_t** backTo) {
  lv_obj_t* scr = lv_obj_create(nullptr);
  lv_obj_t* t = label(scr, &lv_font_montserrat_20, title);
  lv_obj_align(t, LV_ALIGN_TOP_LEFT, 8, 8);
  lv_obj_t* back = button(scr, LV_SYMBOL_LEFT " Back", onBackTo, backTo, 92, 34);
  lv_obj_align(back, LV_ALIGN_TOP_RIGHT, -6, 4);
  lv_obj_t* b = lv_obj_create(scr);
  lv_obj_remove_style_all(b);
  lv_obj_set_size(b, W, H - 44);
  lv_obj_align(b, LV_ALIGN_TOP_LEFT, 0, 44);
  lv_obj_set_flex_flow(b, LV_FLEX_FLOW_COLUMN);
  lv_obj_set_style_pad_hor(b, 8, 0);
  lv_obj_set_style_pad_bottom(b, 8, 0);
  lv_obj_set_style_pad_row(b, 6, 0);
  lv_obj_add_flag(b, LV_OBJ_FLAG_SCROLLABLE);
  *body = b;
  return scr;
}

// ------------------------------------------------------------------------------------------------ screens
static lv_obj_t *scrHome, *scrMaterial, *scrSettings, *scrScale;
// home
static lv_obj_t *lblMode, *lblNet, *lblTemp, *lblRh, *lblReel, *lblInfo, *banner, *lblBanner;
static lv_obj_t* modeBtns[4];   // Dry, Keep dry, Print, Off
// material picker
static lv_obj_t* lblMatTitle;
static Mode pickFor = Mode::Dry;
static lv_obj_t* matLabels[16];
// settings
static lv_obj_t *lblAbout, *lblFlip;
// scale
static lv_obj_t *lblCells, *lblCal, *lblWeight, *lblEmpty, *lblDrift, *btnLearnLbl;
static int calWeight = 500, emptyReel = -1;
static bool learningShown = false;

static void go(lv_obj_t* scr) { lv_scr_load_anim(scr, LV_SCR_LOAD_ANIM_NONE, 0, 0, false); }

static void onBackTo(lv_event_t* e) { click(); go(*(lv_obj_t**)lv_event_get_user_data(e)); }

static void fillMaterials() {
  static char texts[16][32];
  lv_label_set_text(lblMatTitle, pickFor == Mode::Dry ? "Dry: material?" : "Print: material?");
  for (size_t i = 0; i < MATERIAL_COUNT && i < 16; i++) {
    const Material& m = MATERIALS[i];
    float c = pickFor == Mode::Dry ? m.dryC : m.feedC;
    if (c > 65) c = 65;   // the controller caps it too
    if (pickFor == Mode::Dry)
      snprintf(texts[i], sizeof texts[i], "%s\n%.0f\xC2\xB0" "C \xE2\x80\xA2 %lu h", m.name, c, (unsigned long)(m.dryMin / 60));
    else
      snprintf(texts[i], sizeof texts[i], "%s\n%.0f\xC2\xB0" "C", m.name, c);
    lv_label_set_text(matLabels[i], texts[i]);
  }
}

static void onModeBtn(lv_event_t* e) {
  click();
  Mode m = (Mode)(intptr_t)lv_event_get_user_data(e);
  if (m == Mode::Dry || m == Mode::Print) {   // these need a material first
    pickFor = m;
    fillMaterials();
    go(scrMaterial);
    return;
  }
  send(CmdType::SetMode, 0, 0, m);
}

static void onMaterial(lv_event_t* e) {
  click();
  int idx = (int)(intptr_t)lv_event_get_user_data(e);
  send(CmdType::SetMaterial, idx);
  send(CmdType::SetMode, 0, 0, pickFor);
  go(scrHome);
}

static void onClearFault(lv_event_t*) { click(); send(CmdType::ClearFault); }
static void onSettings(lv_event_t*) { click(); go(scrSettings); }
static void onScale(lv_event_t*) { click(); go(scrScale); }

static void onFlip(lv_event_t*) {
  click();
  send(CmdType::SetTouchFlip, (g_touchFlip + 1) & 3);
}

static void onForgetWifiConfirm(lv_event_t* e) {
  lv_obj_t* box = lv_event_get_current_target(e);
  const char* txt = lv_msgbox_get_active_btn_text(box);
  if (txt && strcmp(txt, "Forget") == 0) g_wifiResetRequested = true;
  lv_msgbox_close(box);
}
static void onForgetWifi(lv_event_t*) {
  click();
  static const char* btns[] = {"Forget", "Cancel", ""};
  lv_obj_t* box = lv_msgbox_create(nullptr, "Forget Wi-Fi?",
                                   "The dryer restarts and opens its setup hotspot. Heating stops while it restarts.", btns, false);
  lv_obj_add_event_cb(box, onForgetWifiConfirm, LV_EVENT_VALUE_CHANGED, nullptr);
  lv_obj_center(box);
}

static void onTareConfirm(lv_event_t* e) {
  lv_obj_t* box = lv_event_get_current_target(e);
  const char* txt = lv_msgbox_get_active_btn_text(box);
  if (txt && strcmp(txt, "Tare") == 0) send(CmdType::Tare);
  lv_msgbox_close(box);
}
static void onTare(lv_event_t*) {
  click();
  static const char* btns[] = {"Tare", "Cancel", ""};
  lv_obj_t* box = lv_msgbox_create(nullptr, "Tare the scale?",
                                   "Take the reel off first: the axle and its cones only.", btns, false);
  lv_obj_add_event_cb(box, onTareConfirm, LV_EVENT_VALUE_CHANGED, nullptr);
  lv_obj_center(box);
}

static void onCal(lv_event_t* e) {
  click();
  send(CmdType::CalPoint, (int)(intptr_t)lv_event_get_user_data(e), (float)calWeight);
}

static void onWeightStep(lv_event_t* e) {
  click();
  calWeight += (int)(intptr_t)lv_event_get_user_data(e);
  if (calWeight < 50) calWeight = 50;
  if (calWeight > 3000) calWeight = 3000;
  lv_label_set_text_fmt(lblWeight, "%d g", calWeight);
}

static void onEmptyStep(lv_event_t* e) {
  click();
  if (emptyReel < 0) emptyReel = 0;
  emptyReel += (int)(intptr_t)lv_event_get_user_data(e);
  if (emptyReel < 0) emptyReel = 0;
  if (emptyReel > 1000) emptyReel = 1000;
  lv_label_set_text_fmt(lblEmpty, "%d g", emptyReel);
}
static void onEmptySet(lv_event_t*) {
  click();
  if (emptyReel >= 0) send(CmdType::SetEmptyReel, 0, (float)emptyReel);
}

static void onLearn(lv_event_t*) {
  click();
  send(CmdType::LearnDrift, 0, learningShown ? 0.0f : 1.0f);
}

static void buildHome() {
  scrHome = lv_obj_create(nullptr);
  lblMode = label(scrHome, &lv_font_montserrat_20, "");
  lv_obj_set_size(lblMode, 276, 24);
  lv_label_set_long_mode(lblMode, LV_LABEL_LONG_DOT);
  lv_obj_align(lblMode, LV_ALIGN_TOP_LEFT, 8, 6);
  lblNet = label(scrHome, &lv_font_montserrat_20, "");
  lv_obj_align(lblNet, LV_ALIGN_TOP_RIGHT, -8, 6);

  lblTemp = label(scrHome, &lv_font_montserrat_48, "--");
  lv_obj_align(lblTemp, LV_ALIGN_TOP_LEFT, 8, 40);
  lv_obj_t* c1 = label(scrHome, &lv_font_montserrat_14, "Chamber");
  lv_obj_align(c1, LV_ALIGN_TOP_LEFT, 10, 96);
  lblRh = label(scrHome, &lv_font_montserrat_48, "--");
  lv_obj_align(lblRh, LV_ALIGN_TOP_RIGHT, -8, 40);
  lv_obj_t* c2 = label(scrHome, &lv_font_montserrat_14, "Humidity");
  lv_obj_align(c2, LV_ALIGN_TOP_RIGHT, -10, 96);

  lblReel = label(scrHome, &lv_font_montserrat_20, "");
  lv_obj_align(lblReel, LV_ALIGN_TOP_LEFT, 8, 124);
  lblInfo = label(scrHome, &lv_font_montserrat_14, "");
  lv_obj_set_width(lblInfo, W - 16);
  lv_label_set_long_mode(lblInfo, LV_LABEL_LONG_DOT);
  lv_obj_align(lblInfo, LV_ALIGN_TOP_LEFT, 8, 154);

  lv_obj_t* r = row(scrHome);
  lv_obj_set_style_pad_hor(r, 6, 0);
  lv_obj_align(r, LV_ALIGN_BOTTOM_MID, 0, -6);
  static const struct { const char* t; Mode m; int w; } mb[] = {
      {"Dry", Mode::Dry, 56}, {"Keep dry", Mode::KeepDry, 80}, {"Print", Mode::Print, 58}, {"Off", Mode::Off, 52}};
  for (int i = 0; i < 4; i++) modeBtns[i] = button(r, mb[i].t, onModeBtn, (void*)(intptr_t)mb[i].m, mb[i].w, 44);
  button(r, LV_SYMBOL_SETTINGS, onSettings, nullptr, 44, 44);

  // fault banner over the top of everything
  banner = lv_obj_create(scrHome);
  lv_obj_set_size(banner, W - 12, 90);
  lv_obj_align(banner, LV_ALIGN_TOP_MID, 0, 36);
  lv_obj_set_style_bg_color(banner, lv_palette_main(LV_PALETTE_RED), 0);
  lv_obj_set_style_border_width(banner, 0, 0);
  lv_obj_clear_flag(banner, LV_OBJ_FLAG_SCROLLABLE);
  lblBanner = label(banner, &lv_font_montserrat_20, "");
  lv_obj_set_width(lblBanner, W - 140);
  lv_label_set_long_mode(lblBanner, LV_LABEL_LONG_WRAP);
  lv_obj_set_style_text_color(lblBanner, lv_color_white(), 0);
  lv_obj_align(lblBanner, LV_ALIGN_LEFT_MID, 0, 0);
  lv_obj_t* cb = button(banner, "Clear", onClearFault, nullptr, 90, 44);
  lv_obj_align(cb, LV_ALIGN_RIGHT_MID, 0, 0);
  lv_obj_add_flag(banner, LV_OBJ_FLAG_HIDDEN);
}

static void buildMaterial() {
  scrMaterial = lv_obj_create(nullptr);
  lblMatTitle = label(scrMaterial, &lv_font_montserrat_20, "");
  lv_obj_align(lblMatTitle, LV_ALIGN_TOP_LEFT, 8, 8);
  lv_obj_t* back = button(scrMaterial, LV_SYMBOL_LEFT " Back", onBackTo, &scrHome, 92, 34);
  lv_obj_align(back, LV_ALIGN_TOP_RIGHT, -6, 4);
  lv_obj_t* grid = lv_obj_create(scrMaterial);
  lv_obj_remove_style_all(grid);
  lv_obj_set_size(grid, W, H - 44);
  lv_obj_align(grid, LV_ALIGN_TOP_LEFT, 0, 44);
  lv_obj_set_flex_flow(grid, LV_FLEX_FLOW_ROW_WRAP);
  lv_obj_set_style_pad_all(grid, 6, 0);
  lv_obj_set_style_pad_gap(grid, 6, 0);
  for (size_t i = 0; i < MATERIAL_COUNT && i < 16; i++) {
    lv_obj_t* b = button(grid, "", onMaterial, (void*)(intptr_t)i, 97, 56);
    matLabels[i] = lv_obj_get_child(b, 0);
  }
}

static void buildSettings() {
  lv_obj_t* body;
  scrSettings = page("Settings", &body, &scrHome);
  button(body, "Scale and calibration " LV_SYMBOL_RIGHT, onScale, nullptr, LV_PCT(100), 44);
  lblAbout = label(body, &lv_font_montserrat_14, "");
  lv_obj_t* r = row(body);
  button(r, "Flip touch", onFlip, nullptr, 120, 40);
  lblFlip = label(r, &lv_font_montserrat_14, "");
  button(body, LV_SYMBOL_WIFI " Forget Wi-Fi", onForgetWifi, nullptr, LV_PCT(100), 40);
}

static void buildScale() {
  lv_obj_t* body;
  scrScale = page("Scale", &body, &scrSettings);
  lblCells = label(body, &lv_font_montserrat_14, "");
  lblCal = label(body, &lv_font_montserrat_14, "");
  lv_obj_set_style_text_color(lblCal, lv_palette_main(LV_PALETTE_AMBER), 0);

  lv_obj_t* r1 = row(body);
  label(r1, &lv_font_montserrat_14, "Weight");
  button(r1, LV_SYMBOL_MINUS, onWeightStep, (void*)(intptr_t)-50, 44, 40);
  lblWeight = label(r1, &lv_font_montserrat_20, "500 g");
  button(r1, LV_SYMBOL_PLUS, onWeightStep, (void*)(intptr_t)50, 44, 40);

  lv_obj_t* r2 = row(body);
  button(r2, "Tare", onTare, nullptr, 62, 44);
  button(r2, "Left\nend", onCal, (void*)(intptr_t)CalStep::Left, 70, 44);
  button(r2, "Right\nend", onCal, (void*)(intptr_t)CalStep::Right, 70, 44);
  button(r2, "Middle", onCal, (void*)(intptr_t)CalStep::Centre, 82, 44);

  lv_obj_t* r3 = row(body);
  label(r3, &lv_font_montserrat_14, "Empty reel");
  button(r3, LV_SYMBOL_MINUS, onEmptyStep, (void*)(intptr_t)-5, 40, 40);
  lblEmpty = label(r3, &lv_font_montserrat_20, "");
  button(r3, LV_SYMBOL_PLUS, onEmptyStep, (void*)(intptr_t)5, 40, 40);
  button(r3, "Set", onEmptySet, nullptr, 52, 40);

  lblDrift = label(body, &lv_font_montserrat_14, "");
  lv_obj_t* lb = button(body, "", onLearn, nullptr, LV_PCT(100), 40);
  btnLearnLbl = lv_obj_get_child(lb, 0);
}

// ------------------------------------------------------------------------------------------------ refresh
static const char* faultText(Fault f) {
  switch (f) {
    case Fault::ChamberOverTemp: return "Chamber too hot";
    case Fault::OutletOverTemp: return "Heater outlet too hot (blower?)";
    case Fault::ChamberSensor: return "Chamber probe not answering";
    case Fault::OutletSensor: return "Heater-outlet probe not answering";
    case Fault::NoTempRise: return "Heater on, no warming (heater, fuse?)";
    case Fault::RunTooLong: return "Ran too long";
    default: return "";
  }
}

static void refresh(lv_timer_t*) {
  Snapshot s = snapshot();
  uint32_t now = millis();
  if (s.fault != Fault::None && !backlightOn) { setBacklight(true); lastTouchMs = now; }

  // home: mode line
  const char* mat = MATERIALS[s.material].name;
  if (s.mode == Mode::Dry) {
    uint32_t m = s.dryRemainingS / 60;
    lv_label_set_text_fmt(lblMode, "Drying %s %.0f\xC2\xB0" "C \xE2\x80\xA2 %lu:%02lu left", mat, s.setpointC, (unsigned long)(m / 60), (unsigned long)(m % 60));
  } else if (s.mode == Mode::KeepDry) {
    lv_label_set_text(lblMode, s.boost ? "Keep dry: boost 45\xC2\xB0" "C" : "Keep dry");
  } else if (s.mode == Mode::Print) {
    lv_label_set_text_fmt(lblMode, "Print %s %.0f\xC2\xB0" "C", mat, s.setpointC);
  } else {
    lv_label_set_text(lblMode, "Off");
  }
  static const Mode order[4] = {Mode::Dry, Mode::KeepDry, Mode::Print, Mode::Off};
  for (int i = 0; i < 4; i++) {
    if (order[i] == s.mode) lv_obj_add_state(modeBtns[i], LV_STATE_CHECKED);
    else lv_obj_clear_state(modeBtns[i], LV_STATE_CHECKED);
  }
  bool online = WiFi.status() == WL_CONNECTED;   // Wi-Fi icon, amber when not connected
  lv_label_set_text(lblNet, LV_SYMBOL_WIFI);
  lv_obj_set_style_text_color(lblNet, online ? lv_color_white() : lv_palette_main(LV_PALETTE_AMBER), 0);
  lv_obj_set_style_text_opa(lblNet, online ? LV_OPA_COVER : LV_OPA_70, 0);

  if (s.chamberOk) {
    lv_label_set_text_fmt(lblTemp, "%.1f\xC2\xB0" "C", s.chamberC);
    lv_label_set_text_fmt(lblRh, "%.0f%%", s.chamberRh);
  } else {
    lv_label_set_text(lblTemp, "--");
    lv_label_set_text(lblRh, "--");
  }
  if (!s.scaleOk) lv_label_set_text(lblReel, "Scale: no reading");
  else if (!s.scaleCalibrated) lv_label_set_text(lblReel, "Scale: calibrate it");
  else lv_label_set_text_fmt(lblReel, "Reel %.0f g \xE2\x80\xA2 %.0f m", s.gramsLeft, s.metresLeft);
  char outlet[24] = "no outlet probe";
  if (s.outletOk) snprintf(outlet, sizeof outlet, "outlet %.0f\xC2\xB0" "C", s.outletC);
  lv_label_set_text_fmt(lblInfo, "Heater %d%% \xE2\x80\xA2 blower %s \xE2\x80\xA2 %s%s", (int)(s.duty * 100 + 0.5f),
                        s.blower ? "on" : "off", outlet, s.learning ? " \xE2\x80\xA2 learning drift" : "");
  if (s.fault != Fault::None) {
    lv_label_set_text(lblBanner, faultText(s.fault));
    lv_obj_clear_flag(banner, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(banner, LV_OBJ_FLAG_HIDDEN);
  }

  // settings
  lv_label_set_text_fmt(lblAbout, "%s\n%s  %s\nfirmware %s", g_name.c_str(),
                        WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "not connected",
                        WiFi.status() == WL_CONNECTED ? (String(WiFi.RSSI()) + " dBm").c_str() : "", VERSION);
  static const char* flips[] = {"normal", "mirror x", "mirror y", "mirror x + y"};
  lv_label_set_text(lblFlip, flips[g_touchFlip & 3]);

  // scale
  if (s.scaleOk && s.scaleCalibrated)
    lv_label_set_text_fmt(lblCells, "Left %.0f g + right %.0f g = %.0f g\nReel left %.0f g (empty reel %.0f g)", s.cellG[0], s.cellG[1], s.grams,
                          s.gramsLeft, s.emptyReelG);
  else
    lv_label_set_text(lblCells, s.scaleOk ? "Not calibrated: Tare, then Left end and Right end" : "No reading from the load cells");
  lv_label_set_text(lblCal, s.calStatus);
  if (emptyReel < 0) {   // first time: show the stored value
    emptyReel = (int)(s.emptyReelG + 0.5f);
    lv_label_set_text_fmt(lblEmpty, "%d g", emptyReel);
  }
  learningShown = s.learning;
  if (s.learning)
    lv_label_set_text_fmt(lblDrift, "Learning drift: %lu samples over %.1f\xC2\xB0" "C", (unsigned long)s.learnSamples, s.learnSpanC);
  else if (s.driftLearned)
    lv_label_set_text_fmt(lblDrift, "Drift corrected: %.2f g/\xC2\xB0" "C", s.driftGPerC[0] + s.driftGPerC[1]);
  else
    lv_label_set_text(lblDrift, "Drift: not learned (leave a reel on, run one Dry)");
  lv_label_set_text(btnLearnLbl, s.learning ? "Stop learning drift" : "Start learning drift");
}

// ------------------------------------------------------------------------------------------------ LVGL glue
#ifndef UI_SIM
static void flushCb(lv_disp_drv_t* drv, const lv_area_t* a, lv_color_t* px) {
  uint32_t w = a->x2 - a->x1 + 1, h = a->y2 - a->y1 + 1;
  lcd.startWrite();
  lcd.setAddrWindow(a->x1, a->y1, w, h);
  lcd.writePixels((lgfx::rgb565_t*)&px->full, w * h);
  lcd.endWrite();
  lv_disp_flush_ready(drv);
}

static void touchCb(lv_indev_drv_t*, lv_indev_data_t* d) {
  uint16_t x, y;
  if (lcd.getTouch(&x, &y)) {
    lastTouchMs = millis();
    if (!backlightOn) { setBacklight(true); swallowTouch = true; }   // a touch on a dark screen only wakes it
    if (swallowTouch) { d->state = LV_INDEV_STATE_REL; return; }
    uint8_t f = g_touchFlip;
    if (x >= W) x = W - 1;
    if (y >= H) y = H - 1;
    if (f & 1) x = W - 1 - x;
    if (f & 2) y = H - 1 - y;
    d->point.x = x;
    d->point.y = y;
    d->state = LV_INDEV_STATE_PR;
  } else {
    swallowTouch = false;
    d->state = LV_INDEV_STATE_REL;
  }
}

static void uiTask(void*) {
  ledcSetup(0, 5000, 8);
  ledcAttachPin(pin::TFT_BL, 0);
  lcd.init();
  lcd.setRotation(1);   // landscape, 320 x 240
  lcd.fillScreen(TFT_BLACK);
  setBacklight(true);

  lv_init();
  static lv_disp_draw_buf_t buf;
  const size_t px = W * 40;   // two 40-line buffers in DMA-capable RAM
  lv_color_t* b1 = (lv_color_t*)heap_caps_malloc(px * sizeof(lv_color_t), MALLOC_CAP_DMA);
  lv_color_t* b2 = (lv_color_t*)heap_caps_malloc(px * sizeof(lv_color_t), MALLOC_CAP_DMA);
  lv_disp_draw_buf_init(&buf, b1, b2, px);
  static lv_disp_drv_t disp;
  lv_disp_drv_init(&disp);
  disp.hor_res = W;
  disp.ver_res = H;
  disp.flush_cb = flushCb;
  disp.draw_buf = &buf;
  lv_disp_t* d = lv_disp_drv_register(&disp);
  lv_theme_t* th = lv_theme_default_init(d, lv_palette_main(LV_PALETTE_BLUE), lv_palette_main(LV_PALETTE_ORANGE), true, &lv_font_montserrat_14);
  lv_disp_set_theme(d, th);
  static lv_indev_drv_t indev;
  lv_indev_drv_init(&indev);
  indev.type = LV_INDEV_TYPE_POINTER;
  indev.read_cb = touchCb;
  lv_indev_drv_register(&indev);

  buildHome();
  buildMaterial();
  buildSettings();
  buildScale();
  lv_scr_load(scrHome);
  lv_timer_create(refresh, 500, nullptr);
  refresh(nullptr);

  lastTouchMs = millis();
  uint32_t last = millis();
  for (;;) {
    uint32_t now = millis();
    lv_tick_inc(now - last);
    last = now;
    lv_timer_handler();
    if (backlightOn && now - lastTouchMs > kBacklightOffMs) setBacklight(false);
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

static void start() { xTaskCreatePinnedToCore(uiTask, "ui", 16384, nullptr, 1, nullptr, 1); }
#endif

}  // namespace ui
