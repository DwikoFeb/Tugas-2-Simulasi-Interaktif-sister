from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MessageEvent:
    msg_id: int
    kind: str                      # "request" | "response" | "event"
    label: str                     # teks singkat ditampilkan di tooltip/log
    origin: str                    # nama node asal
    destination: str                # nama node tujuan
    sent_at_ms: int
    delivered_at_ms: Optional[int] = None
    dropped: bool = False
    payload_size_kb: float = 1.0
    extra: dict = field(default_factory=dict)

    def latency_ms(self) -> Optional[int]:
        if self.delivered_at_ms is None:
            return None
        return self.delivered_at_ms - self.sent_at_ms
