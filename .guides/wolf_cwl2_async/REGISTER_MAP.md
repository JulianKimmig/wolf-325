# Built-in CWL-2-325 register catalogue

This table is generated from `wolf_cwl2.py`. Addresses are the documented UWA2 PDU addresses. The default configuration sends them unchanged (`address_offset: 0`). Model-specific validation ranges follow the WOLF CWL-2-325 manual where it is more restrictive than the generic UWA2 register document.

| Key | Address | Table | Access | Unit | Values/range | Flags | Description |
|---|---:|---|---|---|---|---|---|
| `flow_preset_holiday_m3h` | 6000 | holding | R/W | m³/h | 50..325; extra 0; step 5 | restored | Airflow preset 0 / holiday |
| `flow_preset_low_m3h` | 6001 | holding | R/W | m³/h | 50..325; step 5 | restored | Airflow preset 1 / low |
| `flow_preset_normal_m3h` | 6002 | holding | R/W | m³/h | 50..325; step 5 | restored | Airflow preset 2 / normal |
| `flow_preset_high_m3h` | 6003 | holding | R/W | m³/h | 50..325; step 5 | restored | Airflow preset 3 / high |
| `pwm_supply_holiday_pct` | 6010 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Supply PWM preset 0 |
| `pwm_exhaust_holiday_pct` | 6011 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Exhaust PWM preset 0 |
| `pwm_supply_low_pct` | 6012 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Supply PWM preset 1 |
| `pwm_exhaust_low_pct` | 6013 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Exhaust PWM preset 1 |
| `pwm_supply_normal_pct` | 6014 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Supply PWM preset 2 |
| `pwm_exhaust_normal_pct` | 6015 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Exhaust PWM preset 2 |
| `pwm_supply_high_pct` | 6016 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Supply PWM preset 3 |
| `pwm_exhaust_high_pct` | 6017 | holding | R/W | % | 15..100; extra 0; step 1 | restored | Exhaust PWM preset 3 |
| `flow_control_method` | 6030 | holding | R/W |  | constant_pwm, constant_flow, constant_mass_flow | restored | Fan control method |
| `switch_default_position` | 6031 | holding | R/W |  | 0..1 | restored | Default physical switch position |
| `use_display_as_switch` | 6032 | holding | R/W |  |  | restored | Use display as level switch |
| `imbalance_allowed` | 6033 | holding | R/W |  |  | restored | Allow supply/exhaust imbalance |
| `imbalance_pct` | 6034 | holding | R/W | % | 0..20; step 1 | restored | Supply airflow increase relative to exhaust |
| `supply_imbalance_offset_pct` | 6035 | holding | R/W | % | -15..15; step 1 | restored | Supply imbalance correction |
| `exhaust_imbalance_offset_pct` | 6036 | holding | R/W | % | -15..15; step 1 | restored | Exhaust imbalance correction |
| `bypass_mode` | 6100 | holding | R/W |  | automatic, closed, open | restored | Bypass mode |
| `bypass_indoor_threshold_c` | 6101 | holding | R/W | °C | 15.0..35.0; step 0.5 | restored | Indoor temperature threshold for bypass |
| `bypass_outdoor_threshold_c` | 6102 | holding | R/W | °C | 7.0..15.0; step 0.5 | restored | Outdoor temperature threshold for bypass |
| `bypass_hysteresis_c` | 6103 | holding | R/W | K | 0.0..5.0; step 0.5 | restored | Bypass temperature hysteresis |
| `bypass_boost` | 6104 | holding | R/W |  |  | restored | Enable bypass boost |
| `bypass_boost_level` | 6105 | holding | R/W |  | holiday, low, normal, high | restored | Fan level used for bypass boost |
| `frost_control_temperature_c` | 6110 | holding | R/W | °C | -1.5..1.5; step 0.5 | restored | Frost-control temperature |
| `frost_min_supply_temperature_c` | 6111 | holding | R/W | °C | 7.0..17.0; step 0.5 | restored | Minimum inlet temperature during frost control |
| `filter_warning_days` | 6120 | holding | R/W | days | 1..365; step 1 | restored | Days before filter warning |
| `external_heater_mode` | 6130 | holding | R/W |  | unavailable, preheater, postheater | restored | External heater type |
| `postheater_setpoint_c` | 6131 | holding | R/W | °C | 15.0..30.0; step 0.5 | restored | Postheater setpoint |
| `humidity_control` | 6140 | holding | R/W |  |  | restored | Humidity control |
| `humidity_sensitivity` | 6141 | holding | R/W |  | -2..2; step 1 | restored | Humidity-control sensitivity |
| `co2_control` | 6150 | holding | R/W |  |  | restored | CO₂ control |
| `co2_sensor_1_low_ppm` | 6151 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 1 low threshold |
| `co2_sensor_1_high_ppm` | 6152 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 1 high threshold |
| `co2_sensor_2_low_ppm` | 6153 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 2 low threshold |
| `co2_sensor_2_high_ppm` | 6154 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 2 high threshold |
| `co2_sensor_3_low_ppm` | 6155 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 3 low threshold |
| `co2_sensor_3_high_ppm` | 6156 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 3 high threshold |
| `co2_sensor_4_low_ppm` | 6157 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 4 low threshold |
| `co2_sensor_4_high_ppm` | 6158 | holding | R/W | ppm | 400..2000; step 1 | restored | CO₂ sensor 4 high threshold |
| `signal_output_mode` | 6170 | holding | R/W |  | off, filter_warning, error, filter_warning_and_error | restored | 24 V signal output function |
| `central_heating_exhaust_connected` | 6171 | holding | R/W |  |  | restored | Central-heating exhaust connected |
| `digital_input_1_contact_type` | 6200 | holding | R/W |  | normally_open, normally_closed | restored | Digital input 1 contact type |
| `digital_input_1_mode` | 6201 | holding | R/W |  | off, on, on_if_bypass_conditions, bypass_control, external_valve_control | restored | Digital input 1 function |
| `digital_input_1_supply_fan_function` | 6202 | holding | R/W |  | fan_off, absolute_minimum_flow, preset_1, preset_2, preset_3, physical_switch, absolute_maximum_flow, unchanged | restored | Supply fan behavior for digital input 1 |
| `digital_input_1_exhaust_fan_function` | 6203 | holding | R/W |  | fan_off, absolute_minimum_flow, preset_1, preset_2, preset_3, physical_switch, absolute_maximum_flow, unchanged | restored | Exhaust fan behavior for digital input 1 |
| `digital_input_2_contact_type` | 6210 | holding | R/W |  | normally_open, normally_closed | restored | Digital input 2 contact type |
| `digital_input_2_mode` | 6211 | holding | R/W |  | off, on, on_if_bypass_conditions, bypass_control, external_valve_control | restored | Digital input 2 function |
| `digital_input_2_supply_fan_function` | 6212 | holding | R/W |  | fan_off, absolute_minimum_flow, preset_1, preset_2, preset_3, physical_switch, absolute_maximum_flow, unchanged | restored | Supply fan behavior for digital input 2 |
| `digital_input_2_exhaust_fan_function` | 6213 | holding | R/W |  | fan_off, absolute_minimum_flow, preset_1, preset_2, preset_3, physical_switch, absolute_maximum_flow, unchanged | restored | Exhaust fan behavior for digital input 2 |
| `analog_input_1_enabled` | 6220 | holding | R/W |  |  | restored | Enable analogue input 1 |
| `analog_input_1_min_v` | 6221 | holding | R/W | V | 0.0..10.0; step 0.5 | restored | Analogue input 1 minimum voltage |
| `analog_input_1_max_v` | 6222 | holding | R/W | V | 0.0..10.0; step 0.5 | restored | Analogue input 1 maximum voltage |
| `analog_input_2_enabled` | 6230 | holding | R/W |  |  | restored | Enable analogue input 2 |
| `analog_input_2_min_v` | 6231 | holding | R/W | V | 0.0..10.0; step 0.5 | restored | Analogue input 2 minimum voltage |
| `analog_input_2_max_v` | 6232 | holding | R/W | V | 0.0..10.0; step 0.5 | restored | Analogue input 2 maximum voltage |
| `geo_heat_exchanger_enabled` | 6240 | holding | R/W |  |  | restored, optional | Enable ground heat exchanger |
| `geo_heat_exchanger_min_temperature_c` | 6241 | holding | R/W | °C | 0.0..10.0; step 0.1 | restored, optional | Ground heat exchanger minimum temperature |
| `geo_heat_exchanger_max_temperature_c` | 6242 | holding | R/W | °C | 15.0..40.0; step 0.1 | restored, optional | Ground heat exchanger maximum temperature |
| `geo_heat_exchanger_default_valve` | 6243 | holding | R/W |  | closed, open | restored, optional | Ground heat exchanger valve position at 0 V |
| `geo_heat_exchanger_output` | 6244 | holding | R/W |  | analog_output_1, analog_output_2, relay_output_1, relay_output_2 | restored, optional | Ground heat exchanger output assignment |
| `language` | 6900 | holding | R/W |  | english, dutch | restored | Display language |
| `date_format` | 6901 | holding | R/W |  | dd_mm_yyyy, mm_dd_yyyy | restored | Display date format |
| `time_notation` | 6902 | holding | R/W |  | 12_hour, 24_hour | restored | Display time notation |
| `device_date_month_day` | 6903 | holding | R/W |  |  |  | Device month/day |
| `device_date_year` | 6904 | holding | R/W |  | 2000..2099 |  | Device year |
| `device_time` | 6905 | holding | R/W |  |  |  | Device hour/minute |
| `device_weekday_second` | 6906 | holding | R/W |  |  |  | Device weekday/second |
| `modbus_interface_type` | 7990 | holding | R/W |  | internal, external_modbus, external_customer | dangerous | Modbus interface routing |
| `modbus_slave_address` | 7991 | holding | R/W |  | 1..247 | dangerous | Appliance Modbus slave address |
| `modbus_speed` | 7992 | holding | R/W |  | 1200, 2400, 4800, 9600, 19200, 38400, 56000, 115200 | dangerous | Appliance serial baud rate |
| `remote_control_mode` | 8000 | holding | R/W |  | off, level, airflow | restored | External Modbus control mode |
| `remote_ventilation_level` | 8001 | holding | R/W |  | holiday, low, normal, high | restored | Requested external ventilation level |
| `remote_airflow_m3h` | 8002 | holding | R/W | m³/h | 50..325; extra 0; step 1 | restored | Requested external airflow |
| `remote_standby` | 8003 | holding | R/W |  |  | restored | External standby state/command |
| `filter_reset_status` | 8010 | holding | R/W |  | no_action, executed, failed | one-shot | Filter-reset action/status |
| `appliance_reset_status` | 8011 | holding | R/W |  | no_action, executed, failed | one-shot, dangerous | Appliance-reset action/status |
| `base_software_version` | 4000 | input | R |  |  |  | UWA2-B software version |
| `base_hardware_version` | 4003 | input | R |  |  |  | UWA2-B hardware version |
| `appliance_type` | 4004 | input | R |  |  |  | Internal appliance type |
| `base_dipswitch_value` | 4005 | input | R |  |  |  | UWA2-B DIP-switch value |
| `serial_number` | 4010 | input | R |  |  |  | 12-digit appliance serial number |
| `active_function` | 4020 | input | R |  | standby, bootloader, non_blocking_error, blocking_error, manual, holiday, night_ventilation, party, bypass_boost, normal_boost, auto_co2, auto_ebus, auto_modbus, auto_portal, auto_local_network |  | Current appliance function |
| `fan_control_type` | 4021 | input | R |  | initializing, constant_flow, constant_pwm, off, error, mass_balance, standby |  | Active fan-control method |
| `ventilation_mode` | 4022 | input | R |  | holiday, low, normal, high, auto |  | Current ventilation level |
| `supply_pressure_pa` | 4023 | input | R | Pa |  |  | Current supply pressure |
| `exhaust_pressure_pa` | 4024 | input | R | Pa |  |  | Current exhaust pressure |
| `supply_fan_status` | 4030 | input | R |  | no_communication, idle, running, blocked, fan_error |  | Supply fan status |
| `supply_airflow_setpoint_m3h` | 4031 | input | R | m³/h |  |  | Supply airflow setpoint |
| `supply_airflow_actual_m3h` | 4032 | input | R | m³/h |  |  | Actual supply airflow |
| `supply_mass_flow_actual_kgh` | 4033 | input | R | kg/h |  |  | Actual supply mass flow |
| `supply_fan_speed_rpm` | 4034 | input | R | rpm |  |  | Supply fan speed |
| `supply_anemometer_speed_rpm` | 4035 | input | R | rpm |  |  | Supply anemometer speed |
| `supply_temperature_c` | 4036 | input | R | °C |  |  | Supply air temperature |
| `supply_relative_humidity_pct` | 4037 | input | R | % |  | optional | Supply relative humidity |
| `exhaust_fan_status` | 4040 | input | R |  | no_communication, idle, running, blocked, fan_error |  | Exhaust fan status |
| `exhaust_airflow_setpoint_m3h` | 4041 | input | R | m³/h |  |  | Exhaust airflow setpoint |
| `exhaust_airflow_actual_m3h` | 4042 | input | R | m³/h |  |  | Actual exhaust airflow |
| `exhaust_mass_flow_actual_kgh` | 4043 | input | R | kg/h |  |  | Actual exhaust mass flow |
| `exhaust_fan_speed_rpm` | 4044 | input | R | rpm |  |  | Exhaust fan speed |
| `exhaust_anemometer_speed_rpm` | 4045 | input | R | rpm |  |  | Exhaust anemometer speed |
| `exhaust_temperature_c` | 4046 | input | R | °C |  |  | Exhaust air temperature |
| `exhaust_relative_humidity_pct` | 4047 | input | R | % |  | optional | Exhaust relative humidity |
| `bypass_status` | 4050 | input | R |  | initializing, opening, closing, open, closed |  | Bypass state |
| `bypass_step_position` | 4051 | input | R |  |  |  | Bypass motor position relative to zero |
| `preheater_status` | 4060 | input | R |  | initializing, inactive, active, test_mode |  | Preheater state |
| `preheater_capacity_pct` | 4061 | input | R | % |  |  | Preheater output |
| `frost_status` | 4070 | input | R |  | not_initialized, power_up_delay, no_frost, no_frost_delay, frost_control_start_delay, wait_for_icing, ice_detected_delay, heating, wait_for_free_heater, fan_control_start_delay, fan_control_wait_delay, fan_control, fan_off_delay, fan_off, fan_restarting, error, test_mode |  | Frost-protection state |
| `frost_heater_power_pct` | 4071 | input | R | % |  |  | Frost heater output |
| `frost_fan_reduction_pct` | 4072 | input | R | % |  |  | Fan reduction by frost control |
| `physical_switch_position` | 4080 | input | R |  | holiday, low, normal, high, invalid |  | Physical four-position switch |
| `ntc1_temperature_c` | 4081 | input | R | °C |  | optional | NTC1 temperature |
| `ntc2_temperature_c` | 4082 | input | R | °C |  | optional | NTC2 temperature |
| `rht_humidity_pct` | 4083 | input | R | % |  | optional | RHT sensor humidity |
| `signal_output_state` | 4090 | input | R |  | off, on |  | 24 V signal output state |
| `filter_status` | 4100 | input | R |  | clean, dirty |  | Filter warning state |
| `ebus_power_status` | 4101 | input | R |  | power_up, initialize_power, power_off, power_on, wait_for_power_off, slave_power_off |  | eBUS power state |
| `appliance_time` | 4110 | input | R |  |  |  | Appliance clock |
| `appliance_date_raw` | 4111 | input | R |  |  |  | Appliance date words (manual encoding is ambiguous) |
| `operating_time_hours` | 4113 | input | R | h |  |  | Total operating time |
| `filter_runtime_hours` | 4115 | input | R | h |  |  | Operating hours since filter reset |
| `filter_air_volume_counter` | 4116 | input | R | m³ |  |  | Air-volume counter since filter reset |
| `total_air_volume_counter` | 4118 | input | R | m³ |  |  | Total air-volume counter |
| `geo_heat_exchanger_status` | 4150 | input | R |  | open_low, closed, open_high | optional | Ground heat exchanger state |
| `co2_sensor_1_status` | 4200 | input | R |  | error, not_initialized, idle, warming_up, running, calibrating, self_test | optional | CO₂ sensor 1 state |
| `co2_sensor_1_ppm` | 4201 | input | R | ppm |  | optional | CO₂ sensor 1 value |
| `co2_sensor_2_status` | 4202 | input | R |  | error, not_initialized, idle, warming_up, running, calibrating, self_test | optional | CO₂ sensor 2 state |
| `co2_sensor_2_ppm` | 4203 | input | R | ppm |  | optional | CO₂ sensor 2 value |
| `co2_sensor_3_status` | 4204 | input | R |  | error, not_initialized, idle, warming_up, running, calibrating, self_test | optional | CO₂ sensor 3 state |
| `co2_sensor_3_ppm` | 4205 | input | R | ppm |  | optional | CO₂ sensor 3 value |
| `co2_sensor_4_status` | 4206 | input | R |  | error, not_initialized, idle, warming_up, running, calibrating, self_test | optional | CO₂ sensor 4 state |
| `co2_sensor_4_ppm` | 4207 | input | R | ppm |  | optional | CO₂ sensor 4 value |
| `ui_software_version` | 4400 | input | R |  |  | optional | UI module software version |
| `ui_hardware_version` | 4403 | input | R |  |  | optional | UI module hardware version |
| `ui_device_type` | 4404 | input | R |  |  | optional | UI module device type |
| `ui_dipswitch_value` | 4405 | input | R |  |  | optional | UI module DIP-switch value |
| `ui_language_data_version` | 4410 | input | R |  |  | optional | UI language data version |
| `ui_secondary_software_version` | 4413 | input | R |  |  | optional | UI secondary software version |
| `local_ui_switch` | 4420 | input | R |  |  | optional | Level selected on local UI |
| `local_ui_button` | 4421 | input | R |  |  | optional | Local UI button value |
| `extension_software_version` | 4500 | input | R |  |  | optional | UWA2-E software version |
| `extension_hardware_version` | 4503 | input | R |  |  | optional | UWA2-E hardware version |
| `extension_device_type` | 4504 | input | R |  |  | optional | UWA2-E device type |
| `extension_dipswitch_value` | 4505 | input | R |  |  | optional | UWA2-E DIP-switch value |
| `extension_ntc_temperature_c` | 4520 | input | R | °C |  | optional | UWA2-E NTC temperature |
| `extension_contact_1` | 4521 | input | R |  | open, closed | optional | UWA2-E contact 1 |
| `extension_contact_2` | 4522 | input | R |  | open, closed | optional | UWA2-E contact 2 |
| `extension_analog_input_1_v` | 4523 | input | R | V |  | optional | UWA2-E analogue input 1 |
| `extension_analog_input_2_v` | 4524 | input | R | V |  | optional | UWA2-E analogue input 2 |
| `extension_relay_output_1` | 4541 | input | R |  | off, on | optional | UWA2-E relay output 1 |
| `extension_relay_output_2` | 4542 | input | R |  | off, on | optional | UWA2-E relay output 2 |
| `extension_analog_output_1_v` | 4543 | input | R | V |  | optional | UWA2-E analogue output 1 |
| `extension_analog_output_2_v` | 4544 | input | R | V |  | optional | UWA2-E analogue output 2 |
