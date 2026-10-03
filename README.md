# pairwise-audio-spatial-system

Bug修复项目：AudioSpatialSystem 存在多个严重bug，需要修复后让测试全部通过。

## 项目结构

- `audio/spatial.py`：核心模块（包含bug）
- `tests/test_audio_spatial.py`：验收测试

## 运行测试

```bash
python -m pytest tests/test_audio_spatial.py -q
```

## 要求

- 只使用Python标准库
- 不要修改测试文件
- 修复所有bug，让测试全部通过
