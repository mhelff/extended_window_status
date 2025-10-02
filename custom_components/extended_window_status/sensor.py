import logging
import re
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo, async_get as async_get_device_registry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.translation import async_get_translations
from homeassistant.const import CONF_DEVICE_ID

from .const import DOMAIN, MODE_ROTARY_TILT, MODE_BINARY_TILT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.debug(f"Setting up extended window sensor for config entry: {entry.entry_id}")
    device_id = entry.data[CONF_DEVICE_ID]
    base_entity = entry.data["base_entity"]
    second_entity = entry.data["second_entity"]
    device_name = entry.data["device_name"]
    mode = entry.data.get("mode", MODE_ROTARY_TILT)  # Default to rotary for backward compatibility

    # Get the existing device's identifiers from the device registry
    device_registry = async_get_device_registry(hass)
    device_entry = device_registry.async_get(device_id)
    if not device_entry:
        _LOGGER.error(f"Device with ID {device_id} not found in device registry")
        return
    device_identifiers = device_entry.identifiers

    # Create a valid entity_id from the device name
    safe_device_name = re.sub(r"[^a-zA-Z0-9\s]", "", device_name.lower()).replace(" ", "_")
    entity_id = f"sensor.{safe_device_name}_extended_window"

    description = SensorEntityDescription(
        key=DOMAIN,
        name=device_name,  # Use the device name as the sensor name
        icon="mdi:window-closed",  # Set window icon
    )

    entity = ExtendedWindowStatus(
        hass,
        description,
        device_identifiers,
        base_entity,
        second_entity,
        entity_id,
        mode,
    )

    # Ensure the entity_id is set in the entity registry
    entity_registry = async_get_entity_registry(hass)
    registry_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{base_entity}_{second_entity}_{mode}",
        suggested_object_id=entity_id.split(".")[1],  # Use the part after 'sensor.'
        device_id=device_id,
    )

    # Explicitly update the entity_id to ensure the suffix is applied
    if registry_entry.entity_id != entity_id:
        _LOGGER.debug(f"Updating entity_id from {registry_entry.entity_id} to {entity_id}")
        entity_registry.async_update_entity(
            entity_id=registry_entry.entity_id,
            new_entity_id=entity_id
        )

    async_add_entities([entity])
    _LOGGER.debug(f"Added extended window sensor for {device_name} with ID {entity.entity_id} to device with identifiers {device_identifiers}")

class ExtendedWindowStatus(SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        description: SensorEntityDescription,
        device_identifiers: set,
        base_entity: str,
        second_entity: str,
        entity_id: str,
        mode: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{base_entity}_{second_entity}_{mode}"
        self._attr_device_info = DeviceInfo(identifiers=device_identifiers)  # Use existing device's identifiers
        self._attr_entity_id = entity_id  # Set custom entity_id
        self._hass = hass
        self._base_entity = base_entity
        self._second_entity = second_entity
        self._mode = mode
        self._state = None
        self._remove_listeners = []
        self._translations = {}
        _LOGGER.debug(f"Initialized sensor: {self._attr_unique_id} with entity_id: {entity_id} for device with identifiers {device_identifiers}, mode: {mode}")

    async def async_added_to_hass(self) -> None:
        """Set up listeners for state changes and load translations when the entity is added."""
        # Load translations for the current language
        self._translations = await async_get_translations(
            self._hass, self._hass.config.language, "entity", integrations={DOMAIN}
        )
        self._remove_listeners.append(
            async_track_state_change_event(
                self._hass,
                [self._base_entity, self._second_entity],
                self._async_state_changed,
            )
        )
        await super().async_added_to_hass()
        # Perform initial update
        await self._async_update_state(None)
        _LOGGER.debug(f"Set up state change listeners for {self.entity_id}")

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when the entity is removed."""
        for remove_listener in self._remove_listeners:
            remove_listener()
        self._remove_listeners.clear()
        await super().async_will_remove_from_hass()
        _LOGGER.debug(f"Removed state change listeners for {self.entity_id}")

    async def _async_state_changed(self, event: Event) -> None:
        """Handle state changes of input entities."""
        await self._async_update_state(event)
        self.async_write_ha_state()
        _LOGGER.debug(f"State changed for {self.entity_id}, new state: {self._state}")

    async def _async_update_state(self, event: Event | None) -> None:
        """Update the sensor state based on input entities with localized values."""
        try:
            base_state = self._hass.states.get(self._base_entity)
            second_state = self._hass.states.get(self._second_entity)

            if base_state is None or second_state is None:
                _LOGGER.error(f"Missing state for {self._base_entity} or {self._second_entity}")
                self._state = None
                return

            # Get translation keys
            translation_key = f"component.{DOMAIN}.entity.sensor.{DOMAIN}.state."

            if self._mode == MODE_ROTARY_TILT:
                base_on = base_state.state == "on"
                try:
                    rotation = float(second_state.state)
                except (ValueError, TypeError):
                    _LOGGER.error(f"Invalid rotation value for {self._second_entity}")
                    self._state = None
                    return

                if not base_on:
                    self._state = self._translations.get(f"{translation_key}closed", "Closed")
                elif rotation == 0:
                    self._state = self._translations.get(f"{translation_key}open", "Open")
                elif rotation > 0:
                    self._state = self._translations.get(f"{translation_key}tilted", "Tilted")
                else:
                    self._state = None
            else:  # MODE_BINARY_TILT
                first_on = base_state.state == "on"
                second_on = second_state.state == "on"
                if not first_on and not second_on:
                    self._state = self._translations.get(f"{translation_key}closed", "Closed")
                elif first_on and second_on:
                    self._state = self._translations.get(f"{translation_key}open", "Open")
                elif not first_on and second_on:
                    self._state = self._translations.get(f"{translation_key}tilted", "Tilted")
                else:  # first_on and not second_on
                    self._state = None  # Invalid state for sensor mode
                    _LOGGER.warning(f"Invalid state combination for {self.entity_id}: first_on={first_on}, second_on={second_on}")

            _LOGGER.debug(f"Updated state for {self.entity_id}: {self._state}")
        except Exception as e:
            _LOGGER.error(f"Error updating {self.entity_id}: {e}")
            self._state = None

    @property
    def state(self) -> str | None:
        return self._state