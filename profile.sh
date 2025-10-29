#!/bin/bash
sudo sh -c 'echo 0 >/proc/sys/kernel/perf_event_paranoid'
sudo sh -c 'echo 0 >/proc/sys/kernel/kptr_restrict'

if [ ! -d ~/.local/bin/FlameGraph ]; then
  mkdir -p ~/.local/bin/
  git clone https://github.com/brendangregg/FlameGraph.git ~/.local/bin/FlameGraph --depth=1
fi

rm -f ./out.perf ./out.folded ./flamegraph.svg
perf record -F 999 -a -g  ./bin/working_version -E 1024 -I 10000 -U 5000 -S 200 -Y 0.1 --progress 1 -T 2 -P 64 -B 64
perf script > out.perf
~/.local/bin/FlameGraph/stackcollapse-perf.pl out.perf > out.folded
~/.local/bin/FlameGraph/flamegraph.pl out.folded > vanilla.svg


rm -f ./out.perf ./out.folded ./flamegraph.svg
perf record -F 999 -a -g  ./bin/working_version -E 1024 -I 10000 -U 5000 -S 200 -Y 0.1 --progress 1 -T 2 -P 64 -B 64 --rq 1 --lb 0.49
perf script > out.perf
~/.local/bin/FlameGraph/stackcollapse-perf.pl out.perf > out.folded
~/.local/bin/FlameGraph/flamegraph.pl out.folded > rangereduce.svg