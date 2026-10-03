"""
AudioSpatialSystem - 包含多个严重bug，需要修复。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time
import math


@dataclass
class State:
    """通用状态容器"""
    values: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def has(self, key: str) -> bool:
        return key in self.values


class AudioSpatialSystem:
    """
    AudioSpatialSystem 主类。

    注意：本类包含多个故意植入的bug，需要修复后才能通过测试。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.state = State()
        self.history: List[Dict[str, Any]] = []
        self._initialized = False
        self._tick_count = 0

    def initialize(self) -> bool:
        """初始化系统"""
        # BUG: 没有设置_initialized标志
        self.state = State()
        self.history = []
        return True

    def tick(self, delta_time: float = 1.0) -> None:
        """推进一个时间步"""
        if not self._initialized:
            self.initialize()
        self._tick_count += 1
        self.state.timestamp += delta_time
        self._update_state(delta_time)

    def _update_state(self, delta_time: float) -> None:
        """更新内部状态 - 子类可重写"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态快照"""
        return dict(self.state.values)

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return list(self.history)

    def reset(self) -> None:
        """重置系统"""
        self.state = State()
        self.history = []
        self._initialized = False
        self._tick_count = 0
