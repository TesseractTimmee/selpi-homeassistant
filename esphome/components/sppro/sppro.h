#pragma once

#include "esphome/core/component.h"
#include "esphome/core/defines.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#ifdef USE_SPPRO_CLOCK
#include "esphome/components/time/real_time_clock.h"
#endif
#ifdef USE_SPPRO_BUTTONS
#include "esphome/components/button/button.h"
#include "esphome/core/helpers.h"
#endif
#ifdef USE_SPPRO_PROXY
#include "esphome/components/socket/tcp_client_link.h"
#include "esphome/components/socket/tcp_listener.h"
#endif

#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace esphome::sppro {

#ifdef USE_SPPRO_PROXY
/// TcpListener that also reports the accepted peer's IPv4 (network order), so writes can be
/// allowed per address.
class PeerListener : public socket::TcpListener {
 public:
  void poll(socket::TcpClientLink &link, bool may_accept, uint32_t *peer) {
    if (this->listen_ == nullptr) {
      if (!link.in_backoff())
        this->try_listen_(link);
      return;
    }
    if (may_accept && !link.connected() && this->listen_->ready())
      this->accept_peer_(link, peer);
  }

 protected:
  void accept_peer_(socket::TcpClientLink &link, uint32_t *peer);
};
#endif

/// Words read in this poll cycle, by block. Formulas call M(address); a word that wasn't read
/// (block failed or not polled) sets `missing` and the field isn't published.
class Mem {
 public:
  struct Block {
    uint32_t base;
    uint16_t n;
    uint16_t off;
    bool valid;
  };
  void add_block(uint32_t base, uint16_t n) {
    this->blocks_.push_back({base, n, static_cast<uint16_t>(this->words_.size()), false});
    this->words_.resize(this->words_.size() + n);
  }
  double operator()(uint32_t a) const {
    for (const auto &b : this->blocks_) {
      if (b.valid && a >= b.base && a < b.base + b.n)
        return this->words_[b.off + (a - b.base)];
    }
    this->missing = true;
    return 0;
  }
  int word(uint32_t a) const { return static_cast<int>((*this)(a)); }
  std::vector<Block> &blocks() { return this->blocks_; }
  uint16_t *data(const Block &b) { return this->words_.data() + b.off; }
  mutable bool missing{false};

 protected:
  std::vector<Block> blocks_;
  std::vector<uint16_t> words_;
};

// helpers used by the generated formulas (same meaning as selpi/sppro/live.py)
inline double s16(double x) {
  int v = static_cast<int>(x);
  return v > 32767 ? v - 65536 : v;
}
inline double u32(double lo, double hi) {
  return static_cast<double>(static_cast<uint32_t>(lo) | (static_cast<uint32_t>(hi) << 16));
}
inline double s32(double x) { return static_cast<double>(static_cast<int32_t>(static_cast<uint32_t>(x))); }
inline double smax(double a) { return a; }
template<typename... T> double smax(double a, double b, T... rest) { return smax(a > b ? a : b, rest...); }

using Formula = double (*)(const Mem &);
struct EnumEntry {
  int code;
  const char *label;
};

uint16_t crc16(const uint8_t *data, size_t len);

class SpPro : public PollingComponent, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_CONNECTION; }

  void set_password(const std::string &p) { this->password_ = p; }
  void set_timeout(uint32_t ms) { this->timeout_ms_ = ms; }
  void set_expected_versions(int a, int b, int c, int d, int e, int f) {
    this->expected_ = {a, b, c, d, e, f};
  }
  void set_allow_version_mismatch(bool v) { this->allow_mismatch_ = v; }
  void add_block(uint32_t base, uint16_t n) { this->mem_.add_block(base, n); }
  void add_number(sensor::Sensor *s, Formula f) { this->numbers_.push_back({s, f}); }
  void add_enum(text_sensor::TextSensor *t, Formula f, const EnumEntry *table, size_t len) {
    this->enums_.push_back({t, f, table, len});
  }
  void set_status_sensor(text_sensor::TextSensor *t) { this->status_sensor_ = t; }
  void set_versions_sensor(text_sensor::TextSensor *t) { this->versions_sensor_ = t; }
  void set_errors_sensor(sensor::Sensor *s) { this->errors_sensor_ = s; }
#ifdef USE_SPPRO_CLOCK
  void set_clock(time::RealTimeClock *t, uint32_t interval_ms, uint32_t max_drift_s, bool write) {
    this->clock_ = t;
    this->clock_interval_ms_ = interval_ms;
    this->clock_max_drift_s_ = max_drift_s;
    this->clock_write_ = write;
  }
  void set_clock_drift_sensor(sensor::Sensor *s) { this->clock_drift_sensor_ = s; }
