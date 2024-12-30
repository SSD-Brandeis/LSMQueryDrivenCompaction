#include "buffer.h"

Buffer::Buffer(const std::string &filename, size_t limit)
    : buffer_limit(limit) {
  output_file.open(filename, std::ios::out | std::ios::trunc);
  if (!output_file.is_open()) {
    throw std::runtime_error("Failed to open output file: " + filename);
  }
}

Buffer::~Buffer() {
  flush();
  if (output_file.is_open()) {
    output_file.close();
  }
}

Buffer &Buffer::operator<<(std::ostream &(*manip)(std::ostream &)) {
  buffer << manip;
  if (buffer.tellp() >= static_cast<std::streampos>(buffer_limit)) {
    flush();
  }
  return *this;
}

void Buffer::flush() {
  if (buffer.tellp() > 0) {
    output_file << buffer.str();
    output_file.flush();
    buffer.str("");
    buffer.clear();
  }
}
