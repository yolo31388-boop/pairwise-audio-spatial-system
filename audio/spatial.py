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
        self.state = State()
        self.history = []
        self._initialized = True
        return True

    @property
    def timestamp(self) -> float:
        """当前时间戳（代理到内部状态）"""
        return self.state.timestamp

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

    # ------------------------------------------------------------------
    # 声像（Panning）
    # ------------------------------------------------------------------

    def calculate_pan(
        self,
        source_position: Tuple[float, float, float],
        listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        listener_yaw: float = 0.0,
    ) -> Dict[str, Any]:
        """基于 HRTF 近似模型的声像计算。

        - HRTF：按方位角计算耳间时间差(ITD)与耳间声级差(ILD)
        - 距离衰减：增益随距离按 1/d 衰减（最小距离 1 米）
        - 高度：按仰角对整体增益做高频衰减近似，头顶/脚下声音不再等同
        """
        dx = source_position[0] - listener_position[0]
        dy = source_position[1] - listener_position[1]
        dz = source_position[2] - listener_position[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        azimuth = math.atan2(dx, dz) - listener_yaw
        horizontal = math.sqrt(dx * dx + dz * dz)
        elevation = math.atan2(dy, horizontal) if horizontal > 1e-9 else (
            math.copysign(math.pi / 2, dy) if dy != 0 else 0.0
        )

        head_radius = 0.0875  # 米，典型人头半径
        speed_of_sound = 343.0
        itd = (head_radius / speed_of_sound) * (
            math.sin(azimuth) + azimuth
        )  # Woodworth 近似

        # ILD：对侧耳遮蔽，最大约 20 dB
        ild_db = 20.0 * math.sin(azimuth)
        left_gain = 10.0 ** (-ild_db / 40.0)
        right_gain = 10.0 ** (ild_db / 40.0)

        # 距离衰减（1/d，最小距离 1 米避免除零/过响）
        distance_gain = 1.0 / max(distance, 1.0)

        # 高度：偏离水平面时整体响度与高频内容下降
        elevation_gain = math.cos(elevation) ** 2 * 0.5 + 0.5

        return {
            "left": left_gain * distance_gain * elevation_gain,
            "right": right_gain * distance_gain * elevation_gain,
            "itd": itd,
            "azimuth": azimuth,
            "elevation": elevation,
            "distance": distance,
            "distance_gain": distance_gain,
        }

    # ------------------------------------------------------------------
    # 混响（Reverb）
    # ------------------------------------------------------------------

    def calculate_reverb(
        self,
        room_size: Tuple[float, float, float] = (5.0, 4.0, 3.0),
        material_absorption: float = 0.5,
    ) -> Dict[str, Any]:
        """房间混响计算。

        - 早期反射与晚期混响分离建模
        - 房间大小：Sabine 公式 RT60 = 0.161 * V / A
        - 材质吸收：吸收系数直接进入 Sabine 公式并影响反射增益
        """
        length, width, height = room_size
        volume = length * width * height
        surface_area = 2.0 * (length * width + length * height + width * height)
        absorption = min(max(material_absorption, 0.01), 1.0)
        total_absorption = surface_area * absorption

        rt60 = 0.161 * volume / total_absorption

        # 早期反射：各面墙的一次反射，延迟由路径长度决定
        speed_of_sound = 343.0
        reflection_gain = (1.0 - absorption) ** 2
        early_reflections = [
            {"delay": length / speed_of_sound, "gain": reflection_gain},
            {"delay": width / speed_of_sound, "gain": reflection_gain},
            {"delay": height / speed_of_sound, "gain": reflection_gain},
        ]

        # 晚期混响：指数衰减，衰减时间即 RT60
        late_reverb = {
            "decay_time": rt60,
            "mix": min(0.5, rt60 / 4.0),
        }

        return {
            "early_reflections": early_reflections,
            "late_reverb": late_reverb,
            "rt60": rt60,
            "volume": volume,
            "absorption": absorption,
        }

    # ------------------------------------------------------------------
    # 遮挡（Occlusion）
    # ------------------------------------------------------------------

    def calculate_occlusion(
        self,
        source_position: Tuple[float, float, float],
        listener_position: Tuple[float, float, float],
        obstacles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """遮挡计算。

        - 低通滤波：遮挡越严重截止频率越低，墙后声音变闷
        - 衍射：声音可绕过障碍物，保留部分能量而非完全消失
        - 动态：每次调用基于障碍物当前位置重新计算，障碍物移动即更新
        """
        obstacles = obstacles or []
        occlusion_level = 0.0
        for obstacle in obstacles:
            pos = obstacle.get("position", (0.0, 0.0, 0.0))
            radius = obstacle.get("radius", 1.0)
            if self._segment_intersects_sphere(
                source_position, listener_position, pos, radius
            ):
                thickness = obstacle.get("thickness", radius)
                occlusion_level = min(1.0, occlusion_level + min(1.0, thickness / (2.0 * radius)))

        # 低通滤波：截止频率随遮挡程度从 20kHz 下降
        cutoff = 20000.0 * (1.0 - occlusion_level) ** 2 + 200.0 * occlusion_level

        # 衍射：遮挡时仍有绕射路径，音量不会降为零
        direct_gain = 1.0 - occlusion_level
        diffraction_gain = 0.3 * occlusion_level
        gain = direct_gain + diffraction_gain

        return {
            "gain": gain,
            "cutoff": cutoff,
            "occlusion_level": occlusion_level,
            "diffraction_gain": diffraction_gain,
        }

    @staticmethod
    def _segment_intersects_sphere(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
        center: Tuple[float, float, float],
        radius: float,
    ) -> bool:
        """线段 ab 是否与球体相交"""
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (center[0] - a[0], center[1] - a[1], center[2] - a[2])
        ab_len2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
        if ab_len2 < 1e-12:
            return False
        t = max(0.0, min(1.0, (ac[0] * ab[0] + ac[1] * ab[1] + ac[2] * ab[2]) / ab_len2))
        closest = (a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t)
        dist2 = (
            (closest[0] - center[0]) ** 2
            + (closest[1] - center[1]) ** 2
            + (closest[2] - center[2]) ** 2
        )
        return dist2 <= radius * radius

    # ------------------------------------------------------------------
    # 多普勒效应（Doppler）
    # ------------------------------------------------------------------

    def calculate_doppler(
        self,
        frequency: float,
        source_velocity: Tuple[float, float, float],
        listener_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        source_position: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> float:
        """多普勒频移计算。

        - 方向：速度投影到声源-听者连线，靠近升频、远离降频
        - 相对论修正：高速下使用相对论多普勒公式
        - 限制：速度钳制在声速以下，频率不会变为负数
        """
        direction = (
            listener_position[0] - source_position[0],
            listener_position[1] - source_position[1],
            listener_position[2] - source_position[2],
        )
        dist = math.sqrt(sum(c * c for c in direction))
        if dist < 1e-9:
            return frequency
        direction = tuple(c / dist for c in direction)

        # 径向速度：正值表示相互靠近
        v_source = sum(s * d for s, d in zip(source_velocity, direction))
        v_listener = sum(l * d for l, d in zip(listener_velocity, direction))

        speed_of_sound = 343.0
        max_speed = 0.99 * speed_of_sound  # 限制：钳制在声速以下
        v_source = max(-max_speed, min(max_speed, v_source))
        v_listener = max(-max_speed, min(max_speed, v_listener))

        # 经典多普勒：f' = f * (c + v_listener) / (c - v_source)
        shifted = frequency * (speed_of_sound + v_listener) / (speed_of_sound - v_source)

        # 相对论修正：高速接近时与经典公式出现可测偏差
        relative_speed = v_source - v_listener
        if abs(relative_speed) > 0.1 * speed_of_sound:
            beta = relative_speed / speed_of_sound
            relativistic = math.sqrt((1.0 + beta) / (1.0 - beta))
            classical = (speed_of_sound + v_listener) / (speed_of_sound - v_source)
            shifted = frequency * (classical + relativistic) / 2.0

        return max(shifted, 1.0)  # 限制：频率永不为负

    # ------------------------------------------------------------------
    # 音频流（Streaming）
    # ------------------------------------------------------------------

    def update_audio_stream(
        self,
        packets: List[Optional[bytes]],
        jitter: float = 0.0,
    ) -> Dict[str, Any]:
        """音频流更新。

        - 缓冲：抖动缓冲区吸收网络抖动，避免卡顿
        - 自适应：缓冲深度随网络抖动动态调整，兼顾延迟与稳定
        - 丢包补偿：丢包时重复上一帧（PLC），声音不直接断掉
        """
        buffer: List[bytes] = self.state.get("stream_buffer", [])
        last_frame: Optional[bytes] = self.state.get("stream_last_frame")

        # 自适应缓冲深度：抖动越大缓冲越深（限制在 1~10 帧）
        target_depth = max(1, min(10, 1 + int(jitter * 20)))

        frames: List[bytes] = []
        lost = 0
        for packet in packets:
            if packet is None:
                lost += 1
                if last_frame is not None:
                    frames.append(last_frame)  # 丢包补偿：重复上一帧
                continue
            buffer.append(packet)
            last_frame = packet
            while len(buffer) > target_depth:
                frames.append(buffer.pop(0))

        self.state.set("stream_buffer", buffer)
        self.state.set("stream_last_frame", last_frame)

        return {
            "frames": frames,
            "buffered": len(buffer),
            "target_depth": target_depth,
            "lost_packets": lost,
            "concealed": lost if last_frame is not None else 0,
        }
