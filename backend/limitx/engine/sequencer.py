from dataclasses import dataclass


@dataclass(slots=True)
class Sequencer:
    value: int = 0

    def next(self) -> int:
        self.value += 1
        return self.value
