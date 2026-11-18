#include "sppro.h"

#include "esphome/components/md5/md5.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <span>
#include <cinttypes>
#include <cstring>

namespace esphome::sppro {

static const char *const TAG = "sppro";
static const uint32_t LOGIN_ADDRESS = 0x1f0000;   // 8 words challenge; write the answer here
static const uint32_t LOGIN_STATUS = 0x1f0010;    // 1 = logged in
static const uint32_t VERSION_BASE = 0xa007;
static const uint32_t CLOCK_READ = 0x1d0000;   // 8 words BCD: ?, sec, min, hour, weekday (Sun=1), day, month, year
static const uint32_t CLOCK_SET = 0x1d0011;    // 7 words BCD: sec, min, hour, weekday, day, month, year
// Front panel buttons (SP LINK Quick View, selpi sppro/buttons.py): the low byte of 0xa000 is the comms port this
// link is on; each port has its own registers: generator, ON, silence at 0xa232.. (port 1) / 0xa235.. (port 2).
// Write 1 for a short press, 2 for a long press; the SP PRO logs it as a front panel press.
static const uint32_t PORT_REGISTER = 0xa000;
static const char *const BUTTON_NAMES[3] = {"generator", "ON", "silence alarm"};

// Writes a read-only proxy client may still make: what a log download needs (selpi sppro/logs.py):
// download mode 0xa251 = 0/1, and each log's 5-word search range (events, alerts, daily, detailed).
static bool is_log_download_write(const uint8_t *f) {
  uint32_t a = f[2] | (f[3] << 8) | (f[4] << 16) | (static_cast<uint32_t>(f[5]) << 24);
  int words = f[1] + 1;
  if (a == 0xa251)
    return words == 1 && f[9] == 0 && f[8] <= 1;
  return words == 5 && (a == 0xa2d4 || a == 0xa293 || a == 0xa321 || a == 0xa374);
}

static int from_bcd(uint8_t b) { return ((b >> 4) & 0xf) * 10 + (b & 0xf); }
static uint8_t to_bcd(int v) { return static_cast<uint8_t>(((v / 10) << 4) | (v % 10)); }
// days since 1970-01-01 for a civil date (Howard Hinnant's algorithm)
static int64_t days_from_civil(int y, int m, int d) {
  y -= m <= 2;
  const int64_t era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = static_cast<unsigned>(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + static_cast<int64_t>(doe) - 719468;
}

// FCS table (selpi memory/crc.py). A frame with its CRC appended has CRC 0.
static const uint16_t FCS[256] = {
    0x0000, 0x1189, 0x2312, 0x329b, 0x4624, 0x57ad, 0x6536, 0x74bf, 0x8c48, 0x9dc1, 0xaf5a, 0xbed3, 0xca6c, 0xdbe5,
    0xe97e, 0xf8f7, 0x1081, 0x0108, 0x3393, 0x221a, 0x56a5, 0x472c, 0x75b7, 0x643e, 0x9cc9, 0x8d40, 0xbfdb, 0xae52,
    0xdaed, 0xcb64, 0xf9ff, 0xe876, 0x2102, 0x308b, 0x0210, 0x1399, 0x6726, 0x76af, 0x4434, 0x55bd, 0xad4a, 0xbcc3,
    0x8e58, 0x9fd1, 0xeb6e, 0xfae7, 0xc87c, 0xd9f5, 0x3183, 0x200a, 0x1291, 0x0318, 0x77a7, 0x662e, 0x54b5, 0x453c,
    0xbdcb, 0xac42, 0x9ed9, 0x8f50, 0xfbef, 0xea66, 0xd8fd, 0xc974, 0x4204, 0x538d, 0x6116, 0x709f, 0x0420, 0x15a9,
    0x2732, 0x36bb, 0xce4c, 0xdfc5, 0xed5e, 0xfcd7, 0x8868, 0x99e1, 0xab7a, 0xbaf3, 0x5285, 0x430c, 0x7197, 0x601e,
    0x14a1, 0x0528, 0x37b3, 0x263a, 0xdecd, 0xcf44, 0xfddf, 0xec56, 0x98e9, 0x8960, 0xbbfb, 0xaa72, 0x6306, 0x728f,
    0x4014, 0x519d, 0x2522, 0x34ab, 0x0630, 0x17b9, 0xef4e, 0xfec7, 0xcc5c, 0xddd5, 0xa96a, 0xb8e3, 0x8a78, 0x9bf1,
    0x7387, 0x620e, 0x5095, 0x411c, 0x35a3, 0x242a, 0x16b1, 0x0738, 0xffcf, 0xee46, 0xdcdd, 0xcd54, 0xb9eb, 0xa862,
    0x9af9, 0x8b70, 0x8408, 0x9581, 0xa71a, 0xb693, 0xc22c, 0xd3a5, 0xe13e, 0xf0b7, 0x0840, 0x19c9, 0x2b52, 0x3adb,
    0x4e64, 0x5fed, 0x6d76, 0x7cff, 0x9489, 0x8500, 0xb79b, 0xa612, 0xd2ad, 0xc324, 0xf1bf, 0xe036, 0x18c1, 0x0948,
    0x3bd3, 0x2a5a, 0x5ee5, 0x4f6c, 0x7df7, 0x6c7e, 0xa50a, 0xb483, 0x8618, 0x9791, 0xe32e, 0xf2a7, 0xc03c, 0xd1b5,
    0x2942, 0x38cb, 0x0a50, 0x1bd9, 0x6f66, 0x7eef, 0x4c74, 0x5dfd, 0xb58b, 0xa402, 0x9699, 0x8710, 0xf3af, 0xe226,
    0xd0bd, 0xc134, 0x39c3, 0x284a, 0x1ad1, 0x0b58, 0x7fe7, 0x6e6e, 0x5cf5, 0x4d7c, 0xc60c, 0xd785, 0xe51e, 0xf497,
    0x8028, 0x91a1, 0xa33a, 0xb2b3, 0x4a44, 0x5bcd, 0x6956, 0x78df, 0x0c60, 0x1de9, 0x2f72, 0x3efb, 0xd68d, 0xc704,
    0xf59f, 0xe416, 0x90a9, 0x8120, 0xb3bb, 0xa232, 0x5ac5, 0x4b4c, 0x79d7, 0x685e, 0x1ce1, 0x0d68, 0x3ff3, 0x2e7a,
    0xe70e, 0xf687, 0xc41c, 0xd595, 0xa12a, 0xb0a3, 0x8238, 0x93b1, 0x6b46, 0x7acf, 0x4854, 0x59dd, 0x2d62, 0x3ceb,
    0x0e70, 0x1ff9, 0xf78f, 0xe606, 0xd49d, 0xc514, 0xb1ab, 0xa022, 0x92b9, 0x8330, 0x7bc7, 0x6a4e, 0x58d5, 0x495c,
    0x3de3, 0x2c6a, 0x1ef1, 0x0f78};

uint16_t crc16(const uint8_t *data, size_t len) {
  uint16_t n = 0;
  for (size_t i = 0; i < len; i++)
    n = (n >> 8) ^ FCS[(n ^ data[i]) & 0xff];
  return n;
}

static size_t put_header(uint8_t *f, char type, uint32_t address, uint16_t words) {
  f[0] = static_cast<uint8_t>(type);
  f[1] = static_cast<uint8_t>(words - 1);
  for (int i = 0; i < 4; i++)
    f[2 + i] = static_cast<uint8_t>(address >> (8 * i));
  uint16_t c = crc16(f, 6);
  f[6] = c & 0xff;
  f[7] = c >> 8;
  return 8;
}

static uint32_t frame_address(const uint8_t *f) {
  return f[2] | (f[3] << 8) | (f[4] << 16) | (static_cast<uint32_t>(f[5]) << 24);
}

// Total length of a request frame (Q or W) and of its reply.
static size_t request_len(const uint8_t *f) { return f[0] == 'Q' ? 8 : 8 + 2 * (f[1] + 1) + 2; }
static size_t reply_len_for(const uint8_t *f) { return f[0] == 'Q' ? 8 + 2 * (f[1] + 1) + 2 : request_len(f); }

void SpPro::setup() {
  this->login_backoff_until_ = millis() + 1000;  // let the link (USB enumeration / TCP) come up
#ifdef USE_SPPRO_PROXY
  this->client_.begin(TAG);
  this->listener_.begin(TAG);
#endif
  this->set_status_("connecting");
}

void SpPro::dump_config() {
  ESP_LOGCONFIG(TAG,
                "SP PRO:\n"
                "  Fields: %u numbers, %u text\n"
                "  Blocks: %u\n"
                "  Reply timeout: %" PRIu32 " ms",
                (unsigned) this->numbers_.size(), (unsigned) this->enums_.size(),
                (unsigned) this->mem_.blocks().size(), this->timeout_ms_);
  for (auto &b : this->mem_.blocks())
    ESP_LOGCONFIG(TAG, "    0x%04" PRIx32 " x%u", b.base, b.n);
#ifdef USE_SPPRO_PROXY
  ESP_LOGCONFIG(TAG, "  Proxy port: %u", this->client_.port());
  this->listener_.dump_config();
#ifdef USE_SOCKET_IPV4_ALLOW
  for (size_t i = 0; i < this->write_allow_.size(); i++) {
    auto e = this->write_allow_.entry(i);
    ESP_LOGCONFIG(TAG, "  May write: %u.%u.%u.%u/%d", (unsigned) (e.addr & 0xff), (unsigned) ((e.addr >> 8) & 0xff),
                  (unsigned) ((e.addr >> 16) & 0xff), (unsigned) (e.addr >> 24), __builtin_popcount(e.mask));
  }
  if (this->write_allow_.size() == 0)
    ESP_LOGCONFIG(TAG, "  May write: nobody (login frames only)");
#endif
#endif
  LOG_UPDATE_INTERVAL(this);
}

void SpPro::update() { this->cycle_wanted_ = true; }

void SpPro::set_status_(const std::string &s) {
  if (s == this->status_)
    return;
  this->status_ = s;
  ESP_LOGI(TAG, "status: %s", s.c_str());
  if (this->status_sensor_ != nullptr)
    this->status_sensor_->publish_state(s);
}

void SpPro::count_error_() {
  this->errors_++;
  if (this->errors_sensor_ != nullptr)
    this->errors_sensor_->publish_state(this->errors_);
}

void SpPro::send_(Step step, const uint8_t *frame, size_t len, size_t reply_len) {
  uint8_t junk;
  while (this->available() && this->read_byte(&junk)) {
  }  // stale bytes from a late reply
  if (frame != this->tx_)
    std::memcpy(this->tx_, frame, len);
  this->tx_len_ = len;
  this->write_array(this->tx_, len);
  this->step_ = step;
  this->reply_len_ = reply_len;
  this->rx_len_ = 0;
  this->sent_at_ = millis();
}

void SpPro::query_(Step step, uint32_t address, uint16_t words) {
  put_header(this->tx_, 'Q', address, words);
  this->send_(step, this->tx_, 8, 8 + 2 * words + 2);
}

void SpPro::loop() {
#ifdef USE_SPPRO_PROXY
  this->proxy_loop_();
#endif
  if (this->step_ != Step::NONE) {
    while (this->rx_len_ < this->reply_len_ && this->available()) {
      size_t n = std::min<size_t>(this->available(), this->reply_len_ - this->rx_len_);
      if (!this->read_array(this->rx_ + this->rx_len_, n))
        break;
      this->rx_len_ += n;
    }
    if (this->rx_len_ >= this->reply_len_) {
      this->on_reply_();
    } else if (millis() - this->sent_at_ > this->timeout_ms_) {
      this->on_timeout_();
    }
    if (this->step_ != Step::NONE)
      return;
  }
#ifdef USE_SPPRO_PROXY
  bool own_work = this->cycling_ || this->cycle_wanted_ || (!this->logged_in_ && millis() >= this->login_backoff_until_);
  if (this->proxy_pending_ && (this->step_last_proxy_ == false || !own_work)) {
    size_t n = this->proxy_frame_len_;
    this->send_(Step::PROXY, this->prx_, n, reply_len_for(this->prx_));
    std::memmove(this->prx_, this->prx_ + n, this->prx_len_ - n);
    this->prx_len_ -= n;
    this->proxy_pending_ = false;
    this->step_last_proxy_ = true;
    return;
  }
  this->step_last_proxy_ = false;
#endif
  this->next_own_request_();
}

void SpPro::next_own_request_() {
  if (!this->logged_in_) {
    if (millis() >= this->login_backoff_until_)
      this->query_(Step::LOGIN_CHALLENGE, LOGIN_ADDRESS, 8);
    return;
  }
  if (!this->cycling_) {
#ifdef USE_SPPRO_BUTTONS
    if (this->button_step_())
      return;
#endif
#ifdef USE_SPPRO_CLOCK
    if (this->clock_due_()) {
      this->clock_next_ = millis() + this->clock_interval_ms_;
      this->clock_checked_ = true;
      this->query_(Step::CLOCK_READ, CLOCK_READ, 8);
      return;
    }
#endif
    if (!this->cycle_wanted_)
      return;
    this->cycle_wanted_ = false;
    this->cycling_ = true;
    this->cycle_had_error_ = false;
    this->block_idx_ = 0;
    for (auto &b : this->mem_.blocks())
      b.valid = false;
  }
  auto &blocks = this->mem_.blocks();
  if (this->block_idx_ < blocks.size()) {
    this->query_(Step::POLL, blocks[this->block_idx_].base, blocks[this->block_idx_].n);
  } else {
    this->finish_cycle_();
  }
}

void SpPro::on_reply_() {
  Step step = this->step_;
  this->step_ = Step::NONE;
  bool echo = std::memcmp(this->rx_, this->tx_, this->tx_[0] == 'Q' ? 8 : this->tx_len_) == 0;
  bool ok = echo && crc16(this->rx_, this->reply_len_) == 0;
  if (step == Step::PROXY) {
#ifdef USE_SPPRO_PROXY
    if (this->client_.connected())
      this->client_.queue(this->rx_, this->reply_len_);
    this->proxy_frames_++;
#endif
    if (!ok)
      this->count_error_();
    return;
  }
  if (!ok) {
    this->count_error_();
    ESP_LOGW(TAG, "bad reply to %c 0x%" PRIx32 " (%s)", this->tx_[0], frame_address(this->tx_),
             echo ? "CRC" : "header");
    if (step == Step::POLL) {
      this->cycle_had_error_ = true;
      this->block_idx_++;
    } else if (step == Step::CLOCK_READ || step == Step::CLOCK_WRITE) {
      // try again next interval
#ifdef USE_SPPRO_BUTTONS
    } else if (step == Step::PORT_READ || step == Step::BUTTON_WRITE) {
      ESP_LOGW(TAG, "button: %s press not sent (bad reply)", BUTTON_NAMES[std::max<int>(0, this->button_pending_)]);
      this->button_pending_ = -1;  // never resend a press blindly
#endif
    } else {
      this->login_failed_("bad reply");
    }
    return;
  }
  const uint8_t *data = this->rx_ + 8;
  switch (step) {
    case Step::LOGIN_CHALLENGE: {
      // MD5(challenge 16 bytes + password padded to 32 with spaces); send it with each byte pair swapped
      uint8_t buf[48];
      std::memcpy(buf, data, 16);
      std::memset(buf + 16, ' ', 32);
      std::memcpy(buf + 16, this->password_.data(), std::min<size_t>(32, this->password_.size()));
      md5::MD5Digest md5;
      md5.init();
      md5.add(buf, sizeof(buf));
      md5.calculate();
      uint8_t digest[16];
      md5.get_bytes(digest);
      put_header(this->tx_, 'W', LOGIN_ADDRESS, 8);
      for (int i = 0; i < 16; i += 2) {
        this->tx_[8 + i] = digest[i + 1];
        this->tx_[8 + i + 1] = digest[i];
      }
      uint16_t c = crc16(this->tx_, 24);
      this->tx_[24] = c & 0xff;
      this->tx_[25] = c >> 8;
      this->send_(Step::LOGIN_ANSWER, this->tx_, 26, 26);
      break;
    }
    case Step::LOGIN_ANSWER:
      this->query_(Step::LOGIN_CHECK, LOGIN_STATUS, 1);
      break;
    case Step::LOGIN_CHECK:
      if ((data[0] | (data[1] << 8)) == 1) {
        this->logged_in_ = true;
        this->login_fail_count_ = 0;
#ifdef USE_SPPRO_BUTTONS
        this->port_ = 0;  // read it again for this session
#endif
        ESP_LOGI(TAG, "logged in");
        this->set_status_("logged in");
      } else {
        this->login_failed_("password rejected");
      }
      break;
    case Step::POLL: {
      auto &b = this->mem_.blocks()[this->block_idx_];
      uint16_t *w = this->mem_.data(b);
      for (uint16_t i = 0; i < b.n; i++)
        w[i] = data[2 * i] | (data[2 * i + 1] << 8);
      b.valid = true;
      this->block_idx_++;
      break;
    }
#ifdef USE_SPPRO_BUTTONS
    case Step::PORT_READ:
      this->port_ = data[0];
      ESP_LOGD(TAG, "button: link is on SP PRO comms port %u", this->port_);
      if (this->port_ != 1 && this->port_ != 2) {
        ESP_LOGW(TAG, "button: unknown comms port %u, %s press not sent", this->port_,
                 BUTTON_NAMES[std::max<int>(0, this->button_pending_)]);
        this->button_pending_ = -1;
      }
      break;
    case Step::BUTTON_WRITE:
      ESP_LOGI(TAG, "button: %s pressed (0x%" PRIx32 " = %u)", BUTTON_NAMES[std::max<int>(0, this->button_pending_)],
               frame_address(this->tx_), this->tx_[8]);
      this->button_pending_ = -1;
      break;
#endif
#ifdef USE_SPPRO_CLOCK
    case Step::CLOCK_READ:
      this->on_clock_read_(data);
      break;
    case Step::CLOCK_WRITE:
      ESP_LOGI(TAG, "clock: SP PRO clock set");
      this->clock_next_ = millis() + 30000;  // read it back in 30 s
      break;
#endif
    default:
      break;
  }
}

#ifdef USE_SPPRO_BUTTONS
void SpPro::request_button(uint8_t which) {
  if (which > 2)
    return;
  if (this->button_pending_ >= 0) {
    ESP_LOGW(TAG, "button: %s press ignored, %s press still pending", BUTTON_NAMES[which],
             BUTTON_NAMES[this->button_pending_]);
    return;
  }
  if (!this->logged_in_) {
    ESP_LOGW(TAG, "button: %s press ignored, not logged in to the SP PRO", BUTTON_NAMES[which]);
    return;
  }
  this->button_pending_ = static_cast<int8_t>(which);
  ESP_LOGI(TAG, "button: %s press queued", BUTTON_NAMES[which]);
}

// one step of a pending press (port read first, then the write); false = nothing to do
bool SpPro::button_step_() {
  if (this->button_pending_ < 0)
    return false;
  if (this->port_ == 0) {
    this->query_(Step::PORT_READ, PORT_REGISTER, 1);
    return true;
  }
  uint32_t address = (this->port_ == 1 ? 0xa232 : 0xa235) + this->button_pending_;
  uint8_t value = this->button_pending_ == 1 ? 2 : 1;  // ON: long press only; generator, silence: short
  put_header(this->tx_, 'W', address, 1);
  this->tx_[8] = value;
  this->tx_[9] = 0;
  uint16_t c = crc16(this->tx_, 10);
  this->tx_[10] = c & 0xff;
  this->tx_[11] = c >> 8;
  this->send_(Step::BUTTON_WRITE, this->tx_, 12, 12);
  return true;
}

void SpProButton::press_action() {
  if (this->which_ == 1) {  // ON: ON <-> IDLE cuts the AC output, so it takes two presses
    uint32_t now = millis();
    if (this->asked_at_ == 0 || now - this->asked_at_ > 30000) {
      this->asked_at_ = now == 0 ? 1 : now;
      ESP_LOGW(TAG, "button: press ON again within 30 s to switch the SP PRO between ON and IDLE (no AC output)");
      return;
    }
    this->asked_at_ = 0;
  }
  this->parent_->request_button(this->which_);
}
#endif

#ifdef USE_SPPRO_CLOCK
bool SpPro::clock_due_() {
  if (this->clock_ == nullptr || !this->clock_->now().is_valid())
    return false;
  return !this->clock_checked_ || static_cast<int32_t>(millis() - this->clock_next_) >= 0;
}

void SpPro::on_clock_read_(const uint8_t *data) {
  // words are little-endian, the BCD value in the low byte
  int sec = from_bcd(data[2]), min = from_bcd(data[4]), hour = from_bcd(data[6]);
  int day = from_bcd(data[10]), month = from_bcd(data[12]), year = 2000 + from_bcd(data[14]);
  ESPTime now = this->clock_->now();
  if (month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || min > 59 || sec > 59) {
    ESP_LOGW(TAG, "clock: SP PRO clock unreadable (%02x %02x %02x %02x %02x %02x), not setting", data[14], data[12],
             data[10], data[6], data[4], data[2]);
    return;
  }
  int64_t unit = days_from_civil(year, month, day) * 86400 + hour * 3600 + min * 60 + sec;
  int64_t local = days_from_civil(now.year, now.month, now.day_of_month) * 86400 + now.hour * 3600 + now.minute * 60 +
                  now.second;
  int64_t drift = unit - local;  // + = SP PRO ahead
  ESP_LOGD(TAG, "clock: SP PRO %04d-%02d-%02d %02d:%02d:%02d, drift %+lld s", year, month, day, hour, min, sec,
           (long long) drift);
  if (this->clock_drift_sensor_ != nullptr)
    this->clock_drift_sensor_->publish_state(static_cast<float>(drift));
  if (!this->clock_write_ || (drift < 0 ? -drift : drift) <= static_cast<int64_t>(this->clock_max_drift_s_))
    return;
  // set it to local time + 1 s (the write lands a fraction of a second later)
  ESPTime t = ESPTime::from_epoch_local(now.timestamp + 1);
  ESP_LOGI(TAG, "clock: SP PRO is %+lld s out, setting it to %02d:%02d:%02d", (long long) drift, t.hour, t.minute,
           t.second);
  put_header(this->tx_, 'W', CLOCK_SET, 7);
  const int vals[7] = {t.second, t.minute, t.hour, t.day_of_week, t.day_of_month, t.month, t.year % 100};
  for (int i = 0; i < 7; i++) {
    this->tx_[8 + 2 * i] = to_bcd(vals[i]);
    this->tx_[8 + 2 * i + 1] = 0;
  }
  uint16_t c = crc16(this->tx_, 22);
  this->tx_[22] = c & 0xff;
  this->tx_[23] = c >> 8;
  this->send_(Step::CLOCK_WRITE, this->tx_, 24, 24);
}
#endif

void SpPro::on_timeout_() {
  Step step = this->step_;
  this->step_ = Step::NONE;
  this->count_error_();
  ESP_LOGD(TAG, "no reply to %c 0x%" PRIx32 " (%u of %u bytes)", this->tx_[0], frame_address(this->tx_),
           (unsigned) this->rx_len_, (unsigned) this->reply_len_);
  switch (step) {
    case Step::POLL:
      // the unit goes silent when the session isn't logged in: log in again, then retry the cycle
      this->logged_in_ = false;
      this->cycling_ = false;
      this->cycle_wanted_ = true;
      this->set_status_("no reply");
      break;
    case Step::PROXY:
      break;  // the client sees its own timeout
    case Step::CLOCK_READ:
    case Step::CLOCK_WRITE:
      break;  // next interval
#ifdef USE_SPPRO_BUTTONS
    case Step::PORT_READ:
    case Step::BUTTON_WRITE:
      ESP_LOGW(TAG, "button: no reply, %s press not confirmed", BUTTON_NAMES[std::max<int>(0, this->button_pending_)]);
      this->button_pending_ = -1;  // don't resend: it may have landed
      break;
#endif
    default:
      this->login_failed_("no reply");
  }
}

void SpPro::login_failed_(const char *why) {
  this->logged_in_ = false;
  this->login_fail_count_++;
  uint32_t delay = 5000u << std::min<uint32_t>(this->login_fail_count_ - 1, 6);  // 5 s .. 320 s
  this->login_backoff_until_ = millis() + delay;
  ESP_LOGW(TAG, "login failed (%s); retry in %" PRIu32 " s", why, delay / 1000);
  this->set_status_(std::string("login failed: ") + why);
}

bool SpPro::versions_ok_() {
  this->mem_.missing = false;
  char text[96];
  std::snprintf(text, sizeof(text), "settings %d/%d, map %d, logs %d/%d/%d, comms card %d", this->mem_.word(VERSION_BASE),
                this->mem_.word(VERSION_BASE + 1), this->mem_.word(VERSION_BASE + 2), this->mem_.word(VERSION_BASE + 3),
                this->mem_.word(VERSION_BASE + 4), this->mem_.word(VERSION_BASE + 5), this->mem_.word(VERSION_BASE + 20));
  if (this->mem_.missing)
    return this->versions_good_;  // not read this cycle: keep the last verdict
  if (this->versions_text_ != text) {
    this->versions_text_ = text;
    ESP_LOGI(TAG, "unit versions: %s", text);
    if (this->versions_sensor_ != nullptr)
      this->versions_sensor_->publish_state(text);
  }
  bool good = true;
  for (size_t i = 0; i < this->expected_.size(); i++)
    good &= this->mem_.word(VERSION_BASE + i) == this->expected_[i];
  this->versions_good_ = good;
  return good;
}

void SpPro::finish_cycle_() {
  this->cycling_ = false;
  if (!this->versions_ok_() && !this->allow_mismatch_) {
    // field addresses are only known good for the verified map versions: publish nothing
    this->set_status_("version mismatch: " + this->versions_text_);
    return;
  }
  for (auto &f : this->numbers_) {
    this->mem_.missing = false;
    double v = f.f(this->mem_);
    if (!this->mem_.missing && std::isfinite(v)) {
      ESP_LOGV(TAG, "  %s = %.4f", f.sensor->get_name().c_str(), v);
      f.sensor->publish_state(static_cast<float>(v));
    }
  }
  for (auto &f : this->enums_) {
    this->mem_.missing = false;
    int code = static_cast<int>(f.f(this->mem_));
    if (this->mem_.missing)
      continue;
    const char *label = nullptr;
    for (size_t i = 0; i < f.len; i++)
      if (f.table[i].code == code)
        label = f.table[i].label;
    ESP_LOGV(TAG, "  %s = %d (%s)", f.sensor->get_name().c_str(), code, label ? label : "?");
    if (label != nullptr) {
      f.sensor->publish_state(label);
    } else {
      f.sensor->publish_state("code " + std::to_string(code));
    }
  }
  this->set_status_(this->cycle_had_error_ ? "ok (some reads failed)" : "ok");
}

#ifdef USE_SPPRO_PROXY
void PeerListener::accept_peer_(socket::TcpClientLink &link, uint32_t *peer) {
  // as TcpListener::accept_, plus the peer address
  struct sockaddr_storage ss {};
  socklen_t len = sizeof(ss);
  auto client = this->listen_->accept_loop_monitored(reinterpret_cast<struct sockaddr *>(&ss), &len);
  if (client == nullptr) {
    if (errno == EAGAIN || errno == EWOULDBLOCK || errno == ECONNABORTED || errno == EINTR)
      return;
    int err = errno;
    this->listen_.reset();
    ESP_LOGW(this->tag_, "Accept failed: %d", err);
    link.note_attempt();
    return;
  }
  const auto *sa = reinterpret_cast<const struct sockaddr *>(&ss);
  char text[socket::SOCKADDR_STR_LEN];
  socket::format_sockaddr_to(sa, len, std::span<char, socket::SOCKADDR_STR_LEN>(text));
#ifdef USE_SOCKET_IPV4_ALLOW
  if (!this->allow_.allows(sa)) {
    ESP_LOGW(this->tag_, "Rejected %s", text);
    return;
  }
#endif
  *peer = 0;
  socket::sockaddr_to_ipv4(sa, peer);
  link.adopt(std::move(client));
  ESP_LOGI(this->tag_, "Client connected from %s", text);
}

void SpPro::proxy_loop_() {
  this->listener_.poll(this->client_, !this->client_was_up_, &this->client_peer_);
  if (this->client_.connected() != this->client_was_up_) {
    this->client_was_up_ = this->client_.connected();
    this->prx_len_ = 0;
    this->proxy_pending_ = false;
    this->client_may_write_ = false;
#ifdef USE_SOCKET_IPV4_ALLOW
    this->client_may_write_ = this->client_was_up_ && this->client_peer_ != 0 && this->write_allow_.size() != 0 &&
                              this->write_allow_.allows(this->client_peer_);
#endif
    ESP_LOGI(TAG, "proxy client %s%s (%" PRIu32 " frames so far)", this->client_was_up_ ? "connected" : "gone",
             this->client_was_up_ ? (this->client_may_write_ ? ", may write" : ", read-only") : "", this->proxy_frames_);
  }
  if (!this->client_was_up_)
    return;
  if (!this->proxy_pending_ && this->prx_len_ < sizeof(this->prx_) && this->client_.ready()) {
    ssize_t n = this->client_.read(this->prx_ + this->prx_len_, sizeof(this->prx_) - this->prx_len_);
    if (n > 0)
      this->prx_len_ += n;
  }
  while (!this->proxy_pending_ && this->prx_len_ >= 2) {
    if (this->prx_[0] != 'Q' && this->prx_[0] != 'W') {
      std::memmove(this->prx_, this->prx_ + 1, --this->prx_len_);
      continue;
    }
    size_t need = request_len(this->prx_);
    if (this->prx_len_ < need)
      break;
    bool valid = crc16(this->prx_, 8) == 0 && crc16(this->prx_, need) == 0;
    uint32_t address = frame_address(this->prx_);
    bool refused = valid && this->prx_[0] == 'W' && address != LOGIN_ADDRESS && !this->client_may_write_ &&
                   !(this->proxy_log_downloads_ && is_log_download_write(this->prx_));
    if (!valid || refused) {
      if (refused)
        ESP_LOGW(TAG, "proxy: refused write to 0x%" PRIx32 " (client is read-only)", address);
      size_t drop = valid ? need : 1;
      std::memmove(this->prx_, this->prx_ + drop, this->prx_len_ - drop);
      this->prx_len_ -= drop;
      continue;
    }
    this->proxy_frame_len_ = need;
    this->proxy_pending_ = true;
  }
  this->client_.flush_tx();
}
#endif

}  // namespace esphome::sppro
