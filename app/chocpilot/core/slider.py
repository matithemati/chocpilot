"""Suwak ChocPilot v0: położenie 0–100 % → głośność systemu albo wybranego programu.

Akcja wewnętrzna (bez rejestracji w ACTION_TYPES – nie pojawia się na liście akcji klawiszy):
kontroler tworzy ją dla każdej zmiany położenia i wykonuje w puli wątków jak inne akcje.
"""

from __future__ import annotations

from typing import Literal

from .actions import ActionBase, ActionContext


class SliderVolumeAction(ActionBase):
    type: str = "slider_volume"
    target: Literal["system_volume", "app_volume"] = "system_volume"
    process: str = ""
    label_text: str = ""
    value: int = 0  # 0–100

    def run(self, ctx: ActionContext) -> None:
        platform = ctx.platform
        if self.target == "system_volume":
            current = platform.get_system_volume()
            if current is None:
                raise RuntimeError("brak dostępu do głośności systemu")
            value = platform.change_system_volume(self.value - current)
            ctx.host.show_bar(self.label_text or "Glosnosc", value if value is not None else 0)
            return
        if not self.process:
            raise ValueError("nie podano procesu")
        name = self.label_text or self.process.rsplit(".", 1)[0][:12]
        # Mikser podaje tylko zmianę względną – zmiana o 0 zwraca bieżącą głośność.
        current = platform.change_app_volume(self.process, 0)
        if current is None:
            ctx.host.show_text(name, "nie gra", ms=1000)
            return
        value = platform.change_app_volume(self.process, self.value - current)
        ctx.host.show_bar(name, value if value is not None else current)

    def summary(self) -> str:
        if self.target == "system_volume":
            return f"Suwak: głośność systemu {self.value}%"
        return f"Suwak: głośność {self.process or '?'} {self.value}%"
