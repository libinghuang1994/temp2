#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "ggml-alloc.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <vector>

static void require(bool ok, const char * message) {
    if (!ok) throw std::runtime_error(message);
}

int main(int argc, char ** argv) {
    try {
        require(argc >= 3, "usage: verify-cpu HEAD.gguf ROPE_FIXTURE...");
        llama_backend_init();
        auto params = llama_model_default_params();
        params.n_gpu_layers = 0;
        params.check_tensors = true;
        auto * model = llama_model_load_from_file(argv[1], params);
        require(model != nullptr, "head weight loading failed");
        require(llama_model_n_layer(model) == 1, "wrong layer count");
        require(llama_model_n_embd(model) == 2560, "wrong hidden size");
        require(llama_vocab_n_tokens(llama_model_get_vocab(model)) == 248320, "wrong vocab size");
        char value[128];
        require(llama_model_meta_val_str(model, "eagle3.rope.dimension_count", value, sizeof(value)) > 0, "missing RoPE dimension");
        require(std::string(value) == "40", "incorrect RoPE dimension");
        llama_model_free(model);
        std::puts("PASS: fixed llama.cpp loads and checks all EAGLE3 weights on CPU");

        auto * backend = ggml_backend_cpu_init();
        require(backend != nullptr, "CPU backend unavailable");
        ggml_backend_cpu_set_n_threads(backend, 2);
        for (int i = 2; i < argc; ++i) {
            std::ifstream f(argv[i], std::ios::binary);
            int32_t header[3];
            require(bool(f.read(reinterpret_cast<char *>(header), sizeof(header))), "bad fixture header");
            const int heads = header[0], dim = header[1], pos = header[2];
            require((heads == 4 || heads == 16) && dim == 160, "wrong fixture shape");
            std::vector<float> input(heads * dim), expected(heads * dim), result(heads * dim);
            require(bool(f.read(reinterpret_cast<char *>(input.data()), input.size() * sizeof(float))), "bad fixture input");
            require(bool(f.read(reinterpret_cast<char *>(expected.data()), expected.size() * sizeof(float))), "bad fixture expected output");
            ggml_init_params init = { 4 * 1024 * 1024, nullptr, true };
            auto * ctx = ggml_init(init);
            auto * x = ggml_new_tensor_3d(ctx, GGML_TYPE_F32, dim, heads, 1);
            auto * positions = ggml_new_tensor_1d(ctx, GGML_TYPE_I32, 1);
            auto * y = ggml_rope_ext(ctx, x, positions, nullptr, 40, GGML_ROPE_TYPE_NORMAL,
                                    262144, 10000000.0f, 1.0f, 0.0f, 1.0f, 0.0f, 0.0f);
            auto * graph = ggml_new_graph(ctx);
            ggml_build_forward_expand(graph, y);
            auto * allocator = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
            require(ggml_gallocr_alloc_graph(allocator, graph), "graph allocation failed");
            ggml_backend_tensor_set(x, input.data(), 0, input.size() * sizeof(float));
            ggml_backend_tensor_set(positions, &pos, 0, sizeof(pos));
            require(ggml_backend_graph_compute(backend, graph) == GGML_STATUS_SUCCESS, "CPU graph failed");
            ggml_backend_tensor_get(y, result.data(), 0, result.size() * sizeof(float));
            float max_error = 0;
            for (size_t j = 0; j < result.size(); ++j) {
                require(std::isfinite(result[j]), "nonfinite CPU result");
                max_error = std::max(max_error, std::abs(result[j] - expected[j]));
            }
            require(max_error < 3e-5f, "GGML CPU partial RoPE differs from training convention");
            std::printf("PASS: %s max_error=%g\n", argv[i], max_error);
            ggml_gallocr_free(allocator);
            ggml_free(ctx);
        }
        ggml_backend_free(backend);
        llama_backend_free();
        return 0;
    } catch (const std::exception & e) {
        std::fprintf(stderr, "FAIL: %s\n", e.what());
        return 1;
    }
}
