# selpi field reference

Every field selpi reads from the SP PRO, as served at `/api/v1/fields`. **Default** = enabled by default in Home Assistant (the rest are created disabled; enable any without reconfiguring). **System** = how the field rolls up onto the Powerchain *System* device (summed, averaged, or — for per-inverter-only fields — not shown there). Enum/text fields have no unit.

_Generated from the field catalog; do not edit by hand._

**289 fields** across 10 screens.

## ACHistorySubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Export kWh 30 Day | `ac_exportk_wh30_day_acc` | kWh |  | sum |
| AC Export kWh 30 Day Avg | `ac_exportk_wh30_day_acc_avg` | kWh |  | sum |
| AC Export kWh 365 Day | `ac_exportk_wh365_day_acc` | kWh |  | sum |
| AC Export kWh 365 Day Avg | `ac_exportk_wh365_day_acc_avg` | kWh |  | sum |
| AC Export kWh 7 Day | `ac_exportk_wh7_day_acc` | kWh |  | sum |
| AC Export kWh 7 Day Avg | `ac_exportk_wh7_day_acc_avg` | kWh |  | sum |
| AC Export kWh Previous | `ac_exportk_wh_previous` | kWh |  | sum |
| AC Export kWh Resettable | `ac_exportk_wh_resetable_acc` | kWh |  | sum |
| AC Export kWh Resettable Avg | `ac_exportk_wh_resetable_acc_avg` | kWh |  | sum |
| AC Export kWh Year | `ac_exportk_wh_year_acc` | kWh |  | sum |
| AC Export kWh Year Avg | `ac_exportk_wh_year_acc_avg` | kWh |  | sum |
| AC Input Hours 30 Day | `ac_input_hrs30_day_acc` | h |  | — |
| AC Input Hours 30 Day Avg | `ac_input_hrs30_day_acc_avg` | h |  | — |
| AC Input Hours 365 Day | `ac_input_hrs365_day_acc` | h |  | — |
| AC Input Hours 365 Day Avg | `ac_input_hrs365_day_acc_avg` | h |  | — |
| AC Input Hours 7 Day | `ac_input_hrs7_day_acc` | h |  | — |
| AC Input Hours 7 Day Avg | `ac_input_hrs7_day_acc_avg` | h |  | — |
| AC Input Hours Previous | `ac_input_hrs_previous_acc` | h |  | — |
| AC Input Hours Resettable | `ac_input_hrs_resetable_acc` | h |  | — |
| AC Input Hours Resettable Avg | `ac_input_hrs_resetable_acc_avg` | h |  | — |
| AC Input Hours Total | `ac_input_hrs_total_acc` | h |  | — |
| AC Input Hours Year | `ac_input_hrs_year_acc` | h |  | — |
| AC Input Hours Year Avg | `ac_input_hrs_year_acc_avg` | h |  | — |
| AC Input kWh 30 Day | `ac_input_kwh30_day_acc` | kWh |  | sum |
| AC Input kWh 30 Day Avg | `ac_input_kwh30_day_acc_avg` | kWh |  | sum |
| AC Input kWh 365 Day | `ac_input_kwh365_day_acc` | kWh |  | sum |
| AC Input kWh 365 Day Avg | `ac_input_kwh365_day_acc_avg` | kWh |  | sum |
| AC Input kWh 7 Day | `ac_input_kwh7_day_acc` | kWh |  | sum |
| AC Input kWh 7 Day Avg | `ac_input_kwh7_day_acc_avg` | kWh |  | sum |
| AC Input kWh Previous | `ac_inputk_wh_previous` | kWh |  | sum |
| AC Input kWh Resettable | `ac_input_kwh_resetable_acc` | kWh |  | sum |
| AC Input kWh Resettable Avg | `ac_inputk_wh_resetable_acc_avg` | kWh |  | sum |
| AC Input kWh Year | `ac_input_kwh_year_acc` | kWh |  | sum |
| AC Input kWh Year Avg | `ac_inputk_wh_year_acc_avg` | kWh |  | sum |
| AC Load kWh 30 Day | `ac_load_kwh30_day_acc` | kWh |  | sum |
| AC Load kWh 30 Day Avg | `ac_loadk_wh30_day_acc_avg` | kWh |  | sum |
| AC Load kWh 365 Day | `ac_load_kwh365_day_acc` | kWh |  | sum |
| AC Load kWh 365 Day Avg | `ac_load_kwh365_day_acc_avg` | kWh |  | sum |
| AC Load kWh 7 Day | `ac_load_kwh7_day_acc` | kWh |  | sum |
| AC Load kWh 7 Day Avg | `ac_loadk_wh7_day_acc_avg` | kWh |  | sum |
| AC Load kWh Previous | `ac_loadk_wh_previous_acc` | kWh |  | sum |
| AC Load kWh Resettable | `ac_loadk_wh_resetable_acc` | kWh |  | sum |
| AC Load kWh Resettable Avg | `ac_loadk_wh_resetable_acc_avg` | kWh |  | sum |
| AC Load kWh Year | `ac_loadk_wh_year_acc` | kWh |  | sum |
| AC Load kWh Year Avg | `ac_loadk_wh_year_acc_avg` | kWh |  | sum |
| AC Solar kWh 30 Day | `ac_solar_kacok_wh30_day_acc` | kWh |  | sum |
| AC Solar kWh 30 Day Avg | `ac_solar_kacok_wh30_day_acc_avg` | kWh |  | sum |
| AC Solar kWh 365 Day | `ac_solar_kacok_wh365_day_acc` | kWh |  | sum |
| AC Solar kWh 365 Day Avg | `ac_solar_kacok_wh365_day_acc_avg` | kWh |  | sum |
| AC Solar kWh 7 Day | `ac_solar_kacok_wh7_day_acc` | kWh |  | sum |
| AC Solar kWh 7 Day Avg | `ac_solar_kacok_wh7_day_acc_avg` | kWh |  | sum |
| AC Solar kWh Previous | `ac_solar_kacok_wh_previous` | kWh |  | sum |
| AC Solar kWh Resettable | `ac_solar_kacok_wh_resetable_acc` | kWh |  | sum |
| AC Solar kWh Resettable Avg | `ac_solar_kacok_wh_resetable_acc_avg` | kWh |  | sum |
| AC Solar kWh Year | `ac_solar_kacok_wh_year_acc` | kWh |  | sum |
| AC Solar kWh Year Avg | `ac_solar_kacok_wh_year_acc_avg` | kWh |  | sum |

