import streamlit as st
from streamlit_autorefresh import st_autorefresh
import json
import os
import time

DATEI = "turnier_daten.json"


def lade_daten():
    if os.path.exists(DATEI):
        with open(DATEI, "r") as f:
            return json.load(f)
    return {}


def speichere_daten(daten):
    with open(DATEI, "w") as f:
        json.dump(daten, f, indent=4)


def is_valid_score(s1, s2, is_final=False):
    win_req = 4 if is_final else 3
    return (s1 == win_req and s2 < win_req) or (s2 == win_req and s1 < win_req)


st.set_page_config(page_title="Tischzuteilung", layout="wide")
daten = lade_daten()

if "tische" not in daten:
    daten["tische"] = {"Tisch 1": "Frei", "Tisch 2": "Frei", "Tisch 3": "Frei", "Tisch 4": "Frei"}

is_readonly = st.query_params.get("view") == "readonly"

# --- NEUER PASSWORT-SCHUTZ ---
if not is_readonly:
    if "admin_pw" not in st.session_state:
        st.session_state["admin_pw"] = ""

    eingabe = st.sidebar.text_input("🔒 Admin-Passwort", type="password", value=st.session_state["admin_pw"])
    st.session_state["admin_pw"] = eingabe

    if st.session_state["admin_pw"] != "tt2026":
        st.error("Zugriff verweigert. Bitte Admin-Passwort in der Seitenleiste eingeben.")
        st.info("Zuschauer? Hänge '?view=readonly' an die URL an.")
        st.stop()


# -----------------------------

# --- ALLE OFFENEN SPIELE SUCHEN ---
def hole_offene_spiele():
    offene = []

    for g_name, matches in daten.get("matches_einzel", {}).items():
        for m in matches:
            if len(m) >= 4 and not is_valid_score(m[2], m[3]):
                offene.append(f"Einzel Gruppe {g_name} | {m[0]} vs. {m[1]}")

    runden_e = daten.get("ko_einzel", {}).get("runden", [])
    use_bo7 = daten.get("use_bo7_final", True)
    for r_idx, runde in enumerate(runden_e):
        is_fin = (r_idx == len(runden_e) - 1) and len(runde) == 1
        for m in runde:
            if len(m) >= 4 and m[0] != "Freilos" and m[1] != "Freilos":
                if not is_valid_score(m[2], m[3], is_fin and use_bo7):
                    offene.append(f"Einzel KO-Runde {r_idx + 1} | {m[0]} vs. {m[1]}")

    p3 = daten.get("ko_einzel", {}).get("spiel_um_platz_3")
    if p3 and len(p3) >= 4 and not is_valid_score(p3[2], p3[3], use_bo7):
        offene.append(f"Einzel Platz 3 | {p3[0]} vs. {p3[1]}")

    doppel_keys = ["w1", "w2", "w3", "wf", "l1", "l2", "l3", "l4", "l5", "lf", "gf"]
    for key in doppel_keys:
        for m in daten.get("ko_doppel", {}).get(key, []):
            if len(m) >= 4 and m[0] != "Freilos" and m[1] != "Freilos":
                is_fin = (key == "gf")
                if not is_valid_score(m[2], m[3], False):
                    name = "Doppel Grand Final" if key == "gf" else f"Doppel {key.upper()}"
                    offene.append(f"{name} | {m[0]} vs. {m[1]}")

    return offene


offene_spiele = hole_offene_spiele()

# --- AUTO-FREE: BEENDETE SPIELE VON DEN TISCHEN WERFEN ---
tische_geändert = False
for t_name, aktuelles_spiel in daten["tische"].items():
    if aktuelles_spiel and aktuelles_spiel != "Frei" and aktuelles_spiel not in offene_spiele:
        daten["tische"][t_name] = "Frei"
        tische_geändert = True

if tische_geändert:
    speichere_daten(daten)

offene_spiele.insert(0, "Frei")

