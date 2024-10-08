"""Support for Span Panel monitor."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CIRCUITS_ENERGY_CONSUMED,
    CIRCUITS_ENERGY_PRODUCED,
    CIRCUITS_POWER,
    COORDINATOR,
    CURRENT_RUN_CONFIG,
    DOMAIN,
    DSM_GRID_STATE,
    DSM_STATE,
    MAIN_RELAY_STATE,
    STAUS_SOFTWARE_VER,
    STORAGE_BATTERY_PERCENTAGE,
)

from .options import INVERTER_ENABLE, BATTERY_ENABLE
from .span_panel import SpanPanel
from .span_panel_api import SpanPanelApi
from .span_panel_circuit import SpanPanelCircuit
from .span_panel_data import SpanPanelData
from .span_panel_status import SpanPanelStatus
from .span_panel_storage_battery import SpanPanelStorageBattery
from .util import panel_to_device_info


@dataclass
class SpanPanelCircuitsRequiredKeysMixin:
    value_fn: Callable[[SpanPanelCircuit], str]


@dataclass
class SpanPanelCircuitsSensorEntityDescription(
    SensorEntityDescription, SpanPanelCircuitsRequiredKeysMixin
):
    pass


@dataclass
class SpanPanelDataRequiredKeysMixin:
    value_fn: Callable[[SpanPanelData], str]


@dataclass
class SpanPanelDataSensorEntityDescription(
    SensorEntityDescription, SpanPanelDataRequiredKeysMixin
):
    pass


@dataclass
class SpanPanelStatusRequiredKeysMixin:
    value_fn: Callable[[SpanPanelStatus], str]


@dataclass
class SpanPanelStatusSensorEntityDescription(
    SensorEntityDescription, SpanPanelStatusRequiredKeysMixin
):
    pass

@dataclass
class SpanPanelStorageBatteryRequiredKeysMixin:
    value_fn: Callable[[SpanPanelStorageBattery], str]


@dataclass
class SpanPanelStorageBatterySensorEntityDescription(
    SensorEntityDescription, SpanPanelStorageBatteryRequiredKeysMixin
):
    pass



CIRCUITS_SENSORS = (
    SpanPanelCircuitsSensorEntityDescription(
        key=CIRCUITS_POWER,
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda circuit: abs(cast(float, circuit.instant_power)),
    ),
    SpanPanelCircuitsSensorEntityDescription(
        key=CIRCUITS_ENERGY_PRODUCED,
        name="Produced Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda circuit: circuit.produced_energy,
    ),
    SpanPanelCircuitsSensorEntityDescription(
        key=CIRCUITS_ENERGY_CONSUMED,
        name="Consumed Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda circuit: circuit.consumed_energy,
    ),
    
)

PANEL_SENSORS = (
    SpanPanelDataSensorEntityDescription(
        key="instantGridPowerW",
        name="Current Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda panel_data: panel_data.instant_grid_power,
    ),
    SpanPanelDataSensorEntityDescription(
        key="feedthroughPowerW",
        name="Feed Through Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda panel_data: panel_data.feedthrough_power,
    ),
    SpanPanelDataSensorEntityDescription(
        key="mainMeterEnergy.producedEnergyWh",
        name="Main Meter Produced Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda panel_data: panel_data.main_meter_energy_produced,
    ),
    SpanPanelDataSensorEntityDescription(
        key="mainMeterEnergy.consumedEnergyWh",
        name="Main Meter Consumed Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda panel_data: panel_data.main_meter_energy_consumed,
    ),
    SpanPanelDataSensorEntityDescription(
        key="feedthroughEnergy.producedEnergyWh",
        name="Feed Through Produced Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda panel_data: panel_data.feedthrough_energy_produced,
    ),
    SpanPanelDataSensorEntityDescription(
        key="feedthroughEnergy.consumedEnergyWh",
        name="Feed Through Consumed Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda panel_data: panel_data.feedthrough_energy_consumed,
    ),
)

INVERTER_SENSORS = (
        SpanPanelDataSensorEntityDescription(
        key="solar_inverter_instant_power",
        name="Solar Inverter Instant Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda panel_data: panel_data.solar_inverter_instant_power,
    ),
    SpanPanelDataSensorEntityDescription(
        key="solar_inverter_energy_produced",
        name="Solar Inverter Energy Produced",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda panel_data: panel_data.solar_inverter_energy_produced,
    ),
    SpanPanelDataSensorEntityDescription(
        key="solar_inverter_energy_consumed",
        name="Solar Inverter Energy Consumed",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda panel_data: panel_data.solar_inverter_energy_consumed,
    ),
)

PANEL_DATA_STATUS_SENSORS = (
    SpanPanelDataSensorEntityDescription(
        key=CURRENT_RUN_CONFIG,
        name="Current Run Config",
        value_fn=lambda panel_data: panel_data.current_run_config,
    ),
    SpanPanelDataSensorEntityDescription(
        key=DSM_GRID_STATE,
        name="DSM Grid State",
        value_fn=lambda panel_data: panel_data.dsm_grid_state,
    ),
    SpanPanelDataSensorEntityDescription(
        key=DSM_STATE,
        name="DSM State",
        value_fn=lambda panel_data: panel_data.dsm_state,
    ),
    SpanPanelDataSensorEntityDescription(
        key=MAIN_RELAY_STATE,
        name="Main Relay State",
        value_fn=lambda panel_data: panel_data.main_relay_state,
    ),
)

STATUS_SENSORS = (
    SpanPanelStatusSensorEntityDescription(
        key=STAUS_SOFTWARE_VER,
        name="Software Version",
        value_fn=lambda status: status.firmware_version,
    ),
)

STORAGE_BATTERY_SENSORS = (
    SpanPanelStorageBatterySensorEntityDescription(
        key=STORAGE_BATTERY_PERCENTAGE,
        name="SPAN Storage Battery Percentage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=BATTERY_ENABLE,
        value_fn=lambda storage_battery: storage_battery,
    ),    
)

ICON = "mdi:flash"
_LOGGER = logging.getLogger(__name__)

class SpanPanelCircuitSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = ICON

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SpanPanelCircuitsSensorEntityDescription,
        circuit_id: str,
        name: str,
    ) -> None:
        """Initialize Span Panel Circuit entity."""
        span_panel: SpanPanel = coordinator.data

        self.entity_description = description
        self.id = circuit_id
        self._attr_name = f"{name} {description.name}"
        self._attr_unique_id = (
            f"span_{span_panel.status.serial_number}_{circuit_id}_{description.key}"
        )
        self._attr_device_info = panel_to_device_info(span_panel)

        _LOGGER.debug("CREATE SENSOR [%s]", self._attr_name)
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        span_panel: SpanPanel = self.coordinator.data
        value = self.entity_description.value_fn(span_panel.circuits[self.id])
        _LOGGER.debug("native_value:[%s] [%s]", self._attr_name, value)
        return cast(float, value)


class SpanPanelPanel(CoordinatorEntity, SensorEntity):
    _attr_icon = ICON

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Span Panel Circuit entity."""
        span_panel: SpanPanel = coordinator.data

        self.entity_description = description
        self._attr_name = f"{description.name}"
        self._attr_unique_id = (
            f"span_{span_panel.status.serial_number}_{description.key}"
        )
        self._attr_device_info = panel_to_device_info(span_panel)

        _LOGGER.debug("CREATE SENSOR SPAN [%s]", self._attr_name)
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        span_panel: SpanPanel = self.coordinator.data
        value = self.entity_description.value_fn(span_panel.panel)
        return cast(float, value)