## ACHistorySubTab2

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Export kWh Total | `ac_exportk_wh_total_acc` | kWh |  | sum |
| AC Input kWh Total | `ac_input_kwh_total_acc` | kWh |  | sum |
| AC Load kWh Total | `ac_load_kwh_total_acc` | kWh |  | sum |
| AC Solar kWh Total | `ac_solar_kacok_wh_total_acc` | kWh |  | sum |

## DCHistorySubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| Battery In kWh 30 Day | `batt_in_kwh30_day_acc` | kWh |  | sum |
| Battery In kWh 30 Day Avg | `batt_in_kwh30_day_acc_avg` | kWh |  | sum |
| Battery In kWh 365 Day | `batt_in_kwh365_day_acc` | kWh |  | sum |
| Battery In kWh 365 Day Avg | `batt_in_kwh365_day_acc_avg` | kWh |  | sum |
| Battery In kWh 7 Day | `batt_in_kwh7_day_acc` | kWh |  | sum |
| Battery In kWh 7 Day Avg | `batt_in_kwh7_day_acc_avg` | kWh |  | sum |
| Battery In kWh Previous | `batt_in_kwh_previous_acc` | kWh |  | sum |
| Battery In kWh Resettable | `batt_in_kwh_resetable_acc` | kWh |  | sum |
| Battery In kWh Resettable Avg | `batt_in_kwh_resetable_acc_avg` | kWh |  | sum |
| Battery In kWh Total | `batt_in_kwh_total_acc` | kWh |  | sum |
| Battery In kWh Year | `batt_in_kwh_year_acc` | kWh |  | sum |
| Battery In kWh Year Avg | `batt_in_kwh_year_acc_avg` | kWh |  | sum |
| Battery Out kWh 30 Day | `batt_out_kwh30_day_acc` | kWh |  | sum |
| Battery Out kWh 30 Day Avg | `batt_out_kwh30_day_acc_avg` | kWh |  | sum |
| Battery Out kWh 365 Day | `batt_out_kwh365_day_acc` | kWh |  | sum |
| Battery Out kWh 365 Day Avg | `batt_out_kwh365_day_acc_avg` | kWh |  | sum |
| Battery Out kWh 7 Day | `batt_out_kwh7_day_acc` | kWh |  | sum |
| Battery Out kWh 7 Day Avg | `batt_out_kwh7_day_acc_avg` | kWh |  | sum |
| Battery Out kWh Previous | `batt_out_kwh_previous_acc` | kWh |  | sum |
| Battery Out kWh Resettable | `batt_out_kwh_resetable_acc` | kWh |  | sum |
| Battery Out kWh Resettable Avg | `batt_out_kwh_resetable_acc_avg` | kWh |  | sum |
| Battery Out kWh Total | `batt_out_kwh_total_acc` | kWh |  | sum |
| Battery Out kWh Year | `batt_out_kwh_year_acc` | kWh |  | sum |
| Battery Out kWh Year Avg | `batt_out_kwh_year_acc_avg` | kWh |  | sum |
| DC Shunt 1 Peak Power Previous | `dc_shunt1_peak_power_previous` | kW |  | — |
| DC Shunt 2 Peak Power Previous | `dc_shunt2_peak_power_previous` | kW |  | — |
| DC kWh In | `d_ck_wh_in` | kWh |  | sum |
| DC kWh Net | `d_ck_wh_net` | kWh |  | sum |
| DC kWh Out | `d_ck_wh_out` | kWh |  | sum |
| Float Hours 30 Day | `float_hrs30_day_acc` | h |  | — |
| Float Hours 30 Day Avg | `float_hrs30_day_acc_avg` | h |  | — |
| Float Hours 365 Day | `float_hrs365_day_acc` | h |  | — |
| Float Hours 365 Day Avg | `float_hrs365_day_acc_avg` | h |  | — |
| Float Hours 7 Day | `float_hrs7_day_acc` | h |  | — |
| Float Hours 7 Day Avg | `float_hrs7_day_acc_avg` | h |  | — |
| Float Hours Previous | `float_hrs_previous_acc` | h |  | — |
| Float Hours Year | `float_hrs_year_acc` | h |  | — |
| Float Hours Year Avg | `float_hrs_year_acc_avg` | h |  | — |
| Inverter DC kWh 30 Day | `inverter_d_ck_wh30_day_acc` | kWh |  | sum |
| Inverter DC kWh 30 Day Avg | `inverter_d_ck_wh30_day_acc_avg` | kWh |  | sum |
| Inverter DC kWh 365 Day | `inverter_d_ck_wh365_day_acc` | kWh |  | sum |
| Inverter DC kWh 365 Day Avg | `inverter_d_ck_wh365_day_acc_avg` | kWh |  | sum |
| Inverter DC kWh 7 Day | `inverter_d_ck_wh7_day_acc` | kWh |  | sum |
| Inverter DC kWh 7 Day Avg | `inverter_d_ck_wh7_day_acc_avg` | kWh |  | sum |
| Inverter DC kWh Previous | `inverter_d_ck_wh_previous_acc` | kWh |  | sum |
| Inverter DC kWh Resettable | `inverter_d_ck_wh_resetable_acc` | kWh |  | sum |
| Inverter DC kWh Resettable Avg | `inverter_d_ck_wh_resetable_acc_avg` | kWh |  | sum |
| Inverter DC kWh Total | `inverter_d_ck_wh_total_acc` | kWh |  | sum |
| Inverter DC kWh Year | `inverter_d_ck_wh_year_acc` | kWh |  | sum |
| Inverter DC kWh Year Avg | `inverter_d_ck_wh_year_acc_avg` | kWh |  | sum |
| Shunt 1 kWh 30 Day | `shunt1k_wh30_day_acc` | kWh |  | sum |
| Shunt 1 kWh 30 Day Avg | `shunt1k_wh30_day_acc_avg` | kWh |  | sum |
| Shunt 1 kWh 365 Day | `shunt1k_wh365_day_acc` | kWh |  | sum |
| Shunt 1 kWh 365 Day Avg | `shunt1k_wh365_day_acc_avg` | kWh |  | sum |
| Shunt 1 kWh 7 Day | `shunt1k_wh7_day_acc` | kWh |  | sum |
| Shunt 1 kWh 7 Day Avg | `shunt1k_wh7_day_acc_avg` | kWh |  | sum |
| Shunt 1 kWh Previous | `shunt1k_wh_previous_acc` | kWh |  | sum |
| Shunt 1 kWh Resettable | `shunt1k_wh_resetable_acc` | kWh |  | sum |
| Shunt 1 kWh Resettable Avg | `shunt1k_wh_resetable_acc_avg` | kWh |  | sum |
| Shunt 1 kWh Total | `shunt1k_wh_total_acc` | kWh |  | sum |
| Shunt 1 kWh Year | `shunt1k_wh_year_acc` | kWh |  | sum |
| Shunt 1 kWh Year Avg | `shunt1k_wh_year_acc_avg` | kWh |  | sum |
| Shunt 2 kWh 30 Day | `shunt2k_wh30_day_acc` | kWh |  | sum |
| Shunt 2 kWh 30 Day Avg | `shunt2k_wh30_day_acc_avg` | kWh |  | sum |
| Shunt 2 kWh 365 Day | `shunt2k_wh365_day_acc` | kWh |  | sum |
| Shunt 2 kWh 365 Day Avg | `shunt2k_wh365_day_acc_avg` | kWh |  | sum |
| Shunt 2 kWh 7 Day | `shunt2k_wh7_day_acc` | kWh |  | sum |
| Shunt 2 kWh 7 Day Avg | `shunt2k_wh7_day_acc_avg` | kWh |  | sum |
| Shunt 2 kWh Previous | `shunt2k_wh_previous_acc` | kWh |  | sum |
| Shunt 2 kWh Resettable | `shunt2k_wh_resetable_acc` | kWh |  | sum |
| Shunt 2 kWh Resettable Avg | `shunt2k_wh_resetable_acc_avg` | kWh |  | sum |
| Shunt 2 kWh Total | `shunt2k_wh_total_acc` | kWh |  | sum |
| Shunt 2 kWh Year | `shunt2k_wh_year_acc` | kWh |  | sum |
| Shunt 2 kWh Year Avg | `shunt2k_wh_year_acc_avg` | kWh |  | sum |
| Time Float Achieved Previous | `time_float_achieved_previous` |  |  | — |

