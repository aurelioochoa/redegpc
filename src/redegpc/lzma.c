/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
/* Keep liblzma's host ABI behind a small C boundary. */
#include <lzma.h>
#include <stddef.h>
#include <stdint.h>

int redegpc_decode_lzma(const uint8_t *input, size_t input_size,
                       uint8_t *output, size_t output_size, size_t *written) {
    lzma_stream stream = LZMA_STREAM_INIT;
    lzma_ret result = lzma_alone_decoder(&stream, 64 * 1024 * 1024);
    if (result != LZMA_OK)
        return (int)result;
    stream.next_in = input;
    stream.avail_in = input_size;
    stream.next_out = output;
    stream.avail_out = output_size;
    result = lzma_code(&stream, LZMA_FINISH);
    *written = (size_t)stream.total_out;
    lzma_end(&stream);
    return (int)result;
}
