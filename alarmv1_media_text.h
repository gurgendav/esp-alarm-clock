#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>

namespace alarmv1 {
namespace media_text {

inline bool is_supported_ascii(uint32_t codepoint) {
  static constexpr const char *SUPPORTED_ASCII =
      " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz[]_{}|~";
  return codepoint < 0x80 && std::strchr(SUPPORTED_ASCII, static_cast<int>(codepoint)) != nullptr;
}

inline bool is_supported_media_codepoint(uint32_t codepoint) {
  if (is_supported_ascii(codepoint)) {
    return true;
  }
  if (codepoint == 0x00B0 || codepoint == 0x00BB || codepoint == 0x2161 ||
      codepoint == 0x25A0 || codepoint == 0x25B6 || codepoint == 0x266A) {
    return true;
  }
  if (codepoint == 0x0401 || codepoint == 0x0451) {
    return true;
  }
  if (codepoint >= 0x0410 && codepoint <= 0x044F) {
    return true;
  }
  return false;
}

inline bool decode_utf8_codepoint(const std::string &text, size_t offset, uint32_t &codepoint, size_t &length) {
  const auto first = static_cast<uint8_t>(text[offset]);
  if (first < 0x80) {
    codepoint = first;
    length = 1;
    return true;
  }
  if ((first & 0xE0) == 0xC0 && offset + 1 < text.size()) {
    const auto second = static_cast<uint8_t>(text[offset + 1]);
    if ((second & 0xC0) != 0x80) {
      return false;
    }
    codepoint = ((first & 0x1F) << 6) | (second & 0x3F);
    length = 2;
    return codepoint >= 0x80;
  }
  if ((first & 0xF0) == 0xE0 && offset + 2 < text.size()) {
    const auto second = static_cast<uint8_t>(text[offset + 1]);
    const auto third = static_cast<uint8_t>(text[offset + 2]);
    if ((second & 0xC0) != 0x80 || (third & 0xC0) != 0x80) {
      return false;
    }
    codepoint = ((first & 0x0F) << 12) | ((second & 0x3F) << 6) | (third & 0x3F);
    length = 3;
    return codepoint >= 0x800;
  }
  if ((first & 0xF8) == 0xF0 && offset + 3 < text.size()) {
    const auto second = static_cast<uint8_t>(text[offset + 1]);
    const auto third = static_cast<uint8_t>(text[offset + 2]);
    const auto fourth = static_cast<uint8_t>(text[offset + 3]);
    if ((second & 0xC0) != 0x80 || (third & 0xC0) != 0x80 || (fourth & 0xC0) != 0x80) {
      return false;
    }
    codepoint = ((first & 0x07) << 18) | ((second & 0x3F) << 12) |
                ((third & 0x3F) << 6) | (fourth & 0x3F);
    length = 4;
    return codepoint >= 0x10000 && codepoint <= 0x10FFFF;
  }
  return false;
}

inline bool is_space_codepoint(uint32_t codepoint) {
  return codepoint == ' ' || codepoint == '\t' || codepoint == '\n' || codepoint == '\r' ||
         codepoint == 0x00A0 || codepoint == 0x2007 || codepoint == 0x202F;
}

inline const char *sanitize_media_text(const std::string &text, std::string &output) {
  output.clear();
  bool pending_space = false;
  size_t offset = 0;
  while (offset < text.size()) {
    uint32_t codepoint = 0;
    size_t length = 0;
    if (!decode_utf8_codepoint(text, offset, codepoint, length)) {
      offset += 1;
      continue;
    }
    if (is_space_codepoint(codepoint)) {
      pending_space = !output.empty();
    } else if (is_supported_media_codepoint(codepoint)) {
      if (pending_space && !output.empty()) {
        output.push_back(' ');
      }
      output.append(text, offset, length);
      pending_space = false;
    }
    offset += length;
  }
  return output.c_str();
}

inline const char *sanitize(const std::string &text, std::string &output) {
  return sanitize_media_text(text, output);
}

}  // namespace media_text
}  // namespace alarmv1
