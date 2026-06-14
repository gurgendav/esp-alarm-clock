#pragma once

#include "esphome/components/lvgl/lvgl_esphome.h"
#include "esphome/components/web_server_base/web_server_base.h"
#include "esphome/core/application.h"
#include "esphome/core/log.h"

// Private LVGL draw APIs are used to render the active screen into small bands.
// This avoids allocating a full 240x240 framebuffer on memory-constrained ESP32-S3 boards.
#include "src/core/lv_obj_draw_private.h"
#include "src/core/lv_refr_private.h"
#include "src/display/lv_display_private.h"
#include "src/draw/lv_draw_private.h"

#ifdef USE_ESP_IDF
#include "esp_http_server.h"
#endif

#include <algorithm>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace alarmv1::screenshot {

static const char *const TAG = "alarmv1_screenshot";
constexpr const char *SCREENSHOT_PATH = "/alarmv1/screenshot.bmp";
constexpr const char *OPEN_MEDIA_PATH = "/alarmv1/open-media";
constexpr const char *OPEN_CLOCK_PATH = "/alarmv1/open-clock";
constexpr uint16_t ALARMV1_SCREENSHOT_BAND_ROWS = 8;

struct CaptureResult {
  SemaphoreHandle_t done{nullptr};
  bool ok{false};
  bool response_started{false};
  std::string error{};

  CaptureResult() { this->done = xSemaphoreCreateBinary(); }
  ~CaptureResult() {
    if (this->done != nullptr) {
      vSemaphoreDelete(this->done);
    }
  }
};

struct NavigationResult {
  SemaphoreHandle_t done{nullptr};
  bool ok{false};
  std::string error{};