## DataMultiPhase1

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| Multi AC Source Status L1 | `multi_ac_source_status_l1` |  |  | — |
| Multi Battery Charger Stage | `multi_battery_charger_stage` |  |  | — |
| Multi Battery SoC | `multi_battery_so_c` | % |  | avg |
| Multi Phase AC Source Volts L1 | `multi_phase_ac_source_volts_l1` | V |  | — |
| Multi Phase Load AC Volts L1 | `multi_phase_load_ac_volts_l1` | V |  | — |

## NowSubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Solar Power | `now_total_ac_power_kaco` | kW | ✓ | sum |
| AC Source Frequency | `input_ac_hz` | Hz | ✓ | avg |
| AC Source Status | `ac_source_status` |  | ✓ | — |
| AC Source Voltage | `ac_generator_rms_volts` | V | ✓ | avg |
| Battery Current | `dc_battery_current` | A | ✓ | sum |
| Battery SoC | `batt_soc_percent` | % | ✓ | avg |
| Battery Voltage | `battery_volts` | V | ✓ | avg |
| Charge Status | `charge_status_now` |  | ✓ | — |
| Generator Running Reason | `generator_running_reason` |  | ✓ | — |
| Generator Started By | `generator_start_reason` |  | ✓ | — |
| Generator Status | `generator_status_from_led` |  | ✓ | — |
| Inverter Mode | `ac_out_status` |  | ✓ | — |
| Inverter Power | `ac_inverter_power` | kW | ✓ | sum |
| Load Frequency | `inv_freq` | Hz | ✓ | avg |
| Load Power | `load_ac_power` | kW | ✓ | sum |
| Shunt 1 Power | `shunt1_power` | kW | ✓ | sum |
| 15 Min Battery Load | `15_min_batt_load` | kW |  | sum |
| 5 Min Battery Load | `5_min_batt_load` | kW |  | sum |
| AC Generator Power 5min Avg | `ac_generator_power5min_avg` | kW |  | sum |
| AC Generator RMS Amps | `ac_generator_rms_amps` | A |  | sum |
| AC Inverter RMS Amps | `ac_inverter_rms_amps` | A |  | sum |
| AC Solar Power 1 | `now_ac_power_kaco1` | kW |  | sum |
| AC Solar Power 2 | `now_ac_power_kaco2` | kW |  | sum |
| AC Solar Power 3 | `now_ac_power_kaco3` | kW |  | sum |
| AC Solar Power 4 | `now_ac_power_kaco4` | kW |  | sum |
| AC Solar Power 5 | `now_ac_power_kaco5` | kW |  | sum |
| DC Current | `dc_current` | A |  | sum |
| Max Available Input kW | `max_available_inputk_w` | kW |  | sum |
| Shunt 1 Amps | `shunt1_amps` | A |  | sum |
| Shunt 2 Amps | `shunt2_amps` | A |  | sum |
| Shunt 2 Power | `shunt2_power` | kW |  | sum |
| System Regulation Charge Power Limit | `sys_reg_charge_power_limit` | kW |  | — |
| System Regulation Export Power Limit | `sys_reg_export_power_limit` | kW |  | — |

