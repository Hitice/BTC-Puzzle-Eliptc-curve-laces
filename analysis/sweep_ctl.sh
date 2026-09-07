#!/bin/zsh
# Controle das filas de varredura. Uso: ./analysis/sweep_ctl.sh {status|pause|resume|stop|nice}
#
# pause  = SIGSTOP: congela tudo, nao perde progresso, libera a maquina na hora
# resume = SIGCONT: retoma exatamente de onde parou
# stop   = mata as filas (o item em andamento perde o progresso; os JSON ja
#          gravados em analysis/sweeps/ continuam validos)
# nice   = rebaixa a prioridade de tudo que estiver rodando

pids() {
  local out=""
  for d in $(pgrep -f "run_sweeps"); do out="$out $d"; done
  for d in $(pgrep -f "master_seed_sweep"); do
    out="$out $d $(ps -Ao pid,ppid | awk -v p=$d '$2==p {print $1}')"
  done
  echo $out
}

case "$1" in
  status)
    P=$(pids)
    if [[ -z "${P// }" ]]; then echo "nenhuma fila rodando"; exit 0; fi
    ps -o pid,stat,nice,%cpu,etime -p ${P// /,} 2>/dev/null
    for f in analysis/sweeps/run.log analysis/sweeps/run-h2.log; do
      [[ -f $f ]] && echo "\n$f: $(tr '\r' '\n' < $f | tail -1)"
    done
    ;;
  pause)  for p in $(pids); do kill -STOP $p 2>/dev/null; done; echo "congelado (SIGSTOP). retome com: $0 resume" ;;
  resume) for p in $(pids); do kill -CONT $p 2>/dev/null; done; echo "retomado (SIGCONT)" ;;
  stop)   pkill -f run_sweeps; pkill -f master_seed_sweep; echo "filas encerradas" ;;
  nice)   for p in $(pids); do renice 20 -p $p >/dev/null 2>&1; done; echo "prioridade rebaixada" ;;
  *) echo "uso: $0 {status|pause|resume|stop|nice}"; exit 1 ;;
esac