  NavigationResult() { this->done = xSemaphoreCreateBinary(); }
  ~NavigationResult() {
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

inline bool send_bmp_header_(httpd_req_t *request, uint16_t width, uint16_t height) {
#ifdef USE_ESP_IDF
  const uint32_t row_bytes = ((static_cast<uint32_t>(width) * 3U + 3U) / 4U) * 4U;
  const uint32_t pixel_bytes = row_bytes * height;
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
  write_le32(header, 40);                                          // header size
  write_le32(header, width);                                       // width
  write_le32(header, static_cast<uint32_t>(-static_cast<int32_t>(height)));  // top-down height
  write_le16(header, 1);                                           // planes
  write_le16(header, 24);                                          // bits per pixel
  write_le32(header, 0);                                           // BI_RGB, no compression
  write_le32(header, pixel_bytes);
  write_le32(header, 2835);                                        // 72 DPI X pixels/meter
  write_le32(header, 2835);                                        // 72 DPI Y pixels/meter
  write_le32(header, 0);                                           // palette colors
  write_le32(header, 0);                                           // important colors

  httpd_resp_set_type(request, "image/bmp");
  httpd_resp_set_hdr(request, "Content-Disposition", "inline; filename=alarmv1-screenshot.bmp");
  httpd_resp_set_hdr(request, "Cache-Control", "no-store, max-age=0");

  return send_chunk_(request, header.data(), header.size());
#else
  return false;
#endif
}

inline bool render_lvgl_band_(lv_obj_t *screen, lv_display_t *display, lv_draw_buf_t *draw_buf, uint16_t width,
                              uint16_t y, uint16_t rows) {
#if LV_USE_SNAPSHOT
  lv_draw_buf_clear(draw_buf, nullptr);

  lv_area_t band_area;
  band_area.x1 = 0;
  band_area.y1 = y;
  band_area.x2 = width - 1;
  band_area.y2 = y + rows - 1;

  lv_layer_t layer;
  lv_layer_init(&layer);
  layer.draw_buf = draw_buf;
  layer.buf_area = band_area;
  layer.color_format = LV_COLOR_FORMAT_RGB565;
  layer._clip_area = band_area;
  layer.phy_clip_area = band_area;

  lv_draw_unit_send_event(nullptr, LV_EVENT_CHILD_CREATED, &layer);

  lv_display_t *old_refresh_display = lv_refr_get_disp_refreshing();
  lv_layer_t *old_layer_head = display->layer_head;
  display->layer_head = &layer;
  lv_refr_set_disp_refreshing(display);

  lv_obj_redraw(&layer, screen);

  layer.all_tasks_added = true;
  while (layer.draw_task_head != nullptr) {
    lv_draw_dispatch_wait_for_request();
    lv_draw_dispatch();
  }

  display->layer_head = old_layer_head;
  lv_refr_set_disp_refreshing(old_refresh_display);

  lv_draw_unit_send_event(nullptr, LV_EVENT_SCREEN_LOAD_START, &layer);
  lv_draw_unit_send_event(nullptr, LV_EVENT_CHILD_DELETED, &layer);
  return true;
#else
  return false;
#endif
}

inline bool stream_lvgl_screen_as_bmp_(httpd_req_t *request, esphome::lvgl::LvglComponent *lvgl,
                                       CaptureResult *result) {
#if LV_USE_SNAPSHOT
  if (lvgl == nullptr || lvgl->get_disp() == nullptr) {
    result->error = "LVGL display is not ready";
    return false;
  }

  lv_display_t *display = lvgl->get_disp();
  lv_obj_t *screen = lvgl->get_screen_active();
  if (screen == nullptr) {
    result->error = "No active LVGL screen";
    return false;
  }

  const uint16_t width = lvgl->get_width();
  const uint16_t height = lvgl->get_height();
  if (width == 0 || height == 0) {
    result->error = "LVGL display returned invalid dimensions";
    return false;
  }

  lv_draw_buf_t *draw_buf = lv_draw_buf_create(width, ALARMV1_SCREENSHOT_BAND_ROWS, LV_COLOR_FORMAT_RGB565,
                                               LV_STRIDE_AUTO);
  if (draw_buf == nullptr || draw_buf->data == nullptr) {
    result->error = "LVGL band snapshot allocation failed";
    if (draw_buf != nullptr) {
      lv_draw_buf_destroy(draw_buf);
    }
    return false;
  }

  const uint32_t row_bytes = ((static_cast<uint32_t>(width) * 3U + 3U) / 4U) * 4U;
  std::vector<uint8_t> row(row_bytes, 0);
  if (row.empty()) {
    result->error = "Could not allocate BMP row buffer";
    lv_draw_buf_destroy(draw_buf);
    return false;
  }

  lv_refr_now(display);

  if (!send_bmp_header_(request, width, height)) {
    result->error = "Could not send BMP header";
    lv_draw_buf_destroy(draw_buf);
    return false;
  }
  result->response_started = true;

  const uint16_t stride = static_cast<uint16_t>(draw_buf->header.stride);
  if (stride < width * 2U) {
    result->error = "LVGL band snapshot returned invalid stride";
    lv_draw_buf_destroy(draw_buf);
    return false;
  }

  for (uint16_t y = 0; y < height; y += ALARMV1_SCREENSHOT_BAND_ROWS) {
    const uint16_t rows = std::min<uint16_t>(ALARMV1_SCREENSHOT_BAND_ROWS, height - y);
    if (!render_lvgl_band_(screen, display, draw_buf, width, y, rows)) {
      result->error = "LVGL band rendering failed";
      lv_draw_buf_destroy(draw_buf);
      return false;
    }

    for (uint16_t band_y = 0; band_y < rows; band_y++) {
      std::fill(row.begin(), row.end(), 0);
      const uint8_t *src = draw_buf->data + (static_cast<size_t>(band_y) * stride);
      for (uint16_t x = 0; x < width; x++) {
        const uint16_t pixel = static_cast<uint16_t>(src[x * 2]) | (static_cast<uint16_t>(src[x * 2 + 1]) << 8);
        const uint8_t r = static_cast<uint8_t>(((pixel >> 11) & 0x1F) * 255 / 31);
        const uint8_t g = static_cast<uint8_t>(((pixel >> 5) & 0x3F) * 255 / 63);
        const uint8_t b = static_cast<uint8_t>((pixel & 0x1F) * 255 / 31);
        row[x * 3] = b;
        row[x * 3 + 1] = g;
        row[x * 3 + 2] = r;
      }
      if (!send_chunk_(request, row.data(), row.size())) {
        result->error = "Could not send BMP row";
        lv_draw_buf_destroy(draw_buf);
        return false;
      }
    }
  }

  lv_draw_buf_destroy(draw_buf);
  return httpd_resp_send_chunk(request, nullptr, 0) == ESP_OK;
#else
  result->error = "LVGL snapshot support is disabled";
  return false;
#endif
}

inline void capture_lvgl_screen_(AsyncWebServerRequest *request, esphome::lvgl::LvglComponent *lvgl,
                                 CaptureResult *result) {
#ifdef USE_ESP_IDF
  httpd_req_t *raw_request = *request;
  result->ok = stream_lvgl_screen_as_bmp_(raw_request, lvgl, result);
#else
  result->error = "AlarmV1 screenshots require the ESP-IDF web server backend";
#endif
  xSemaphoreGive(result->done);
}

inline void execute_navigation_(const std::function<void()> &action, const char *name, NavigationResult *result) {
  if (!action) {
    result->error = "AlarmV1 navigation action is not configured";
    xSemaphoreGive(result->done);
    return;
  }
  action();
  result->ok = true;
  ESP_LOGI(TAG, "AlarmV1 navigation executed: %s", name);
  xSemaphoreGive(result->done);
}

class AlarmV1ScreenshotHandler : public AsyncWebHandler {
 public:
  AlarmV1ScreenshotHandler(esphome::lvgl::LvglComponent *lvgl, std::function<void()> open_media,
                           std::function<void()> open_clock)
      : lvgl_(lvgl), open_media_(std::move(open_media)), open_clock_(std::move(open_clock)) {}

  bool canHandle(AsyncWebServerRequest *request) const override {
    char url_buffer[AsyncWebServerRequest::URL_BUF_SIZE];
    const auto url = request->url_to(url_buffer);
    return request->method() == HTTP_GET &&
           (url == SCREENSHOT_PATH || request->url_to(url_buffer) == OPEN_MEDIA_PATH ||
            request->url_to(url_buffer) == OPEN_CLOCK_PATH);
  }

  void handleRequest(AsyncWebServerRequest *request) override {
    char url_buffer[AsyncWebServerRequest::URL_BUF_SIZE];
    const auto url = request->url_to(url_buffer);
    if (url == OPEN_MEDIA_PATH) {
      this->handle_navigation_request_(request, "open-media", this->open_media_);
      return;
    }
    if (url == OPEN_CLOCK_PATH) {
      this->handle_navigation_request_(request, "open-clock", this->open_clock_);
      return;
    }

    auto result = std::make_shared<CaptureResult>();
    if (result->done == nullptr) {
      request->send(503, "text/plain", "Could not allocate screenshot synchronization primitive");
      return;
    }

    esphome::App.scheduler.set_timeout(this->lvgl_, "alarmv1_screenshot_capture", 0,
                                      [this, request, result]() { capture_lvgl_screen_(request, this->lvgl_, result.get()); });

    if (xSemaphoreTake(result->done, pdMS_TO_TICKS(5000)) != pdTRUE) {
      request->send(504, "text/plain", "Timed out waiting for AlarmV1 LVGL screenshot");
      return;
    }

    if (!result->ok) {
      const std::string message = result->error.empty() ? "AlarmV1 LVGL screenshot failed" : result->error;
      if (!result->response_started) {
        request->send(503, "text/plain", message.c_str());
      } else {
        ESP_LOGW(TAG, "AlarmV1 screenshot failed after BMP response started: %s", message.c_str());
      }
      return;
    }
  }

 protected:
  void handle_navigation_request_(AsyncWebServerRequest *request, const char *name,
                                  const std::function<void()> &action) {
    auto result = std::make_shared<NavigationResult>();
    if (result->done == nullptr) {
      request->send(503, "text/plain", "Could not allocate navigation synchronization primitive");
      return;
    }

    esphome::App.scheduler.set_timeout(this->lvgl_, "alarmv1_screenshot_navigation", 0,
                                      [action, name, result]() { execute_navigation_(action, name, result.get()); });

    if (xSemaphoreTake(result->done, pdMS_TO_TICKS(2000)) != pdTRUE) {
      request->send(504, "text/plain", "Timed out waiting for AlarmV1 navigation");
      return;
    }

    if (!result->ok) {
      const std::string message = result->error.empty() ? "AlarmV1 navigation failed" : result->error;
      request->send(503, "text/plain", message.c_str());
      return;
    }

    std::string message = "OK ";
    message += name;
    request->send(200, "text/plain", message.c_str());
  }

  esphome::lvgl::LvglComponent *lvgl_;
  std::function<void()> open_media_;
  std::function<void()> open_clock_;
};

inline void register_alarmv1_screenshot_endpoint(esphome::lvgl::LvglComponent *lvgl, std::function<void()> open_media,
                                                 std::function<void()> open_clock) {
  static bool registered = false;
  if (registered) {
    return;
  }
  auto *base = esphome::web_server_base::global_web_server_base;
  if (base == nullptr) {
    ESP_LOGW(TAG, "Web server base is not available; screenshot endpoint was not registered");
    return;
  }
  base->add_handler(new AlarmV1ScreenshotHandler(lvgl, std::move(open_media), std::move(open_clock)));
  registered = true;
  ESP_LOGI(TAG, "Registered AlarmV1 screenshot endpoint at %s with navigation endpoints %s and %s", SCREENSHOT_PATH,
           OPEN_MEDIA_PATH, OPEN_CLOCK_PATH);
}

}  // namespace alarmv1::screenshot
