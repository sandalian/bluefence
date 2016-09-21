from gattlib import DiscoveryService

service = DiscoveryService("hci0")
devices = service.discover(2)
print devices
