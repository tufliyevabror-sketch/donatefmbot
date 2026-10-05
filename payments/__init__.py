"""To'lov provayderlari abstraksiyasi.

Hozir jonli: ManualProvider (karta/terminal, admin tasdiqlaydi).
Keyingi qadam: ClickProvider / PaymeProvider shu interfeysga yoziladi,
merchant credentiallar .env ga qo'shilgach server.py da almashtiriladi.
"""
from dataclasses import dataclass


@dataclass
class PaymentIntent:
    provider: str
    amount: int
    ref: str
    pay_url: str = ""
    external_id: str = ""


class BaseProvider:
    name = "base"

    def create_intent(self, user_id: int, amount: int, ref: str) -> PaymentIntent:
        raise NotImplementedError

    def verify_callback(self, payload: dict) -> bool:
        raise NotImplementedError


class ManualProvider(BaseProvider):
    """Hozirgi oqim: karta raqami beriladi, chek admin tomonidan tasdiqlanadi."""

    name = "manual"

    def create_intent(self, user_id: int, amount: int, ref: str) -> PaymentIntent:
        return PaymentIntent(provider=self.name, amount=amount, ref=ref)

    def verify_callback(self, payload: dict) -> bool:
        return bool(payload.get("admin_confirmed"))


class ClickProvider(BaseProvider):
    """Stub: merchant_id/service_id/secret_key .env ga qo'yilgach to'ldiriladi."""

    name = "click"

    def create_intent(self, user_id: int, amount: int, ref: str) -> PaymentIntent:
        raise RuntimeError("Click merchant credentiallari sozlanmagan")

    def verify_callback(self, payload: dict) -> bool:
        raise RuntimeError("Click merchant credentiallari sozlanmagan")


class PaymeProvider(BaseProvider):
    """Stub: merchant_id/key .env ga qo'yilgach to'ldiriladi."""

    name = "payme"

    def create_intent(self, user_id: int, amount: int, ref: str) -> PaymentIntent:
        raise RuntimeError("Payme merchant credentiallari sozlanmagan")

    def verify_callback(self, payload: dict) -> bool:
        raise RuntimeError("Payme merchant credentiallari sozlanmagan")


PROVIDERS = {
    "manual": ManualProvider(),
    "click": ClickProvider(),
    "payme": PaymeProvider(),
}


def get_provider(name: str) -> BaseProvider:
    return PROVIDERS.get(name, PROVIDERS["manual"])
