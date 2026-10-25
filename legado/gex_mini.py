import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.gexmetrix.com/gamma_dashboard"
SIMBOLO = "SPX"          # troque por SPY, NDX, QQQ ou VIX se quiser

TAB = chr(9)

CAMPOS = ["Data Timestamp", "Spot Price", "Call Gamma", "Zero Gamma",
          "Total Vol", "Vol P/C Ratio", "Exp Dates", "Total Gamma",
          "Put Gamma", "Max Pain", "Total OI", "OI P/C Ratio"]

CHAVES = ["Spot Price", "Total Gamma", "Zero Gamma", "Max Pain"]
VAZIOS = ("N/A", "NA", "-", "", "LOADING...", "LOADING")

LIMITE = 60
PASSO = 5


def limpar(v):
    v = v.strip()
    corte = v.find("   ")
    if corte > 0:
        v = v[:corte]
    return v.strip()


def extrair(texto):
    out = {}
    for linha in texto.splitlines():
        for parte in linha.split(TAB):
            if ":" not in parte:
                continue
            nome, valor = parte.split(":", 1)
            nome = nome.strip()
            if nome in CAMPOS and nome not in out:
                out[nome] = limpar(valor)
    return out


def tem_dado(vals):
    for k in CHAVES:
        v = vals.get(k, "")
        if v.upper() in VAZIOS:
            continue
        for ch in v:
            if ch.isdigit():
                return True
    return False


def fechar_popups(pg):
    alvos = ["button[aria-label='Close']", "button[aria-label='close']",
             ".modal .close", ".close-button", "#closeModal", ".banner-close",
             "text=" + chr(215), "text=" + chr(10005)]
    for sel in alvos:
        try:
            el = pg.locator(sel).first
            if el.is_visible(timeout=500):
                el.click(timeout=1000)
                print("   fechei popup:", sel)
                pg.wait_for_timeout(400)
        except Exception:
            pass
    try:
        pg.keyboard.press("Escape")
    except Exception:
        pass


def escolher(pg, simbolo):
    # tentativa 1: select nativo do HTML
    try:
        sels = pg.locator("select")
        for i in range(sels.count()):
            s = sels.nth(i)
            ops = s.locator("option")
            for j in range(ops.count()):
                t = (ops.nth(j).inner_text() or "").strip().upper()
                if t.startswith(simbolo):
                    s.select_option(index=j)
                    return "select nativo (opcao " + str(j) + ")"
    except Exception:
        pass

    # tentativa 2: abrir o combobox e clicar na opcao
    for abrir in ["[role=combobox]", ".select2-selection", ".dropdown-toggle",
                  "text=Loading Instruments"]:
        try:
            el = pg.locator(abrir).first
            if el.is_visible(timeout=500):
                el.click(timeout=1000)
                pg.wait_for_timeout(800)
                op = pg.get_by_text(simbolo + " (", exact=False).first
                if op.is_visible(timeout=1000):
                    op.click(timeout=1000)
                    return "combobox " + abrir
        except Exception:
            pass

    # tentativa 3: digitar no campo de busca
    for cx in ["input[placeholder*=symbol i]", "input[placeholder*=Type i]",
               "input[type=search]", "input[type=text]"]:
        try:
            el = pg.locator(cx).first
            if el.is_visible(timeout=500):
                el.click(timeout=1000)
                el.fill(simbolo)
                pg.wait_for_timeout(1500)
                pg.keyboard.press("Enter")
                return "campo de busca " + cx
        except Exception:
            pass

    return ""


print("abrindo o site...")
with sync_playwright() as p:
    nav = p.chromium.launch(headless=False)
    ctx = nav.new_context(viewport={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    pg.goto(URL, timeout=60000)
    pg.wait_for_timeout(5000)

    fechar_popups(pg)

    via = escolher(pg, SIMBOLO)
    if via:
        print("   selecionei", SIMBOLO, "via:", via)
    else:
        print("   NAO consegui selecionar automaticamente")

    esperou = 0
    while esperou <= LIMITE:
        if tem_dado(extrair(pg.inner_text("body"))):
            print("   dados chegaram em", esperou, "segundos")
            break
        print("   esperando dados... (" + str(esperou) + "s)")
        pg.wait_for_timeout(PASSO * 1000)
        esperou = esperou + PASSO

    if not tem_dado(extrair(pg.inner_text("body"))):
        print("")
        print("-----------------------------------------------------")
        print("MODO MANUAL: escolha " + SIMBOLO + " na janela do Chrome agora.")
        print("Depois volte aqui e aperte ENTER.")
        print("-----------------------------------------------------")
        try:
            input()
        except Exception:
            pass
        pg.wait_for_timeout(3000)

    texto = pg.inner_text("body")
    try:
        pg.screenshot(path="tela.png", full_page=True)
    except Exception:
        pass
    nav.close()

with open("pagina.txt", "w", encoding="utf-8") as f:
    f.write(texto)

vals = extrair(texto)
ts = datetime.now().strftime("%Y-%m-%d %H:%M")
print("")
print(ts)
for k in CAMPOS:
    if k in vals:
        print("  %-16s %s" % (k, vals[k]))

if tem_dado(vals):
    with open("gamma.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for k, v in vals.items():
            w.writerow([ts, SIMBOLO, k, v])
    print("")
    print("GRAVADO em gamma.csv")
else:
    print("")
    print("ainda sem dados - me mande pagina.txt e tela.png")

print("tamanho do texto:", len(texto), "caracteres")
