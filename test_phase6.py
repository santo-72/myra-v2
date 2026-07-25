from app.auth.vault import Vault
from app.tools.system_telemetry import SystemTelemetry

vault = Vault()
encrypted = vault.encrypt("my_secret")
decrypted = vault.decrypt(encrypted)
print(f"Vault Test: 'my_secret' -> Encrypted: {encrypted} -> Decrypted: {decrypted}")
assert decrypted == "my_secret"

telemetry = SystemTelemetry()
metrics = telemetry.get_metrics()
print(f"Telemetry metrics: {metrics}")
