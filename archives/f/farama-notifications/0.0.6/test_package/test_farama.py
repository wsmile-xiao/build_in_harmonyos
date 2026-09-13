import farama_notifications

assert isinstance(farama_notifications.notifications, dict)
assert "gymnasium_robotics" in farama_notifications.notifications

print("farama-notifications test package: OK")