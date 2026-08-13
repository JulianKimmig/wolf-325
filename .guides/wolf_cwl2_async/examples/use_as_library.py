"""Minimal library example. Run from the project directory."""

import asyncio

from wolf_cwl2 import WolfCWL2


async def main() -> None:
    controller = WolfCWL2("config.json")
    controller.subscribe(lambda update: print(update["key"], update["value"]))
    await controller.start()
    try:
        print("Supply temperature:", controller.get_value("supply_temperature_c"))
        await controller.set_ventilation_level("normal")
        await asyncio.Event().wait()
    finally:
        await controller.stop()


if __name__ == "__main__":
    asyncio.run(main())