#endif
#ifdef USE_SPPRO_BUTTONS
  /// Front panel button press, sent between polls: 0 generator, 1 ON, 2 silence alarm.
  void request_button(uint8_t which);
#endif
#ifdef USE_SPPRO_PROXY
  void set_proxy_port(uint16_t port) { this->client_.set_port(port); }
  void set_proxy_log_downloads(bool v) { this->proxy_log_downloads_ = v; }
#ifdef USE_SOCKET_IPV4_ALLOW
  void set_proxy_allow(const socket::Ipv4AllowEntry *e, size_t n) { this->listener_.set_allow(e, n); }
  void set_proxy_write_allow(const socket::Ipv4AllowEntry *e, size_t n) { this->write_allow_.set(e, n); }
#endif
#endif

 protected:
  enum class Step : uint8_t {
    NONE, LOGIN_CHALLENGE, LOGIN_ANSWER, LOGIN_CHECK, POLL, PROXY, CLOCK_READ, CLOCK_WRITE, PORT_READ, BUTTON_WRITE
  };
  struct NumberField {
    sensor::Sensor *sensor;
    Formula f;
  };
  struct EnumField {
    text_sensor::TextSensor *sensor;
    Formula f;
    const EnumEntry *table;
    size_t len;
  };

  void send_(Step step, const uint8_t *frame, size_t len, size_t reply_len);
  void query_(Step step, uint32_t address, uint16_t words);
  void on_reply_();
  void on_timeout_();
  void next_own_request_();
  void finish_cycle_();
  void login_failed_(const char *why);
  void set_status_(const std::string &s);
  void count_error_();
  bool versions_ok_();
#ifdef USE_SPPRO_PROXY
  void proxy_loop_();
#endif
#ifdef USE_SPPRO_CLOCK
  bool clock_due_();
  void on_clock_read_(const uint8_t *data);
  time::RealTimeClock *clock_{nullptr};
  sensor::Sensor *clock_drift_sensor_{nullptr};
  uint32_t clock_interval_ms_{3600000};
  uint32_t clock_max_drift_s_{10};
  bool clock_write_{true};
  uint32_t clock_next_{0};
  bool clock_checked_{false};
#endif

  std::string password_;
  uint32_t timeout_ms_{1500};
  std::vector<int> expected_;
  bool allow_mismatch_{false};
  Mem mem_;
  std::vector<NumberField> numbers_;
  std::vector<EnumField> enums_;
  text_sensor::TextSensor *status_sensor_{nullptr};
  text_sensor::TextSensor *versions_sensor_{nullptr};
  sensor::Sensor *errors_sensor_{nullptr};

  bool logged_in_{false};
  uint32_t login_backoff_until_{0};
  uint32_t login_fail_count_{0};
  bool cycle_wanted_{false};
  bool cycling_{false};
  size_t block_idx_{0};
  bool cycle_had_error_{false};
  bool versions_good_{false};

  Step step_{Step::NONE};
  uint32_t sent_at_{0};
  uint8_t tx_[540];
  size_t tx_len_{0};
  uint8_t rx_[540];
  size_t rx_len_{0};
  size_t reply_len_{0};
  uint32_t errors_{0};
  std::string status_;
  std::string versions_text_;

#ifdef USE_SPPRO_BUTTONS
  bool button_step_();
  int8_t button_pending_{-1};
  uint8_t port_{0};  // SP PRO comms port of this link (low byte of 0xa000), 0 = not read yet this session
#endif
#ifdef USE_SPPRO_PROXY
  PeerListener listener_;
  socket::TcpClientLink client_;
  bool client_was_up_{false};
  uint32_t client_peer_{0};
  bool client_may_write_{false};
  bool proxy_log_downloads_{true};
#ifdef USE_SOCKET_IPV4_ALLOW
  socket::Ipv4Allow write_allow_;  // empty = nobody writes (unlike the connect list)
#endif
  uint8_t prx_[540];
  size_t prx_len_{0};
  bool proxy_pending_{false};
  size_t proxy_frame_len_{0};
  uint32_t proxy_frames_{0};
  bool step_last_proxy_{false};
#endif
};

#ifdef USE_SPPRO_BUTTONS
/// An SP PRO front panel button as an ESPHome button. The ON button (ON <-> IDLE, IDLE = no AC output) needs a
/// second press within 30 s; the first only logs a warning.
class SpProButton : public button::Button, public Parented<SpPro> {
 public:
  void set_which(uint8_t which) { this->which_ = which; }

 protected:
  void press_action() override;
  uint8_t which_{0};
  uint32_t asked_at_{0};
};
#endif

}  // namespace esphome::sppro
