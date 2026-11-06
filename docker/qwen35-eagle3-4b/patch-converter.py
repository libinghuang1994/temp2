#!/usr/bin/env python3
"""Patch only the pinned converter for this BF16 partial-RoPE EAGLE3 head."""
import hashlib
import sys
from pathlib import Path


def main():
    source = Path(sys.argv[1]) / 'conversion/llama.py'
    text = source.read_text()
    expected = Path(__file__).with_name('sources.json')
    import json
    before = json.loads(expected.read_text())['converter_original_sha256']
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise SystemExit('Refusing to patch a modified or different llama.py')
    changes = [
        (
            '        self.gguf_writer.add_rope_dimension_count(rope_dim)\n',
            '        if getattr(self, "is_eagle3", False):\n'
            '            rope_dim = int(rope_dim * hparams.get("partial_rotary_factor", 1.0))\n'
            '        self.gguf_writer.add_rope_dimension_count(rope_dim)\n',
        ),
        (
            '    def permute(weights: Tensor, n_head: int, n_head_kv: int | None):\n'
            '        if n_head_kv is not None and n_head != n_head_kv:\n'
            '            n_head = n_head_kv\n'
            '        return (weights.reshape(n_head, 2, weights.shape[0] // n_head // 2, *weights.shape[1:])\n'
            '                .swapaxes(1, 2)\n'
            '                .reshape(weights.shape))\n',
            '    def permute(weights: Tensor, n_head: int, n_head_kv: int | None, n_rot: int | None = None):\n'
            '        if n_head_kv is not None and n_head != n_head_kv:\n'
            '            n_head = n_head_kv\n'
            '        head_dim = weights.shape[0] // n_head\n'
            '        n_rot = head_dim if n_rot is None else n_rot\n'
            '        if n_rot <= 0 or n_rot > head_dim or n_rot % 2:\n'
            '            raise ValueError("Invalid partial RoPE dimension")\n'
            '        heads = weights.reshape(n_head, head_dim, *weights.shape[1:])\n'
            '        rotated = (heads[:, :n_rot].reshape(n_head, 2, n_rot // 2, *weights.shape[1:])\n'
            '                   .swapaxes(1, 2).reshape(n_head, n_rot, *weights.shape[1:]))\n'
            '        return torch.cat((rotated, heads[:, n_rot:]), dim=1).reshape(weights.shape)\n',
        ),
        (
            '        if self.undo_permute:\n'
            '            if name.endswith(("q_proj.weight", "q_proj.bias")):\n'
            '                data_torch = LlamaModel.permute(data_torch, n_head, n_head)\n'
            '            if name.endswith(("k_proj.weight", "k_proj.bias")):\n'
            '                data_torch = LlamaModel.permute(data_torch, n_head, n_kv_head)\n',
            '        if self.undo_permute:\n'
            '            n_rot = None\n'
            '            if getattr(self, "is_eagle3", False):\n'
            '                head_dim = self.hparams.get("head_dim", self.hparams["hidden_size"] // n_head)\n'
            '                n_rot = int(head_dim * self.hparams.get("partial_rotary_factor", 1.0))\n'
            '            if name.endswith(("q_proj.weight", "q_proj.bias")):\n'
            '                data_torch = LlamaModel.permute(data_torch, n_head, n_head, n_rot)\n'
            '            if name.endswith(("k_proj.weight", "k_proj.bias")):\n'
            '                data_torch = LlamaModel.permute(data_torch, n_head, n_kv_head, n_rot)\n',
        ),
    ]
    for old, new in changes:
        if text.count(old) != 1:
            raise SystemExit('Pinned converter patch anchor mismatch')
        text = text.replace(old, new)
    source.write_text(text)
    print('Patched partial RoPE metadata and Q/K row permutation; target layers unchanged')


if __name__ == '__main__':
    main()