## Now_Today_Tech_KacoModelsCapacityAndOEM

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| Country Code | `country_code` |  |  | — |
| Disable Sp Link Login Password | `disable_splink_login_password` |  |  | — |
| Power Control Mode Enabled | `power_control_mode_enabled` |  |  | — |

## RAndDOnlyDataSubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| Build Time | `build_time` |  |  | — |
| Version Number In RD | `version_number_in_rd` |  |  | — |

## ServiceSettings

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Solar Differential Gain | `ac_solar_differential_gain` |  |  | — |
| AC Solar Differential Gain Connected To Source | `ac_solar_differential_gain_connected_to_source` |  |  | — |
| AC Solar Feed Forward Gain | `ac_solar_feed_forward_gain` |  |  | — |
| AC Solar Feed Forward Gain Connected To Source | `ac_solar_feed_forward_gain_connected_to_source` |  |  | — |
| AC Solar Filter Falling Standalone | `ac_solar_filter_falling_standalone` |  |  | — |
| AC Solar Filter Falling Sync | `ac_solar_filter_falling_sync` |  |  | — |
| AC Solar Filter Rising Standalone | `ac_solar_filter_rising_standalone` |  |  | — |
| AC Solar Filter Rising Sync | `ac_solar_filter_rising_sync` |  |  | — |
| AC Solar Integral Gain | `ac_solar_integral_gain` |  |  | — |
| AC Solar Integral Gain Connected To Source | `ac_solar_integral_gain_connected_to_source` |  |  | — |
| AC Solar Proportional Gain 0 | `ac_solar_proportional_gain0` |  |  | — |
| AC Solar Proportional Gain 1 | `ac_solar_proportional_gain1` |  |  | — |
| AC Solar Proportional Gain 2 | `ac_solar_proportional_gain2` |  |  | — |
| AC Solar Proportional Gain 3 | `ac_solar_proportional_gain3` |  |  | — |
| AC Solar Proportional Gain 4 | `ac_solar_proportional_gain4` |  |  | — |
| AC Solar Proportional Gain Connected To Source | `ac_solar_proportional_gain_connected_to_source` |  |  | — |
| AC Solar Proportional Voltage 0 | `ac_solar_proportional_voltage0` |  |  | — |
| AC Solar Proportional Voltage 1 | `ac_solar_proportional_voltage1` |  |  | — |
| AC Solar Proportional Voltage 2 | `ac_solar_proportional_voltage2` |  |  | — |
| AC Solar Proportional Voltage 3 | `ac_solar_proportional_voltage3` |  |  | — |
| AC Solar Proportional Voltage 4 | `ac_solar_proportional_voltage4` |  |  | — |
| Emulated Inductance Percent | `emulated_inductance_percent` |  |  | — |

## TechnicalDataSubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Source Power | `ac_source_power` | kW | ✓ | sum |
| AC Source Power In | `ac_source_power_in` | kW | ✓ | sum |
| AC Source Power Out | `ac_source_power_out` | kW | ✓ | sum |
| AC Source Reactive Power | `ac_source_reactive_power` | kvar | ✓ | sum |
| Battery Power | `dc_battery_power` | kW | ✓ | sum |
| Battery Power In | `dc_battery_power_in` | kW | ✓ | sum |
| Battery Power Out | `dc_battery_power_out` | kW | ✓ | sum |
| Battery Temperature | `battery_temperature` | °C | ✓ | — |
| Days Since Equalise | `days_since_equalise` |  | ✓ | — |
| Days To Equalise | `days_to_equalise` |  | ✓ | — |
| Digital Input 1 | `digital_in_status1` |  | ✓ | — |
| Digital Input 2 | `digital_in_status2` |  | ✓ | — |
| Digital Input 3 | `digital_in_status3` |  | ✓ | — |
| Digital Input 4 | `digital_in_status4` |  | ✓ | — |
| Fan Speed | `fan_speed` | % | ✓ | — |
| Generator Power In | `generator_power_in` | kW | ✓ | sum |
| Grid Power In | `grid_power_in` | kW | ✓ | sum |
| Grid Power Out | `grid_power_out` | kW | ✓ | sum |
| Heatsink Temperature | `heatsink_temperature` | °C | ✓ | — |
| Inlet Air Temperature | `inlet_air_temperature` | °C | ✓ | — |
| Inverter Reactive Power | `inverter_reactive_power` | kvar | ✓ | sum |
| Load Voltage | `ac_inverter_rms_volts_tech` | V | ✓ | avg |
| Total Run Time | `inverter_run_hrs_total_acc` | h | ✓ | — |
| Transformer Temperature | `transformer_temperature` | °C | ✓ | — |
| Battery Cable Loss | `battery_cable_loss` | kW |  | sum |
| Battery Mid Point | `battery_mid_point` | V |  | — |
| Batteryless | `factory_batteryless` |  |  | — |
| Capacitor Life Consumed Filter | `capacitor_life_consumed_filter` | % |  | — |
| Capacitor Life Consumed PM 1 | `capacitor_life_consumed_pm1` | % |  | — |
| Capacitor Life Consumed PM 2 | `capacitor_life_consumed_pm2` | % |  | — |
| Charge Index | `charge_index` |  |  | — |
| Comms Card Firmware Update | `comms_card_firmware_update` |  |  | — |
| Comms Card Serial | `comms_card_serial` |  |  | — |
| Comms Card Software Version | `comms_card_software` |  |  | — |
| Comms Card Stored Firmware | `comms_card_stored_firmware` |  |  | — |
| Control Board Temperature | `control_board_temperature` | °C |  | — |
| Control PCA Mod Status | `control_pca_mod_status` |  |  | — |
| Control PCA Rev Number | `control_pca_rev_number` |  |  | — |
| Control PCA Serial Number | `control_pca_serial_number` |  |  | — |
| DC Volts | `dc_volts` | V |  | avg |
| Days Since Recharge | `days_since_recharge` |  |  | — |
| Days To Recharge | `days_to_recharge` |  |  | — |
| Digital Out Status 1 | `digital_out_status1` |  |  | — |
| Digital Out Status 2 | `digital_out_status2` |  |  | — |
| Digital Out Status 3 | `digital_out_status3` |  |  | — |
| Digital Out Status 4 | `digital_out_status4` |  |  | — |
| Digital Out Status 5 | `digital_out_status5` |  |  | — |
| Digital Out Status 6 | `digital_out_status6` |  |  | — |
| Digital Out Status 7 | `digital_out_status7` |  |  | — |
| Factory Export Limit | `factory_export_limit` |  |  | — |
| Fan Life | `fan_life` | % |  | — |
| General Purpose 1 | `general_purpose1` | V |  | — |
| General Purpose 2 | `general_purpose2` | V |  | — |
| Grid Firmware | `grid_firmware` |  |  | — |
| Inverter Apparent Power | `inverter_apparent_power` | kVA |  | sum |
| Kaco Mode | `kaco_mode` |  |  | — |
| Load Volts High Frequency Ripple | `load_volts_high_frequency_ripple` | V |  | — |
| Number Of Kacos | `number_of_kacos` |  |  | — |
| PM 1 Mod Status | `pm1_mod_status` |  |  | — |
| PM 1 Rev Number | `pm1_rev_number` |  |  | — |
| PM 1 Serial Number | `pm1_serial_number` |  |  | — |
| PM 2 Mod Status | `pm2_mod_status` |  |  | — |
| PM 2 Rev Number | `pm2_rev_number` |  |  | — |
| PM 2 Serial Number | `pm2_serial_number` |  |  | — |
| String Inverter Support | `string_inverter_support` |  |  | — |
| Unit Mod Status | `unit_mod_status` |  |  | — |
| Unit Model Number | `unit_model_number` |  |  | — |
| Unit Model Ratings | `unit_model_ratings` |  |  | — |
| Unit Rev Number | `unit_rev_number` |  |  | — |
| Unit Serial Number | `unit_serial_number` |  |  | — |