class SpanPanelPanelStatus(CoordinatorEntity, SensorEntity):
    _attr_icon = ICON

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Span Panel Extra entity."""
        span_panel: SpanPanel = coordinator.data

        self.entity_description = description
        self._attr_name = f"{description.name}"
        self._attr_unique_id = (
            f"span_{span_panel.status.serial_number}_{description.key}"
        )
        self._attr_device_info = panel_to_device_info(span_panel)

        _LOGGER.debug("CREATE SENSOR SPAN [%s]", self._attr_name)
        super().__init__(coordinator)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        span_panel: SpanPanel = self.coordinator.data
        return self.entity_description.value_fn(span_panel.panel)

class SpanPanelStatus(CoordinatorEntity, SensorEntity):
    _attr_icon = ICON

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Span Panel Status entity."""
        span_panel: SpanPanel = coordinator.data

        self.entity_description = description
        self._attr_name = f"{description.name}"
        self._attr_unique_id = (
            f"span_{span_panel.status.serial_number}_{description.key}"
        )
        self._attr_device_info = panel_to_device_info(span_panel)

        _LOGGER.debug("CREATE SENSOR SPAN [%s]", self._attr_name)
        super().__init__(coordinator)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        span_panel: SpanPanel = self.coordinator.data
        value = self.entity_description.value_fn(span_panel.status)
        return value


class SpanPanelStorageBatteryStatus(CoordinatorEntity, SensorEntity):
    """Battery Status"""
    _attr_icon = "mdi:battery"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SpanPanelStorageBatterySensorEntityDescription,
    ) -> None:
        """Initialize Span Panel Storage Battery entity."""
        span_panel: SpanPanel = coordinator.data

        self.entity_description = description
        self._attr_name = f"{description.name}"
        self._attr_unique_id = (
            f"span_{span_panel.status.serial_number}_{description.key}"
        )
        self._attr_device_info = panel_to_device_info(span_panel)

        _LOGGER.debug("CREATE SENSOR SPAN [%s]", self._attr_name)
        super().__init__(coordinator)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        span_panel: SpanPanel = self.coordinator.data
        value = self.entity_description.value_fn(span_panel.storage_battery)
        return value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up envoy sensor platform."""

    _LOGGER.debug("ASYNC SETUP ENTRY SENSOR")
    data: dict = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("  config_entry: %s", config_entry)
    _LOGGER.debug("  config_entry(uid): %s", config_entry.unique_id)
    _LOGGER.debug("  data: %s", data)

    coordinator: DataUpdateCoordinator = data[COORDINATOR]
    span_panel: SpanPanel = coordinator.data

    entities: list[SpanPanelCircuitSensor | SpanPanelPanel | SpanPanelExtra | SpanPanelStatus | SpanPanelStorageBatteryStatus] = []

    for description in PANEL_SENSORS:
        entities.append(SpanPanelPanel(coordinator, description))
    for description in PANEL_DATA_STATUS_SENSORS:
        entities.append(SpanPanelPanelStatus(coordinator, description))
    if config_entry.options.get(INVERTER_ENABLE, False):
        for description in INVERTER_SENSORS:
            entities.append(SpanPanelPanel(coordinator, description))

    for description in STATUS_SENSORS:
        entities.append(SpanPanelStatus(coordinator, description))

    for description in CIRCUITS_SENSORS:
        for id, circuit_data in span_panel.circuits.items():
            entities.append(
                SpanPanelCircuitSensor(coordinator, description, id, circuit_data.name)
            )
    if config_entry.options.get(BATTERY_ENABLE, False):
        for description in STORAGE_BATTERY_SENSORS:
            entities.append(SpanPanelStorageBatteryStatus(coordinator, description))
    
    async_add_entities(entities)
