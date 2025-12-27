# HA-Goodtop

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

> **WARNING: AI Slop Coded**
>
> This integration was AI slop coded. While it has been tested, **do not use this in mission-critical situations**. Use at your own risk. The code may contain bugs, security issues, or unexpected behavior.

Control and monitor Goodtop network switches from Home Assistant.

## Features

- **PoE Control** - Enable/disable PoE per port
- **Port Control** - Enable/disable ports
- **Power Monitoring** - Total PoE power consumption (W)
- **Link Status** - Per-port link up/down with speed
- **Traffic Statistics** - TX/RX packet counters (diagnostic)

## Tested Models

- ZX-AFGW-SWTG218ANS-100

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/hairyfred/HA-Goodtop` with category **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Copy `custom_components/goodtop` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Goodtop Switch**
4. Enter your switch IP, username, and password

## Entities

| Type | Entity | Description |
|------|--------|-------------|
| Switch | Port X PoE | Toggle PoE power per port |
| Switch | Port X | Enable/disable port |
| Sensor | PoE Power | Total PoE consumption (W) |
| Binary Sensor | Port X Link | Link status (up/down) |
| Sensor | Port X TX/RX Good/Bad | Packet counters (diagnostic) |