## TodaySubTab

| Field | Key | Unit | Default | System |
|---|---|---|:---:|:---:|
| AC Input Energy Today | `ac_inputk_wh_acc` | kWh | ✓ | sum |
| AC Solar Energy Today | `today_total_ac_energy_kaco` | kWh | ✓ | sum |
| Battery Charge Today | `batt_ink_wh_acc` | kWh | ✓ | sum |
| Battery Discharge Today | `batt_outk_wh_acc` | kWh | ✓ | sum |
| DC Energy In Today | `d_ck_wh_in_today` | kWh | ✓ | sum |
| DC Energy Out Today | `d_ck_wh_out_today` | kWh | ✓ | sum |
| Export Energy Today | `ac_export_accumulated_today` | kWh | ✓ | sum |
| Load Energy Today | `ac_loadk_wh_acc` | kWh | ✓ | sum |
| AC Input Hours | `ac_input_hrs_acc` | h |  | — |
| Battery Net kWh | `batt_netk_wh` | kWh |  | sum |
| DC kWh Net Today | `d_ck_wh_net_today` | kWh |  | sum |
| Float Hours | `float_hrs_acc` | h |  | — |
| Inverter DC kWh | `inverter_d_ck_wh_acc` | kWh |  | sum |
| Inverter Run Hours | `inverter_run_hrs_acc` | h |  | — |
| Shunt 1 Peak Power Today | `shunt1_peak_power_today` | kW |  | — |
| Shunt 1 kWh | `shunt1k_wh_acc` | kWh |  | sum |
| Shunt 2 Peak Power Today | `shunt2_peak_power_today` | kW |  | — |
| Shunt 2 kWh | `shunt2k_wh_acc` | kWh |  | sum |
| Time Float Achieved | `time_float_achieved` |  |  | — |

