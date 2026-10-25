import subprocess
import sys
import time
from datetime import datetime

SCRIPT = "gamma_cboe.py"
INTERVALO = 15        # minutos entre coletas
HORA_INI = 10.5       # 10:30 - abertura em horario de Brasilia
HORA_FIM = 17.0       # 17:00 - fechamento em horario de Brasilia
SO_EM_MERCADO = True  # False = coleta o dia inteiro


def mercado_aberto(agora):
    if agora.weekday() >= 5:      # 5 = sabado, 6 = domingo
        return False
    h = agora.hour + agora.minute / 60.0
    return HORA_INI <= h <= HORA_FIM


def falta_para_proximo(agora):
    passados = (agora.minute % INTERVALO) * 60 + agora.second
    resta = INTERVALO * 60 - passados
    return resta if resta > 10 else resta + INTERVALO * 60


def coletar():
    print("")
    print("=" * 56)
    print("coleta de", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 56)
    try:
        subprocess.run([sys.executable, SCRIPT], timeout=300)
    except Exception as e:
        print("erro na coleta (segue tentando):", e)


print("agendador ativo - coleta a cada", INTERVALO, "minutos")
if SO_EM_MERCADO:
    print("janela: dias de semana, de %.2fh as %.2fh" % (HORA_INI, HORA_FIM))
print("para parar, aperte CTRL+C")

while True:
    agora = datetime.now()
    if SO_EM_MERCADO and not mercado_aberto(agora):
        print(agora.strftime("%d/%m %H:%M"), "- mercado fechado, aguardando...")
        try:
            time.sleep(600)
        except KeyboardInterrupt:
            print("")
            print("encerrado.")
            break
        continue

    coletar()

    espera = falta_para_proximo(datetime.now())
    alvo = time.time() + espera
    print("")
    print("proxima coleta as", datetime.fromtimestamp(alvo).strftime("%H:%M:%S"))
    try:
        time.sleep(espera)
    except KeyboardInterrupt:
        print("")
        print("encerrado.")
        break
