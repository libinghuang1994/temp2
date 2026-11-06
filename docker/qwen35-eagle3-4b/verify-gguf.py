#!/usr/bin/env python3
"""Check every converted tensor and generate real-weight CPU RoPE fixtures."""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', type=Path)
    parser.add_argument('llama_source', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.llama_source / 'gguf-py'))
    from gguf import GGUFReader, GGMLQuantizationType
    torch.set_num_threads(2)
    bundle = args.bundle
    (bundle / 'verification').mkdir(exist_ok=True)
    reader = GGUFReader(bundle / 'gguf/Qwen3.5-4B-EAGLE3-F16.gguf')
    expected_meta = {
        'general.architecture': 'eagle3',
        'eagle3.block_count': 1,
        'eagle3.embedding_length': 2560,
        'eagle3.attention.head_count': 16,
        'eagle3.attention.head_count_kv': 4,
        'eagle3.attention.key_length': 160,
        'eagle3.rope.dimension_count': 40,
        'eagle3.rope.freq_base': 10000000.0,
        'eagle3.target_layers': [2, 16, 29],
    }
    for key, value in expected_meta.items():
        field = reader.get_field(key)
        assert field is not None and field.contents() == value, (key, field)
    assert len(reader.get_field('tokenizer.ggml.tokens').data) == 248320
    tensors = {t.name: t for t in reader.tensors}
    mapping = {
        'fc.weight': 'fc.weight',
        'lm_head.weight': 'output.weight',
        'norm.weight': 'output_norm.weight',
        'midlayer.hidden_norm.weight': 'blk.0.attn_norm_2.weight',
        'midlayer.input_layernorm.weight': 'blk.0.attn_norm.weight',
        'midlayer.post_attention_layernorm.weight': 'blk.0.ffn_norm.weight',
        'midlayer.self_attn.q_proj.weight': 'blk.0.attn_q.weight',
        'midlayer.self_attn.k_proj.weight': 'blk.0.attn_k.weight',
        'midlayer.self_attn.v_proj.weight': 'blk.0.attn_v.weight',
        'midlayer.self_attn.o_proj.weight': 'blk.0.attn_output.weight',
        'midlayer.mlp.gate_proj.weight': 'blk.0.ffn_gate.weight',
        'midlayer.mlp.up_proj.weight': 'blk.0.ffn_up.weight',
        'midlayer.mlp.down_proj.weight': 'blk.0.ffn_down.weight',
    }
    assert set(tensors) == set(mapping.values()) | {'d2t'}
    report = {'metadata': expected_meta, 'tensor_checks': {}, 'cpu_fixtures': []}
    rng = np.random.default_rng(20261106)
    with safe_open(bundle / 'original/model.safetensors', framework='pt', device='cpu') as sf:
        for name, dest in mapping.items():
            raw = sf.get_tensor(name).float().numpy()
            expected = raw
            heads = 16 if '.q_proj.' in name else 4 if '.k_proj.' in name else None
            if heads:
                # Independent explicit index map: first 40 rows/head only.
                order = np.arange(160)
                order[:40:2] = np.arange(20)
                order[1:40:2] = np.arange(20, 40)
                expected = raw.reshape(heads, 160, -1)[:, order].reshape(raw.shape)
            actual = tensors[dest].data
            assert actual.shape == expected.shape, (name, actual.shape, expected.shape)
            np.testing.assert_array_equal(actual, expected.astype(actual.dtype), err_msg=name)
            assert np.isfinite(actual).all(), name
            report['tensor_checks'][dest] = 'exact_match_after_declared_dtype_conversion'
            if heads:
                inp = rng.normal(0, 0.05, raw.shape[1]).astype(np.float32)
                projection = (raw @ inp).reshape(heads, 160)
                converted_projection = (actual.astype(np.float32) @ inp).reshape(heads, 160)
                np.testing.assert_allclose(converted_projection[:, 40:], projection[:, 40:], atol=1e-5)
                for pos in (0, 3, 127):
                    freq = 1.0 / (10000000.0 ** (np.arange(0, 40, 2, dtype=np.float64) / 40))
                    angle = pos * freq
                    c, s = np.cos(angle), np.sin(angle)
                    rotated = projection.copy()
                    rotated[:, :20] = projection[:, :20] * c - projection[:, 20:40] * s
                    rotated[:, 20:40] = projection[:, :20] * s + projection[:, 20:40] * c
                    expected_cpu = rotated[:, order].astype(np.float32)
                    name_bin = f'rope-{heads}heads-pos{pos}.bin'
                    path = bundle / 'verification' / name_bin
                    with path.open('wb') as f:
                        f.write(struct.pack('<iii', heads, 160, pos))
                        f.write(converted_projection.astype('<f4').tobytes())
                        f.write(expected_cpu.astype('<f4').tobytes())
                    report['cpu_fixtures'].append(name_bin)
        ids = sf.get_tensor('d2t').numpy() + np.arange(50000, dtype=np.int64)
        assert tensors['d2t'].tensor_type == GGMLQuantizationType.I64
        np.testing.assert_array_equal(tensors['d2t'].data, ids)
        np.testing.assert_array_equal(np.flatnonzero(sf.get_tensor('t2d').numpy()), ids)
        assert len(np.unique(ids)) == 50000 and ids.min() >= 0 and ids.max() < 248320
        report['draft_vocab_mapping'] = '50000_unique_absolute_ids_exactly_match_t2d_mask'
    (bundle / 'verification/gguf-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: all 14 GGUF tensors, metadata, tokenizer size, partial Q/K permutation, and vocabulary mapping')


if __name__ == '__main__':
    main()
