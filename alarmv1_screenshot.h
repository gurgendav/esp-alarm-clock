#pragma once

#include "esphome/components/lvgl/lvgl_esphome.h"
#include "esphome/components/web_server_base/web_server_base.h"
#include "esphome/core/application.h"
#include "esphome/core/log.h"

#ifdef USE_ESP_IDF
#include "esp_http_server.h"
#endif

#include <algorithm>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace alarmv1::screenshot {

static const char *const TAG = "alarmv1_screenshot";
constexpr const char *SCREENSHOT_PATH = "/alarmv1/screenshot.bmp";

struct CaptureResult {
  SemaphoreHandle_t done{nullptr};
  bool ok{false};
  std::string error{};
  uint16_t width{0};
  uint16_t height{0};
  uint16_t stride{0};
  std::vector<uint8_t> rgb565{};

  CaptureResult() { this->done = xSemaphoreCreateBinary(); }
  ~CaptureResult() {
    if (this->done != nullptr) {
      vSemaphoreDelete(this->done);
    }
  }
};

inline void write_le16(std::vector<uint8_t> &out, uint16_t value) {
  out.push_back(static_cast<uint8_t>(value & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
}

inline void write_le32(std::vector<uint8_t> &out, uint32_t value) {
  out.push_back(static_cast<uint8_t>(value & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
}

inline bool send_chunk_(httpd_req_t *request, const uint8_t *data, size_t len) {
#ifdef USE_ESP_IDF
  return httpd_resp_send_chunk(request, reinterpret_cast<const char *>(data), len) == ESP_OK;
#else
  return false;
#endif
}

inline bool stream_bmp_(AsyncWebServerRequest *request, const CaptureResult &capture) {
#ifdef USE_ESP_IDF
  httpd_req_t *raw_request = *request;
  const uint32_t row_bytes = ((static_cast<uint32_t>(capture.width) * 3U + 3U) / 4U) * 4U;
  const uint32_t pixel_bytes = row_bytes * capture.height;
  const uint32_t header_bytes = 54U;
  const uint32_t file_bytes = header_bytes + pixel_bytes;

  std::vector<uint8_t> header;
  header.reserve(header_bytes);
  header.push_back('B');
  header.push_back('M');
  write_le32(header, file_bytes);
  write_le16(header, 0);
  write_le16(header, 0);
  write_le32(header, header_bytes);

  // BITMAPINFOHEADER
  write_le32(header, 40);                         // header size
  write_le32(header, capture.width);              // width
  write_le32(header, static_cast<uint32_t>(-static_cast<int32_t>(capture.height)));  // top-down height
  write_le16(header, 1);                          // planes
  write_le16(header, 24);                         // bits per pixel
  write_le32(header, 0);                          // BI_RGB, no compression
  write_le32(header, pixel_bytes);
  write_le32(header, 2835);                       // 72 DPI X pixels/meter
  write_le32(header, 2835);                       // 72 DPI Y pixels/meter
  write_le32(header, 0);                          // palette colors
  write_le32(header, 0);                          // important colors

  httpd_resp_set_type(raw_request, "image/bmp");
  httpd_resp_set_hdr(raw_request, "Content-Disposition", "inline; filename=alarmv1-screenshot.bmp");
  httpd_resp_set_hdr(raw_request, "Cache-Control", "no-store, max-age=0");

  if (!send_chunk_(raw_request, header.data(), header.size())) {
    return false;
  }

  std::vector<uint8_t> row(row_bytes, 0);
  for (uint16_t y = 0; y < capture.height; y++) {
    std::fill(row.begin(), row.end(), 0);
    const uint8_t *src = capture.rgb565.data() + (static_cast<size_t>(y) * capture.stride);
    for (uint16_t x = 0; x < capture.width; x++) {
      const uint16_t pixel = static_cast<uint16_t>(src[x * 2]) | (static_cast<uint16_t>(src[x * 2 + 1]) << 8);
      const uint8_t r = static_cast<uint8_t>(((pixel >> 11) & 0x1F) * 255 / 31);
      const uint8_t g = static_cast<uint8_t>(((pixel >> 5) & 0x3F) * 255 / 63);
      const uint8_t b = static_cast<uint8_t>((pixel & 0x1F) * 255 / 31);
      row[x * 3] = b;
      row[x * 3 + 1] = g;
      row[x * 3 + 2] = r;
    }
    if (!send_chunk_(raw_request, row.data(), row.size())) {
      return false;
    }
  }

  return httpd_resp_send_chunk(raw_request, nullptr, 0) == ESP_OK;
#else
  request->send(501, "text/plain", "AlarmV1 screenshots require the ESP-IDF web server backend");
  return false;
#endif
}

inline void capture_lvgl_screen_(esphome::lvgl::LvglComponent *lvgl, CaptureResult *result) {
#if LV_USE_SNAPSHOT
  if (lvgl == nullptr || lvgl->get_disp() == nullptr) {
    result->error = "LVGL display is not ready";
    xSemaphoreGive(result->done);
    return;
  }

  lv_obj_t *screen = lvgl->get_screen_active();
  if (screen == nullptr) {
    result->error = "No active LVGL screen";
    xSemaphoreGive(result->done);
    return;
  }

  lv_refr_now(lvgl->get_disp());
  lv_draw_buf_t *snapshot = lv_snapshot_take(screen, LV_COLOR_FORMAT_RGB565);
  if (snapshot == nullptr || snapshot->data == nullptr) {
    result->error = "LVGL snapshot allocation failed";
    if (snapshot != nullptr) {
      lv_draw_buf_destroy(snapshot);
    }
    xSemaphoreGive(result->done);
    return;
  }

  result->width = static_cast<uint16_t>(snapshot->header.w);
  result->height = static_cast<uint16_t>(snapshot->header.h);
  result->stride = static_cast<uint16_t>(snapshot->header.stride);
  const size_t data_size = static_cast<size_t>(result->stride) * result->height;

  if (result->width == 0 || result->height == 0 || result->stride < result->width * 2U || data_size == 0) {
    result->error = "LVGL snapshot returned invalid dimensions";
    lv_draw_buf_destroy(snapshot);
    xSemaphoreGive(result->done);
    return;
  }

  result->rgb565.assign(snapshot->data, snapshot->data + data_size);
  result->ok = true;
  lv_draw_buf_destroy(snapshot);
#else
  result->error = "LVGL snapshot support is disabled";
#endif
  xSemaphoreGive(result->done);
}

class AlarmV1ScreenshotHandler : public AsyncWebHandler {
 public:
  explicit AlarmV1ScreenshotHandler(esphome::lvgl::LvglComponent *lvgl) : lvgl_(lvgl) {}

  bool canHandle(AsyncWebServerRequest *request) const override {
    char url_buffer[AsyncWebServerRequest::URL_BUF_SIZE];
    return request->method() == HTTP_GET && request->url_to(url_buffer) == SCREENSHOT_PATH;
  }

  void handleRequest(AsyncWebServerRequest *request) override {
    auto result = std::make_shared<CaptureResult>();
    if (result->done == nullptr) {
      request->send(503, "text/plain", "Could not allocate screenshot synchronization primitive");
      return;
    }

    esphome::App.scheduler.set_timeout(this->lvgl_, "alarmv1_screenshot_capture", 0,
                                      [this, result]() { capture_lvgl_screen_(this->lvgl_, result.get()); });

    if (xSemaphoreTake(result->done, pdMS_TO_TICKS(5000)) != pdTRUE) {
      request->send(504, "text/plain", "Timed out waiting for AlarmV1 LVGL screenshot");
      return;
    }

    if (!result->ok) {
      const std::string message = result->error.empty() ? "AlarmV1 LVGL screenshot failed" : result->error;
      request->send(503, "text/plain", message.c_str());
      return;
    }

    if (!stream_bmp_(request, *result)) {
      ESP_LOGW(TAG, "Failed to stream AlarmV1 screenshot BMP response");
    }
  }

 protected:
  esphome::lvgl::LvglComponent *lvgl_;
};

inline void register_alarmv1_screenshot_endpoint(esphome::lvgl::LvglComponent *lvgl) {
  static bool registered = false;
  if (registered) {
    return;
  }
  auto *base = esphome::web_server_base::global_web_server_base;
  if (base == nullptr) {
    ESP_LOGW(TAG, "Web server base is not available; screenshot endpoint was not registered");
    return;
  }
  base->add_handler(new AlarmV1ScreenshotHandler(lvgl));
  registered = true;
  ESP_LOGI(TAG, "Registered AlarmV1 screenshot endpoint at %s", SCREENSHOT_PATH);
}

}  // namespace alarmv1::screenshot
