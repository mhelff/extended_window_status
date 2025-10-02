import logging
from typing import Any, Dict
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.helpers.selector import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, MODE_ROTARY_TILT, MODE_BINARY_TILT

_LOGGER = logging.getLogger(__name__)

class EntityCombinerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Combiner."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step: select device and binary entity."""
        _LOGGER.debug(f"Config flow step: user, input: {user_input}")
        errors = {}
        if user_input is not None:
            try:
                # Get the device name from the device registry
                device_registry = async_get_device_registry(self.hass)
                device_entry = device_registry.async_get(user_input[CONF_DEVICE_ID])
                if not device_entry:
                    errors[CONF_DEVICE_ID] = "device_invalid"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_user_schema(),
                        errors=errors,
                    )
                device_name = device_entry.name_by_user or device_entry.name or "Unnamed Device"

                # Save data for next step
                self._temp_data = {
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                    "base_entity": user_input["base_entity"],
                    "device_name": device_name,
                }
                _LOGGER.debug(f"User step completed, proceeding to mode selection for device {device_name}")
                return await self.async_step_mode()
            except Exception as e:
                _LOGGER.error(f"Error in config flow user step: {e}")
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_user_schema(),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_schema(),
            errors=errors,
            description_placeholders={
                "description": (
                    "Select the device and binary sensor or boolean helper for the extended window sensor."
                )
            },
        )

    def _get_user_schema(self):
        """Return the schema for the user step."""
        return vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): selector({
                    "device": {
                        "filter": {}
                    }
                }),
                vol.Required("base_entity"): selector({
                    "entity": {
                        "domain": ["binary_sensor", "input_boolean"]
                    }
                }),
            }
        )

    async def async_step_mode(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the mode selection step."""
        _LOGGER.debug(f"Config flow step: mode, input: {user_input}")
        errors = {}
        if user_input is not None:
            mode = user_input["mode"]
            self._temp_data["mode"] = mode
            _LOGGER.debug(f"Mode selected: {mode}")
            return await self.async_step_second_entity()

        return self.async_show_form(
            step_id="mode",
            data_schema=vol.Schema({
                vol.Required("mode"): selector({
                    "select": {
                        "options": [
                            {"label": "Rotary value", "value": MODE_ROTARY_TILT},
                            {"label": "Another window sensor", "value": MODE_BINARY_TILT},
                        ],
                        "translation_key": "mode"
                    }
                }),
            }),
            errors=errors,
            description_placeholders={
                "description": "Select how the tilted status should be calculated."
            },
        )

    async def async_step_second_entity(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the second entity selection step based on mode."""
        _LOGGER.debug(f"Config flow step: second_entity, input: {user_input}")
        errors = {}
        if user_input is not None:
            self._temp_data["second_entity"] = user_input["second_entity"]
            _LOGGER.debug(f"Creating config entry for device {self._temp_data['device_name']}")
            return self.async_create_entry(
                title=self._temp_data['device_name'],
                data=self._temp_data,
            )

        mode = self._temp_data["mode"]
        if mode == MODE_ROTARY_TILT:
            schema = vol.Schema({
                vol.Required("second_entity"): selector({
                    "entity": {
                        "domain": ["number", "input_number"]
                    }
                }),
            })
            description = "Select the number or number helper for rotation."
        else:
            schema = vol.Schema({
                vol.Required("second_entity"): selector({
                    "entity": {
                        "domain": ["binary_sensor", "input_boolean"]
                    }
                }),
            })
            description = "Select the second binary sensor or boolean helper for the window sensor."

        return self.async_show_form(
            step_id="second_entity",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": description
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        _LOGGER.debug(f"Starting options flow for config entry: {config_entry.entry_id}")
        return EntityCombinerOptionsFlow(config_entry)

class EntityCombinerOptionsFlow(OptionsFlow):
    """Handle options flow for Entity Combiner."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        _LOGGER.debug(f"Initialized options flow for {config_entry.entry_id}")

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step of options flow."""
        errors = {}
        if user_input is not None:
            try:
                # Get the device name from the device registry
                device_registry = async_get_device_registry(self.hass)
                device_entry = device_registry.async_get(user_input[CONF_DEVICE_ID])
                if not device_entry:
                    errors[CONF_DEVICE_ID] = "device_invalid"
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._get_init_schema(),
                        errors=errors,
                    )
                device_name = device_entry.name_by_user or device_entry.name or "Unnamed Device"

                # Save data for next step
                self._temp_data = {
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                    "base_entity": user_input["base_entity"],
                    "device_name": device_name,
                    "mode": user_input["mode"],
                }
                _LOGGER.debug(f"Options flow init completed, proceeding to second entity for device {device_name}")
                return await self.async_step_second_entity()

            except Exception as e:
                _LOGGER.error(f"Error in options flow: {e}")
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_init_schema(),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_init_schema(),
            errors=errors,
            description_placeholders={
                "description": (
                    "Select the device, binary sensor or boolean helper, and mode for the combined sensor."
                )
            },
        )

    async def async_step_second_entity(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the second entity selection step in options flow."""
        _LOGGER.debug(f"Options flow step: second_entity, input: {user_input}")
        errors = {}
        if user_input is not None:
            self._temp_data["second_entity"] = user_input["second_entity"]
            _LOGGER.debug(f"Updating options for device {self._temp_data['device_name']}")
            return self.async_create_entry(
                title=self._temp_data['device_name'],
                data=self._temp_data,
            )

        mode = self._temp_data["mode"]
        if mode == MODE_ROTARY:
            schema = vol.Schema({
                vol.Required("second_entity", default=self.config_entry.data.get("second_entity")): selector({
                    "entity": {
                        "domain": ["number", "input_number"]
                    }
                }),
            })
            description = "Select the number or number helper for rotation."
        else:
            schema = vol.Schema({
                vol.Required("second_entity", default=self.config_entry.data.get("second_entity")): selector({
                    "entity": {
                        "domain": ["binary_sensor", "input_boolean"]
                    }
                }),
            })
            description = "Select the second binary sensor or boolean helper for the window sensor."

        return self.async_show_form(
            step_id="second_entity",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": description
            },
        )

    def _get_init_schema(self):
        """Return the schema for the options flow init step."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_ID,
                    default=self.config_entry.data.get(CONF_DEVICE_ID),
                ): selector({
                    "device": {
                        "filter": {}
                    }
                }),
                vol.Required(
                    "base_entity",
                    default=self.config_entry.data.get("base_entity"),
                ): selector({
                    "entity": {
                        "domain": ["binary_sensor", "input_boolean"]
                    }
                }),
                vol.Required(
                    "mode",
                    default=self.config_entry.data.get("mode", MODE_ROTARY_TILT),
                ): selector({
                    "select": {
                        "options": [
                            {"label": "Rotary value", "value": MODE_ROTARY_TILT},
                            {"label": "Another window sensor", "value": MODE_BINARY_TILT},
                        ],
                        "translation_key": "mode"
                    }
                }),
            }
        )