# ==========================================
# UI: ZUSCHAUER / TV MODUS
# ==========================================
if is_readonly:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            .big-table {font-size: 35px; font-weight: bold; background-color: #2e2e2e; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 20px;}
            .match-text {color: #4CAF50; font-size: 28px;}
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🏓 Live Tischübersicht</h1><hr>", unsafe_allow_html=True)

    # HTML-Fix: Im selben Tab öffnen
    st.markdown("<a href='/?view=readonly' target='_self'>👈 <b>🏆 Zurück zum Turnierbaum</b></a>",
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tische_items = list(daten.get("tische", {}).items())
    cols_count = 2 if len(tische_items) <= 6 else 3
    cols = st.columns(cols_count)

    for i, (t_name, m_name) in enumerate(tische_items):
        with cols[i % cols_count]:
            if not m_name or m_name == "Frei":
                m_name = "<span style='color: gray;'>Tisch frei</span>"
            else:
                m_name = f"<span class='match-text'>{m_name}</span>"
            st.markdown(f"<div class='big-table'>{t_name}<br>{m_name}</div>", unsafe_allow_html=True)

    st.info("🔄 Aktualisiert sich alle 10 Sekunden automatisch...")
    st_autorefresh(interval=10000, key="live_update")

# ==========================================
# UI: TURNIERLEITUNG (Admin)
# ==========================================
else:
    st.title("📋 Tischzuteilung (Admin)")
    st.write("Hier kannst du aktuell laufende Spiele den Tischen zuweisen.")

    aktuelle_anzahl = len(daten.get("tische", {}))
    neue_anzahl = st.number_input("Wie viele Tische stehen zur Verfügung?", min_value=1, max_value=16,
                                  value=max(1, aktuelle_anzahl))

    if neue_anzahl != aktuelle_anzahl:
        neue_tische = {}
        for i in range(1, neue_anzahl + 1):
            t_name = f"Tisch {i}"
            neue_tische[t_name] = daten.get("tische", {}).get(t_name, "Frei")
        daten["tische"] = neue_tische
        speichere_daten(daten)
        st.rerun()

    st.markdown("---")


    # --- KOLLISIONSPRÜFUNG: Welche Spieler sind gerade an anderen Tischen aktiv? ---
    def get_busy_players(current_tisch):
        busy = set()
        for t_name, m_str in daten["tische"].items():
            if t_name != current_tisch and m_str and m_str != "Frei":
                try:
                    p_teil = m_str.split(" | ")[-1]
                    p1, p2 = p_teil.split(" vs. ")

                    # Wenn es ein Doppel ist, am "&" auftrennen
                    for p in [p1.strip(), p2.strip()]:
                        if " & " in p:
                            busy.update([sp.strip() for sp in p.split(" & ")])
                        else:
                            busy.add(p)
                except:
                    pass
        return busy


    # Breiteres Layout (2 Spalten statt 4)
    cols = st.columns(2)
    changed = False

    for idx, (tisch_name, aktuelles_spiel) in enumerate(daten["tische"].items()):
        with cols[idx % 2]:
            st.markdown(f"### {tisch_name}")

            # Spieler blockieren, die woanders spielen
            busy_players = get_busy_players(tisch_name)
            erlaubte_spiele = ["Frei"]

            for m_str in offene_spiele:
                if m_str == "Frei": continue
                if m_str == aktuelles_spiel:
                    erlaubte_spiele.append(m_str)
                    continue

                try:
                    p_teil = m_str.split(" | ")[-1]
                    p1, p2 = p_teil.split(" vs. ")

                    # Die Spieler des potenziellen Matches aufsplitten (falls Doppel)
                    match_players = set()
                    for p in [p1.strip(), p2.strip()]:
                        if " & " in p:
                            match_players.update([sp.strip() for sp in p.split(" & ")])
                        else:
                            match_players.add(p)

                    # Spiel nur erlauben, wenn KEIN EINZIGER der Spieler am Tisch busy ist
                    if match_players.isdisjoint(busy_players):
                        erlaubte_spiele.append(m_str)
                except:
                    erlaubte_spiele.append(m_str)

            index = erlaubte_spiele.index(aktuelles_spiel) if aktuelles_spiel in erlaubte_spiele else 0

            neu_spiel = st.selectbox("Spiel", erlaubte_spiele, index=index, key=f"sel_{tisch_name}",
                                     label_visibility="collapsed")
            if neu_spiel != aktuelles_spiel:
                daten["tische"][tisch_name] = neu_spiel
                changed = True

    if changed:
        speichere_daten(daten)
        st.rerun()

    st.markdown("---")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🔄 Ansicht aktualisieren"): st.rerun()
    with c2:
        if st.button("🧹 Alle Tische auf 'Frei' setzen"):
            for t in daten["tische"]: daten["tische"][t] = "Frei"
            speichere_daten(daten)
            st.rerun()

    st.write(f"**Verbleibende offene Spiele insgesamt:** {len(offene_spiele) - 1}")