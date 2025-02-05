"""Support for Home Assistant iOS app sensors."""
from __future__ import annotations

from homeassistant.components import ios
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.icon import icon_for_battery_level

from .const import DOMAIN

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="level",
        name="Battery Level",
        unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="state",
        name="Battery State",
    ),
)

DEFAULT_ICON_LEVEL = "mdi:battery"
DEFAULT_ICON_STATE = "mdi:power-plug"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the iOS sensor."""
    # Leave here for if someone accidentally adds platform: ios to config


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up iOS from a config entry."""
    entities = [
        IOSSensor(device_name, device, description)
        for device_name, device in ios.devices(hass).items()
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities, True)


class IOSSensor(SensorEntity):
    """Representation of an iOS sensor."""

    _attr_should_poll = False

    def __init__(self, device_name, device, description: SensorEntityDescription):
        """Initialize the sensor."""
        self.entity_description = description
        self._device = device

        device_name = device[ios.ATTR_DEVICE][ios.ATTR_DEVICE_NAME]
        self._attr_name = f"{device_name} {description.key}"

        device_id = device[ios.ATTR_DEVICE_ID]
        self._attr_unique_id = f"{description.key}_{device_id}"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {
                (
                    ios.DOMAIN,
                    self._device[ios.ATTR_DEVICE][ios.ATTR_DEVICE_PERMANENT_ID],
                )
            },
            "name": self._device[ios.ATTR_DEVICE][ios.ATTR_DEVICE_NAME],
            "manufacturer": "Apple",
            "model": self._device[ios.ATTR_DEVICE][ios.ATTR_DEVICE_TYPE],
            "sw_version": self._device[ios.ATTR_DEVICE][ios.ATTR_DEVICE_SYSTEM_VERSION],
        }

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        device = self._device[ios.ATTR_DEVICE]
        device_battery = self._device[ios.ATTR_BATTERY]
        return {
            "Battery State": device_battery[ios.ATTR_BATTERY_STATE],
            "Battery Level": device_battery[ios.ATTR_BATTERY_LEVEL],
            "Device Type": device[ios.ATTR_DEVICE_TYPE],
            "Device Name": device[ios.ATTR_DEVICE_NAME],
            "Device Version": device[ios.ATTR_DEVICE_SYSTEM_VERSION],
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        device_battery = self._device[ios.ATTR_BATTERY]
        battery_state = device_battery[ios.ATTR_BATTERY_STATE]
        battery_level = device_battery[ios.ATTR_BATTERY_LEVEL]
        charging = True
        icon_state = DEFAULT_ICON_STATE
        if battery_state in (
            ios.ATTR_BATTERY_STATE_FULL,
            ios.ATTR_BATTERY_STATE_UNPLUGGED,
        ):
            charging = False
            icon_state = f"{DEFAULT_ICON_STATE}-off"
        elif battery_state == ios.ATTR_BATTERY_STATE_UNKNOWN:
            battery_level = None
            charging = False
            icon_state = f"{DEFAULT_ICON_LEVEL}-unknown"

        if self.entity_description.key == "state":
            return icon_state
        return icon_for_battery_level(battery_level=battery_level, charging=charging)

    @callback
    def _update(self, device):
        """Get the latest state of the sensor."""
        self._device = device
        self._attr_state = self._device[ios.ATTR_BATTERY][self.entity_description.key]
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Added to hass so need to register to dispatch."""
        self._attr_state = self._device[ios.ATTR_BATTERY][self.entity_description.key]
        device_id = self._device[ios.ATTR_DEVICE_ID]
        self.async_on_remove(
            async_dispatcher_connect(self.hass, f"{DOMAIN}.{device_id}", self._update)
        )
