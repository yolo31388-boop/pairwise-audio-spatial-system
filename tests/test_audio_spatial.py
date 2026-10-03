"""
TestAudioSpatialSystem - 验收测试。

修复 AudioSpatialSystem 中的bug后，这些测试应该全部通过。
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio.spatial import AudioSpatialSystem, State


class TestAudioSpatialSystem:
    """AudioSpatialSystem 验收测试"""

    def setup_method(self):
        """每个测试前创建新实例"""
        self.system = AudioSpatialSystem()

    def test_initialize_sets_flag(self):
        """初始化后应该设置已初始化标志"""
        assert self.system._initialized == False
        result = self.system.initialize()
        assert result == True
        assert self.system._initialized == True

    def test_tick_increments_count(self):
        """tick应该增加计数"""
        self.system.initialize()
        assert self.system._tick_count == 0
        self.system.tick()
        assert self.system._tick_count == 1
        self.system.tick()
        assert self.system._tick_count == 2

    def test_tick_updates_timestamp(self):
        """tick应该更新时间戳"""
        self.system.initialize()
        assert self.system.timestamp == 0.0
        self.system.tick(1.5)
        assert self.system.timestamp == 1.5
        self.system.tick(2.5)
        assert self.system.timestamp == 4.0

    def test_state_set_get(self):
        """状态设置和获取"""
        self.system.state.set("key1", "value1")
        assert self.system.state.get("key1") == "value1"
        assert self.system.state.get("nonexistent", "default") == "default"

    def test_state_has(self):
        """状态存在检查"""
        assert self.system.state.has("key") == False
        self.system.state.set("key", 123)
        assert self.system.state.has("key") == True

    def test_get_state_returns_copy(self):
        """get_state应该返回副本，修改不影响内部"""
        self.system.state.set("test", 100)
        snapshot = self.system.get_state()
        snapshot["test"] = 999
        assert self.system.state.get("test") == 100

    def test_get_history_returns_copy(self):
        """get_history应该返回副本"""
        self.system.history.append({"event": "test"})
        history = self.system.get_history()
        history.append({"event": "extra"})
        assert len(self.system.history) == 1

    def test_reset_clears_state(self):
        """reset应该清除状态"""
        self.system.state.set("key", "value")
        self.system.history.append({"event": "test"})
        self.system._tick_count = 5
        self.system.reset()
        assert self.system.state.get("key") is None
        assert len(self.system.history) == 0
        assert self.system._tick_count == 0
        assert self.system._initialized == False

    def test_config_preserved(self):
        """配置应该被保留"""
        config = {"key": "value", "number": 42}
        system = AudioSpatialSystem(config)
        assert system.config == config

    def test_default_config(self):
        """默认配置应该是空字典"""
        assert self.system.config == {}

    def test_multiple_ticks(self):
        """多次tick应该正确累积"""
        self.system.initialize()
        for i in range(10):
            self.system.tick(0.5)
        assert self.system._tick_count == 10
        assert self.system.timestamp == 5.0

    def test_state_with_numeric_values(self):
        """状态支持数值类型"""
        self.system.state.set("int", 42)
        self.system.state.set("float", 3.14)
        self.system.state.set("bool", True)
        self.system.state.set("list", [1, 2, 3])
        self.system.state.set("dict", {"a": 1})
        assert self.system.state.get("int") == 42
        assert self.system.state.get("float") == 3.14
        assert self.system.state.get("bool") == True
        assert self.system.state.get("list") == [1, 2, 3]
        assert self.system.state.get("dict") == {"a": 1}

    def test_state_timestamp_updated(self):
        """State的timestamp应该在tick时更新"""
        self.system.initialize()
        assert self.system.state.timestamp == 0.0
        self.system.tick(2.0)
        assert self.system.state.timestamp == 2.0

    def test_initial_state_empty(self):
        """初始状态应该为空"""
        assert len(self.system.state.values) == 0
        assert len(self.system.history) == 0
        assert self.system._tick_count == 0
