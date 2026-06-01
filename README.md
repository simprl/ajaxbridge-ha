# Ajaxbridge Home Assistant Integration

Custom Home Assistant integration for connecting Home Assistant to an
Ajaxbridge cloud bridge server.

Ajaxbridge receives Ajax Enterprise API / AWS SQS events on a backend server and
streams normalized entity updates to Home Assistant over HTTPS/WebSocket.

## Installation Through HACS

This repository is intended to be used as a HACS custom repository.

1. Open Home Assistant.
2. Go to `HACS -> Integrations`.
3. Open the menu and choose `Custom repositories`.
4. Add this repository URL with category `Integration`.
5. Download `Ajaxbridge`.
6. Restart Home Assistant.
7. Add the `Ajaxbridge` integration from `Settings -> Devices & services`.

## Configuration

The config flow asks for:

- bridge URL, for example `https://ajaxbridge.ilazyhome.com`;
- installation ID, for example `site-prod`;
- installation API token.

The installation token is not the backend admin token. Do not use the admin
token in Home Assistant.

## Entities

The integration creates entities from the bridge state model:

- group-level `alarm_control_panel` entities;
- hub-level `binary_sensor` for active alarm;
- hub-level `sensor` entities for security summary, alarm source, last event,
  delivery lag, and diagnostics.

The alarm control panels are read-only in the current version.

## Development

The source of truth for development currently lives in the Ajaxbridge monorepo:

```text
ajaxbridge/integrations/home_assistant/custom_components/ajaxbridge
```

This repository is the HACS distribution copy.
