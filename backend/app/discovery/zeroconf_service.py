"""Device discovery manager using AsyncZeroconf."""

import asyncio
import logging
import socket
from typing import Callable, Dict, List, Optional
import uuid

from zeroconf import IPVersion, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from app.discovery.device import Device, DeviceRole, DeviceStatus, DiscoveryMethod

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_peershare._tcp.local."


def get_local_ip() -> str:
    """Determine the primary local network IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not send actual traffic, merely binds routing
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class DeviceDiscoveryManager:
    """Manages Zeroconf mDNS advertisement for receivers and service browsing for senders."""

    def __init__(
        self,
        aiozc: Optional[AsyncZeroconf] = None,
        on_device_discovered: Optional[Callable[[Device], None]] = None,
    ) -> None:
        self.aiozc = aiozc
        self._owns_aiozc = aiozc is None
        self.on_device_discovered = on_device_discovered

        self._advertised_info: Optional[AsyncServiceInfo] = None
        self._browser: Optional[AsyncServiceBrowser] = None
        self.discovered_devices: Dict[str, Device] = {}
        self._running = False

    async def _ensure_aiozc(self) -> AsyncZeroconf:
        if self.aiozc is None:
            self.aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        return self.aiozc

    async def start_advertising(
        self,
        device_id: uuid.UUID,
        device_name: str,
        api_port: int,
        udp_port: int = 0,
        api_version: str = "1.0.0",
        ip_address: Optional[str] = None,
    ) -> None:
        """Advertise this device as an available Receiver on the local network."""
        aiozc = await self._ensure_aiozc()
        local_ip = ip_address or get_local_ip()

        service_name = f"{device_name}-{str(device_id)[:8]}.{SERVICE_TYPE}"
        properties = {
            "device_id": str(device_id),
            "device_name": device_name,
            "api_port": str(api_port),
            "udp_port": str(udp_port),
            "api_version": api_version,
            "role": DeviceRole.RECEIVER.value,
        }

        self._advertised_info = AsyncServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=api_port,
            properties=properties,
        )

        logger.info("Advertising service: %s at %s:%d", service_name, local_ip, api_port)
        await aiozc.async_register_service(self._advertised_info)
        self._running = True

    async def stop_advertising(self) -> None:
        """Unregister the advertised service."""
        if self._advertised_info and self.aiozc:
            logger.info("Unregistering service: %s", self._advertised_info.name)
            await self.aiozc.async_unregister_service(self._advertised_info)
            self._advertised_info = None

    async def start_discovery(self) -> None:
        """Start browsing for available Receiver devices."""
        aiozc = await self._ensure_aiozc()
        if self._browser is None:
            self._browser = AsyncServiceBrowser(
                aiozc.zeroconf,
                SERVICE_TYPE,
                handlers=[self._on_service_state_change],
            )
            logger.info("Started Zeroconf discovery for %s", SERVICE_TYPE)
        self._running = True

    async def stop_discovery(self) -> None:
        """Stop browsing for devices."""
        if self._browser:
            await self._browser.async_cancel()
            self._browser = None
            logger.info("Stopped Zeroconf discovery")

    def _on_service_state_change(
        self,
        zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Handle service addition, update, or removal."""
        asyncio.create_task(self._handle_state_change(name, state_change))

    async def _handle_state_change(self, name: str, state_change: ServiceStateChange) -> None:
        if state_change == ServiceStateChange.Removed:
            if name in self.discovered_devices:
                del self.discovered_devices[name]
                logger.debug("Device removed from discovery: %s", name)
            return

        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            aiozc = await self._ensure_aiozc()
            info = AsyncServiceInfo(SERVICE_TYPE, name)
            success = await info.async_request(aiozc.zeroconf, 3000)
            if not success:
                return

            try:
                addresses = info.parsed_scoped_addresses()
                if not addresses:
                    return
                ip_addr = addresses[0]

                props = {
                    k.decode("utf-8") if isinstance(k, bytes) else k: (
                        v.decode("utf-8") if isinstance(v, bytes) else v
                    )
                    for k, v in info.properties.items()
                }

                device_id_str = props.get("device_id")
                if not device_id_str:
                    return

                device_id = uuid.UUID(device_id_str)
                device_name = props.get("device_name", name.split(".")[0])
                api_port = int(props.get("api_port", info.port or 8000))
                udp_port = int(props.get("udp_port", 0))
                api_version = props.get("api_version", "1.0.0")

                device = Device(
                    device_id=device_id,
                    device_name=device_name,
                    ip_address=ip_addr,
                    api_port=api_port,
                    udp_port=udp_port,
                    api_version=api_version,
                    role=DeviceRole.RECEIVER,
                    discovery_method=DiscoveryMethod.ZEROCONF,
                    status=DeviceStatus.ONLINE,
                )

                self.discovered_devices[name] = device
                logger.info("Discovered device: %s at %s:%d", device_name, ip_addr, api_port)

                if self.on_device_discovered:
                    self.on_device_discovered(device)

            except Exception as exc:
                logger.warning("Error parsing discovered service %s: %s", name, exc)

    def get_discovered_devices(self) -> List[Device]:
        """Return list of currently discovered active devices."""
        return list(self.discovered_devices.values())

    async def close(self) -> None:
        """Clean up Zeroconf resources."""
        await self.stop_advertising()
        await self.stop_discovery()
        if self._owns_aiozc and self.aiozc:
            await self.aiozc.async_close()
            self.aiozc = None
        self._running = False

