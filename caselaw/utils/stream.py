import gzip
import io

def open_fast_gzip_lines(path):
    f = gzip.open(path, 'rb')  # binary mode
    buffered = io.BufferedReader(f, buffer_size=1024 * 1024)  # 1MB buffer
    # return io.TextIOWrapper(buffered, encoding='utf-8', errors='ignore')
    return io.TextIOWrapper(buffered, encoding='utf-8')


def stream_turtle_chunks(file_path):
    in_multiline_string = False
    buffer = []

    with open_fast_gzip_lines(file_path) as f:
        for line in f:
            buffer.append(line)

            # Count the number of triple quotes to toggle state
            triple_quote_count = line.count('"""') + line.count("'''")
            if triple_quote_count % 2 == 1:
                # Odd number of triple quotes in line - toggle state
                in_multiline_string = not in_multiline_string

            # if not in_multiline_string and line.strip().endswith('.'):
            if not in_multiline_string and len(line) > 1 and line[-2] == ".":
                chunk = ''.join(buffer)
                yield chunk
                buffer.clear()