import streamlit as st
import json
import os
import random
import time
import itertools
import copy

# ==========================================
# 1. KONFIGURATION & DATENVERWALTUNG
# ==========================================
DATEI = "turnier_daten.json"


def lade_daten():
    if os.path.exists(DATEI):
        with open(DATEI, "r") as f:
            return json.load(f)
    return {
        "spieler": {}, "doppel": [], "gruppen": {},
        "matches_einzel": {}, "turnier_gestartet": False,
        "gruppen_beendet": False, "ko_einzel": {"runden": [], "spiel_um_platz_3": None},
        "ko_doppel": {"w1": [], "phase": 1, "baum_typ": 8},
        "turnier_eingefroren": False
    }


def speichere_daten(daten):
    with open(DATEI, "w") as f:
        json.dump(daten, f, indent=4)


def get_power_of_two(n):
    if n <= 2: return 2
    if n <= 4: return 4
    if n <= 8: return 8
    if n <= 16: return 16
    return 32


def is_valid_score(s1, s2, is_final=False):
    win_req = 4 if is_final else 3
    return (s1 == win_req and s2 < win_req) or (s2 == win_req and s1 < win_req)


# ==========================================
# 2. SEITEN-SETUP, READONLY & SIDEBAR
# ==========================================
dev_mode = False
st.set_page_config(page_title="Turnier Manager", layout="wide")

is_readonly = st.query_params.get("view") == "readonly"

# --- NEUER PASSWORT-SCHUTZ ---
if not is_readonly:
    pwd = st.sidebar.text_input("🔒 Admin-Passwort", type="password")
    if pwd != "tt2026":  # <-- Hier dein gewünschtes Passwort eintragen
        st.error("Zugriff verweigert. Bitte Admin-Passwort in der Seitenleiste eingeben.")
        st.info("Zuschauer? Hänge '?view=readonly' an die URL an.")
        st.stop()
# -----------------------------

if is_readonly:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    st.info("👁️ **Zuschauer-Modus:** Ergebnisse werden live angezeigt. Bearbeitung ist deaktiviert.")
    st.markdown("<a href='tische?view=readonly' target='_self'>👉 <b>📺 Zum Live-Tisch-Dashboard wechseln</b></a>", unsafe_allow_html=True)

daten = lade_daten()
is_locked = daten.get("turnier_gestartet", False)
is_frozen = daten.get("turnier_eingefroren", False)
ui_disabled = is_frozen or is_readonly

if not is_readonly:
    with st.sidebar:
        dev_mode = st.checkbox("🛠️ Dev-Modus")
        if dev_mode and not is_frozen:
            st.warning("Dev-Modus aktiv: Gesperrte Runden bearbeitbar!")
            if st.button("🎲 Einzel-Gruppen auf 3:0 setzen"):
                if not daten["gruppen_beendet"]:
                    for g_name, matches in daten["matches_einzel"].items():
                        for idx, m in enumerate(matches):
                            if len(m) < 4:
                                daten["matches_einzel"][g_name][idx] = [m[0], m[1], 3, 0]
                            else:
                                daten["matches_einzel"][g_name][idx][2] = 3
                                daten["matches_einzel"][g_name][idx][3] = 0
                            st.session_state[f"e_s1_{g_name}_{idx}"] = 3
                            st.session_state[f"e_s2_{g_name}_{idx}"] = 0
                speichere_daten(daten)
                st.rerun()

st.title("🏓 Tischtennis Vereinsmeisterschaft")

tab1, tab2, tab3 = st.tabs(["👥 Spieler", "🤝 Doppel", "🏆 Spiele"])

# ==========================================
# 3. TAB 1: SPIELER REGISTRIERUNG
# ==========================================
with tab1:
    st.subheader("Spieler Registrierung")
    if is_locked or is_readonly:
        st.warning("🔒 Registrierung ist gesperrt.")
        st.write(f"**Registriert ({len(daten['spieler'])}):**")
        for name in daten["spieler"].keys():
            st.write(f"- {name}")
    else:
        with st.form("neuer_spieler_form", clear_on_submit=True):
            neuer_spieler = st.text_input("Spielername eingeben:")
            submitted = st.form_submit_button("Hinzufügen")
            if submitted and neuer_spieler:
                if neuer_spieler == "TEST10":
                    for i in range(1, 11): daten["spieler"][f"Spieler {i}"] = {"einzel": True, "doppel": True,
                                                                               "kopf": (i <= 2),
                                                                               "staerke": "stark" if i <= 5 else "schwach"}
                    speichere_daten(daten);
                    st.rerun()
                elif neuer_spieler == "TEST18":
                    for i in range(1, 19): daten["spieler"][f"Spieler {i}"] = {"einzel": True, "doppel": True,
                                                                               "kopf": (i <= 4),
                                                                               "staerke": "stark" if i <= 9 else "schwach"}
                    speichere_daten(daten);
                    st.rerun()
                elif neuer_spieler not in daten["spieler"]:
                    daten["spieler"][neuer_spieler] = {"einzel": True, "doppel": True, "kopf": False,
                                                       "staerke": "stark"}
                    speichere_daten(daten);
                    st.rerun()

        st.write(f"**Registriert ({len(daten['spieler'])}):**")
        for name, info in list(daten["spieler"].items()):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            with col1:
                st.write(name)
            with col2:
                info["einzel"] = st.checkbox("E", value=info["einzel"], key=f"e_{name}")
            with col3:
                info["doppel"] = st.checkbox("D", value=info["doppel"], key=f"d_{name}")
            with col4:
                info["kopf"] = st.checkbox("K", value=info["kopf"], key=f"k_{name}")
            with col5:
                if st.button("❌", key=f"del_{name}"):
                    del daten["spieler"][name];
                    speichere_daten(daten);
                    st.rerun()
        speichere_daten(daten)

# ==========================================
# 4. TAB 2: DOPPEL SETUP & AUSLOSUNG
# ==========================================
with tab2:
    st.subheader("Doppel Setup & Auslosung")
    if is_locked or is_readonly:
        st.warning("🔒 Das Doppel-Setup ist gesperrt.")
        if daten.get("doppel"):
            st.success("Die Doppel stehen fest:")
            for team in daten["doppel"]: st.info(team)
    else:
        doppel_spieler = [name for name, info in daten["spieler"].items() if info["doppel"]]
        if not doppel_spieler:
            st.info("Noch keine Spieler für das Doppel markiert.")
        else:
            starke = [n for n in doppel_spieler if daten["spieler"][n].get("staerke", "stark") == "stark"]
            schwache = [n for n in doppel_spieler if daten["spieler"][n].get("staerke", "stark") == "schwach"]

            st.write(f"**Teilnehmer Doppel: {len(doppel_spieler)} | Stark: {len(starke)} | Schwach: {len(schwache)}**")
            st.markdown("---")

            col_links, col_rechts = st.columns(2)
            with col_links:
                st.markdown("### 💪 Stark")
                for name in starke:
                    c_name, c_btn = st.columns([4, 1])
                    c_name.write(name)
                    if c_btn.button("➡️", key=f"r_{name}"):
                        daten["spieler"][name]["staerke"] = "schwach";
                        speichere_daten(daten);
                        st.rerun()
            with col_rechts:
                st.markdown("### 🐣 Schwach")
                for name in schwache:
                    c_btn, c_name = st.columns([1, 4])
                    if c_btn.button("⬅️", key=f"l_{name}"):
                        daten["spieler"][name]["staerke"] = "stark";
                        speichere_daten(daten);
                        st.rerun()
                    c_name.write(name)

            st.markdown("---")
            if len(starke) != len(schwache):
                st.error("⚠️ Die Anzahl der Spieler in 'Stark' und 'Schwach' muss exakt gleich sein für die Auslosung!")
            elif len(doppel_spieler) > 0:
                if st.button("Doppel-Partner zulosen"):
                    random.shuffle(starke);
                    random.shuffle(schwache)
                    daten["doppel"] = [f"{starke.pop()} & {schwache.pop()}" for _ in range(len(starke))]
                    speichere_daten(daten);
                    st.balloons();
                    st.rerun()

            if daten.get("doppel"):
                st.success("Die Doppel stehen fest:")
                for team in daten["doppel"]: st.info(team)

# ==========================================
# 5. TAB 3: TURNIERBAUM & ERGEBNISSE
# ==========================================
with tab3:
    st.subheader("Turnierbaum & Ergebnisse")

    if not is_locked:
        if not is_readonly:
            einzel_spieler = [n for n, info in daten["spieler"].items() if info["einzel"]]
            koepfe = [n for n in einzel_spieler if daten["spieler"][n].get("kopf")]
            calc_gruppen = max(1, round(len(einzel_spieler) / 4.5)) if einzel_spieler else 1
            anzahl_gruppen = st.number_input("Anzahl der Gruppen festlegen:", min_value=1, max_value=10,
                                             value=calc_gruppen)
            use_bo7_final = st.checkbox("Finalspiele im Einzel (Finale & Platz 3) als Best-of-7 spielen", value=True)

            if len(einzel_spieler) > 0:
                if len(koepfe) != anzahl_gruppen:
                    st.error(f"Fehler: Markiere exakt {anzahl_gruppen} Gruppenköpfe.")
                elif not daten.get("doppel"):
                    st.error("Fehler: Bitte lose zuerst die Doppel aus!")
                else:
                    if st.button("🚨 Registrierung abschließen & Turnier starten"):
                        rest = [n for n in einzel_spieler if not daten["spieler"][n].get("kopf")]
                        random.shuffle(koepfe);
                        random.shuffle(rest)

                        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        gruppen = {alphabet[i]: [] for i in range(anzahl_gruppen)}
                        gruppen_namen = list(gruppen.keys())

                        for i, kopf in enumerate(koepfe): gruppen[gruppen_namen[i]].append(kopf)
                        for i, spieler in enumerate(rest): gruppen[gruppen_namen[i % anzahl_gruppen]].append(spieler)

                        daten["gruppen"] = gruppen
                        daten["matches_einzel"] = {}
                        for g_name, spieler_liste in gruppen.items():
                            match_kombis = list(itertools.combinations(spieler_liste, 2))
                            daten["matches_einzel"][g_name] = [[m[0], m[1], 0, 0] for m in match_kombis]

                        d_teams = daten["doppel"].copy()
                        random.shuffle(d_teams)

                        baum_typ = 16 if len(d_teams) > 8 else 8
                        slots = baum_typ
                        w1_matches = [["Freilos", "Freilos", 0, 0] for _ in range(slots // 2)]
                        for idx, team in enumerate(d_teams):
                            match_idx = idx % (slots // 2)
                            pos_idx = idx // (slots // 2)
                            w1_matches[match_idx][pos_idx] = team

                        daten["ko_doppel"] = {"phase": 1, "baum_typ": baum_typ, "w1": w1_matches}
                        daten["use_bo7_final"] = use_bo7_final
                        daten["turnier_gestartet"] = True
                        speichere_daten(daten);
                        st.rerun()
    else:
        einzel_fertig = False
        runden = daten["ko_einzel"].get("runden", [])
        if runden and len(runden[-1]) == 1 and len(runden[-1][0]) >= 4 and is_valid_score(runden[-1][0][2],
                                                                                          runden[-1][0][3],
                                                                                          daten.get("use_bo7_final",
                                                                                                    True)):
            p3 = daten["ko_einzel"].get("spiel_um_platz_3")
            if not p3 or (len(p3) >= 4 and is_valid_score(p3[2], p3[3],
                                                          daten.get("use_bo7_final", True))): einzel_fertig = True

        doppel_fertig = False
        gf = daten["ko_doppel"].get("gf", [])
        if gf and len(gf[0]) >= 4 and is_valid_score(gf[0][2], gf[0][3], False):
            if len(gf) == 1 or (len(gf[1]) >= 4 and is_valid_score(gf[1][2], gf[1][3], False)): doppel_fertig = True

        tab_list = ["🏓 Einzel", "🤝 Doppel"]
        if einzel_fertig or doppel_fertig: tab_list.append("🥇 Siegerehrung")

        tabs = st.tabs(tab_list)
        t_einzel = tabs[0];
        t_doppel = tabs[1];
        t_sieger = tabs[2] if (einzel_fertig or doppel_fertig) else None

        # ==========================================
        # EINZEL LOGIK
        # ==========================================
        with t_einzel:
            if not daten.get("gruppen_beendet"):
                alle_spiele_gueltig = True
                gruppen_ergebnisse = {}

                for g_name, matches in daten["matches_einzel"].items():
                    with st.expander(f"Gruppe {g_name}", expanded=True):
                        stats = {s: {"wins": 0, "diff": 0, "spiele": 0} for s in daten["gruppen"][g_name]}

                        for idx, match in enumerate(matches):
                            if len(match) < 4: daten["matches_einzel"][g_name][idx] = [match[0], match[1], 0,
                                                                                       0]; match = \
                            daten["matches_einzel"][g_name][idx]
                            p1, p2, s1, s2 = match
                            if is_valid_score(s1, s2):
                                stats[p1]["spiele"] += 1;
                                stats[p2]["spiele"] += 1
                                stats[p1]["diff"] += (s1 - s2);
                                stats[p2]["diff"] += (s2 - s1)
                                if s1 > s2:
                                    stats[p1]["wins"] += 1
                                else:
                                    stats[p2]["wins"] += 1
                            else:
                                alle_spiele_gueltig = False

                        tabelle_keys = sorted(stats.keys(), key=lambda x: (stats[x]["wins"], stats[x]["diff"]),
                                              reverse=True)
                        gruppen_ergebnisse[g_name] = tabelle_keys

                        c_platz, c_name, c_spiele, c_siege, c_diff, c_status = st.columns([1, 4, 2, 2, 2, 2])
                        c_platz.write("**#**");
                        c_name.write("**Spieler**");
                        c_spiele.write("**Spiele**");
                        c_siege.write("**Siege**");
                        c_diff.write("**Diff**");
                        c_status.write("**Status**")

                        for idx, spieler in enumerate(tabelle_keys):
                            data = stats[spieler]
                            c_platz, c_name, c_spiele, c_siege, c_diff, c_status = st.columns([1, 4, 2, 2, 2, 2])
                            c_platz.write(f"{idx + 1}.");
                            c_name.write(spieler);
                            c_spiele.write(str(data["spiele"]));
                            c_siege.write(str(data["wins"]));
                            c_diff.write(f"{data['diff']:+d}")
                            if idx < 2:
                                c_status.success("Weiter")
                            else:
                                c_status.error("Raus")

                        st.markdown("---")
                        for idx, match in enumerate(matches):
                            p1, p2, s1, s2 = match
                            p1_disp, p2_disp = p1, p2
                            if is_valid_score(s1, s2):
                                if s1 > s2:
                                    p1_disp, p2_disp = f"🟢 {p1}", f"🔴 {p2}"
                                else:
                                    p1_disp, p2_disp = f"🔴 {p1}", f"🟢 {p2}"

                            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                            c1.write(f"**{p1_disp}**")
                            new_s1 = c2.number_input("Satz", min_value=0, max_value=5, value=s1, key=f"e_s1_{g_name}_{idx}",
                                                     label_visibility="collapsed", disabled=ui_disabled)
                            c3.markdown("<div style='text-align: center; font-weight: bold;'>:</div>",
                                        unsafe_allow_html=True)
                            new_s2 = c4.number_input("Satz", min_value=0, max_value=5, value=s2, key=f"e_s2_{g_name}_{idx}",
                                                     label_visibility="collapsed", disabled=ui_disabled)
                            c5.write(f"**{p2_disp}**")

                            if new_s1 != s1 or new_s2 != s2:
                                daten["matches_einzel"][g_name][idx][2] = new_s1
                                daten["matches_einzel"][g_name][idx][3] = new_s2
                                speichere_daten(daten);
                                st.rerun()

                if alle_spiele_gueltig and not ui_disabled:
                    if "confirm_grp" not in st.session_state: st.session_state["confirm_grp"] = False
                    if not st.session_state["confirm_grp"]:
                        if st.button("✅ Alle Gruppen abschließen & KO-Runde generieren", type="primary"):
                            st.session_state["confirm_grp"] = True;
                            st.rerun()
                    else:
                        st.warning("Bist du sicher? Die Gruppenphase wird hart abgeschlossen.")
                        c_y, c_n = st.columns(2)
                        if c_y.button("✅ Ja, abschließen", type="primary", key="grp_y"):
                            st.session_state["confirm_grp"] = False
                            erstplatzierte = [gruppen_ergebnisse[g][0] for g in daten["gruppen"].keys() if
                                              len(gruppen_ergebnisse[g]) > 0]
                            zweitplatzierte = [gruppen_ergebnisse[g][1] for g in daten["gruppen"].keys() if
                                               len(gruppen_ergebnisse[g]) > 1]
                            alle_weiter = erstplatzierte + zweitplatzierte
                            ko_slots = get_power_of_two(len(alle_weiter))
                            for i in range(ko_slots - len(alle_weiter)): zweitplatzierte.append("Freilos")

                            runde_1 = []
                            zweitplatzierte.reverse()
                            for i in range(len(erstplatzierte)): runde_1.append(
                                [erstplatzierte[i], zweitplatzierte[i], 0, 0])
                            while len(runde_1) < (ko_slots // 2): runde_1.append(["Freilos", "Freilos", 0, 0])

                            daten["ko_einzel"]["runden"] = [runde_1]
                            daten["gruppen_beendet"] = True
                            speichere_daten(daten);
                            st.rerun()
                        if c_n.button("❌ Abbrechen", key="grp_n"):
                            st.session_state["confirm_grp"] = False;
                            st.rerun()

            else:
                st.success("Gruppenphase abgeschlossen!")
                runden = daten["ko_einzel"]["runden"]
                use_bo7 = daten.get("use_bo7_final", True)

                for r_idx, runde in enumerate(runden):
                    is_final = (r_idx == len(runden) - 1) and len(runde) == 1
                    r_name = (
                        "🥇 Finale (Best-of-7)" if use_bo7 else "🥇 Finale (Best-of-5)") if is_final else f"KO-Runde {r_idx + 1} (Best-of-5)"
                    is_locked_round = ((not dev_mode) and (r_idx < len(runden) - 1)) or ui_disabled

                    with st.expander(f"{r_name}" + (" 🔒" if is_locked_round else ""), expanded=True):
                        runde_gueltig = True
                        for m_idx, match in enumerate(runde):
                            if len(match) < 4: daten["ko_einzel"]["runden"][r_idx][m_idx] = [match[0], match[1], 0,
                                                                                             0]; match = \
                            daten["ko_einzel"]["runden"][r_idx][m_idx]
                            p1, p2, s1, s2 = match
                            if p1 == "Freilos" or p2 == "Freilos": st.info(
                                f"🟢 **{p1 if p2 == 'Freilos' else p2}** (Freilos)"); continue

                            p1_disp, p2_disp = p1, p2
                            if is_valid_score(s1, s2, is_final and use_bo7):
                                if s1 > s2:
                                    p1_disp, p2_disp = f"🟢 {p1}", f"🔴 {p2}"
                                else:
                                    p1_disp, p2_disp = f"🔴 {p1}", f"🟢 {p2}"
                            else:
                                runde_gueltig = False

                            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                            c1.write(f"**{p1_disp}**")
                            max_s = 7 if (is_final and use_bo7) else 5
                            new_s1 = c2.number_input("Satz", min_value=0, max_value=max_s, value=s1,
                                                     key=f"ko_s1_{r_idx}_{m_idx}", label_visibility="collapsed",
                                                     disabled=is_locked_round)
                            c3.markdown("<div style='text-align: center; font-weight: bold;'>:</div>",
                                        unsafe_allow_html=True)
                            new_s2 = c4.number_input("Satz", min_value=0, max_value=max_s, value=s2,
                                                     key=f"ko_s2_{r_idx}_{m_idx}", label_visibility="collapsed",
                                                     disabled=is_locked_round)
                            c5.write(f"**{p2_disp}**")

                            if new_s1 != s1 or new_s2 != s2:
                                daten["ko_einzel"]["runden"][r_idx][m_idx][2] = new_s1;
                                daten["ko_einzel"]["runden"][r_idx][m_idx][3] = new_s2
                                speichere_daten(daten);
                                st.rerun()

                if len(runden) >= 2 and len(runden[-2]) == 2:
                    h_runde = runden[-2]
                    losers = []
                    h_gueltig = True
                    for m in h_runde:
                        if len(m) < 4: h_gueltig = False; continue
                        if m[1] == "Freilos" or m[0] == "Freilos":
                            h_gueltig = False
                        elif is_valid_score(m[2], m[3]):
                            losers.append(m[1] if m[2] > m[3] else m[0])
                        else:
                            h_gueltig = False

                    if h_gueltig and len(losers) == 2 and all(losers):
                        if not daten["ko_einzel"].get("spiel_um_platz_3"):
                            daten["ko_einzel"]["spiel_um_platz_3"] = [losers[0], losers[1], 0, 0]
                            speichere_daten(daten);
                            st.rerun()

                        p3_match = daten["ko_einzel"].get("spiel_um_platz_3")
                        if p3_match and len(p3_match) >= 4:
                            p3_bo7 = daten.get("use_bo7_final", True)
                            p3_name = "🥉 Spiel um Platz 3 (Best-of-7)" if p3_bo7 else "🥉 Spiel um Platz 3 (Best-of-5)"
                            with st.expander(p3_name, expanded=True):
                                p1, p2, s1, s2 = p3_match
                                p1_disp, p2_disp = p1, p2
                                if is_valid_score(s1, s2, p3_bo7):
                                    if s1 > s2:
                                        p1_disp, p2_disp = f"🟢 {p1}", f"🔴 {p2}"
                                    else:
                                        p1_disp, p2_disp = f"🔴 {p1}", f"🟢 {p2}"

                                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                                c1.write(f"**{p1_disp}**")
                                max_p3 = 7 if p3_bo7 else 5
                                is_p3_locked = bool(
                                    not dev_mode and daten.get("spiel_um_platz_3_gesperrt", False)) or ui_disabled
                                new_s1 = c2.number_input("Satz", min_value=0, max_value=max_p3, value=s1, key="p3_s1",
                                                         label_visibility="collapsed", disabled=is_p3_locked)
                                c3.markdown("<div style='text-align: center; font-weight: bold;'>:</div>",
                                            unsafe_allow_html=True)
                                new_s2 = c4.number_input("Satz", min_value=0, max_value=max_p3, value=s2, key="p3_s2",
                                                         label_visibility="collapsed", disabled=is_p3_locked)
                                c5.write(f"**{p2_disp}**")

                                if new_s1 != s1 or new_s2 != s2:
                                    daten["ko_einzel"]["spiel_um_platz_3"][2] = new_s1;
                                    daten["ko_einzel"]["spiel_um_platz_3"][3] = new_s2
                                    speichere_daten(daten);
                                    st.rerun()

                is_final_reached = len(runden[-1]) == 1
                if not is_locked_round and runde_gueltig and not is_final_reached and not ui_disabled:
                    ckey = f"conf_ko_{len(runden)}"
                    if ckey not in st.session_state: st.session_state[ckey] = False
                    if not st.session_state[ckey]:
                        if st.button("✅ Einzel Runde abschließen", type="primary", key=f"btn_{ckey}"):
                            st.session_state[ckey] = True;
                            st.rerun()
                    else:
                        st.warning("Bist du sicher? Die Runde wird hart abgeschlossen.")
                        c_y, c_n = st.columns(2)
                        if c_y.button("✅ Ja, abschließen", type="primary", key=f"y_{ckey}"):
                            st.session_state[ckey] = False
                            next_round = []
                            winners = [m[0] if m[2] > m[3] else m[1] for m in runden[-1]]
                            for i in range(0, len(winners), 2): next_round.append(
                                [winners[i], winners[i + 1] if i + 1 < len(winners) else "Freilos", 0, 0])
                            daten["ko_einzel"]["runden"].append(next_round)
                            speichere_daten(daten);
                            st.rerun()
                        if c_n.button("❌ Abbrechen", key=f"n_{ckey}"):
                            st.session_state[ckey] = False;
                            st.rerun()

        # ==========================================
        # DOPPEL LOGIK (FEST, STRICT BO5)
        # ==========================================
        with t_doppel:
            d_ko = daten["ko_doppel"]
            phase = d_ko.get("phase", 1)
            baum = d_ko.get("baum_typ", 8)
            st.subheader(f"🤝 Doppel Turnierbaum ({baum}er-Bracket)")


            def render_runde(runde, name, r_key, is_disabled):
                is_disabled = is_disabled or ui_disabled
                st.write(f"### {name}")
                all_valid = True
                for idx, m in enumerate(runde):
                    if len(m) < 4: m.extend([0, 0])
                    p1, p2, s1, s2 = m

                    is_freilos = False
                    if p1 == "Freilos" and p2 != "Freilos":
                        s1, s2 = 0, 3; is_freilos = True
                    elif p2 == "Freilos" and p1 != "Freilos":
                        s1, s2 = 3, 0; is_freilos = True
                    elif p1 == "Freilos" and p2 == "Freilos":
                        s1, s2 = 3, 0; is_freilos = True

                    if is_freilos:
                        runde[idx][2], runde[idx][3] = s1, s2
                        st.info(f"🟢 **{p2 if p1 == 'Freilos' else p1}** zieht durch ein Freilos direkt weiter.")
                        continue

                    p1_disp, p2_disp = p1, p2
                    if is_valid_score(s1, s2, False):
                        if s1 > s2:
                            p1_disp, p2_disp = f"🟢 {p1}", f"🔴 {p2}"
                        else:
                            p1_disp, p2_disp = f"🔴 {p1}", f"🟢 {p2}"
                    else:
                        all_valid = False

                    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                    c1.write(f"**{p1_disp}**")
                    ns1 = c2.number_input("Satz", 0, 5, s1, key=f"{r_key}_{idx}_1", label_visibility="collapsed",
                                          disabled=(is_disabled and not dev_mode))
                    c3.markdown("<div style='text-align: center; font-weight: bold;'>:</div>", unsafe_allow_html=True)
                    ns2 = c4.number_input("Satz", 0, 5, s2, key=f"{r_key}_{idx}_2", label_visibility="collapsed",
                                          disabled=(is_disabled and not dev_mode))
                    c5.write(f"**{p2_disp}**")

                    if ns1 != s1 or ns2 != s2:
                        runde[idx][2], runde[idx][3] = ns1, ns2
                        if "gf" in r_key and idx == 0:
                            if is_valid_score(ns1, ns2, False):
                                w_win = m[0] if ns1 > ns2 else m[1]
                                if w_win != m[0] and len(d_ko["gf"]) == 1:
                                    d_ko["gf"].append([m[0], m[1], 0, 0])
                                elif w_win == m[0] and len(d_ko["gf"]) == 2:
                                    d_ko["gf"].pop()
                            elif len(d_ko["gf"]) == 2:
                                d_ko["gf"].pop()
                        speichere_daten(daten);
                        st.rerun()
                return all_valid


            def get_win_los(runde):
                wins, los = [], []
                for m in runde:
                    if m[2] > m[3]:
                        wins.append(m[0]); los.append(m[1])
                    else:
                        wins.append(m[1]); los.append(m[0])
                return wins, los


            def render_phase_button(phase_nr, label, action_func):
                if ui_disabled: return
                confirm_key = f"confirm_phase_{phase_nr}"
                if not st.session_state.get(confirm_key, False):
                    if st.button(label, key=f"btn_p{phase_nr}", type="primary"):
                        st.session_state[confirm_key] = True;
                        st.rerun()
                else:
                    st.warning(f"Bist du sicher? Die Phase {phase_nr} wird hart abgeschlossen.")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Ja, abschließen", type="primary", key=f"btn_y_{phase_nr}"):
                        st.session_state[confirm_key] = False;
                        action_func();
                        st.rerun()
                    if c2.button("❌ Abbrechen", key=f"btn_n_{phase_nr}"):
                        st.session_state[confirm_key] = False;
                        st.rerun()


            w1_ok = render_runde(d_ko["w1"], "Winner Runde 1", "d_w1", phase > 1)


            def do_phase1():
                w1_w, w1_l = get_win_los(d_ko["w1"])
                if baum == 8:
                    d_ko["w2"] = [[w1_w[i], w1_w[i + 1], 0, 0] for i in range(0, 4, 2)];
                    d_ko["l1"] = [[w1_l[i], w1_l[i + 1], 0, 0] for i in range(0, 4, 2)]
                else:
                    d_ko["w2"] = [[w1_w[i], w1_w[i + 1], 0, 0] for i in range(0, 8, 2)];
                    d_ko["l1"] = [[w1_l[i], w1_l[i + 1], 0, 0] for i in range(0, 8, 2)]
                d_ko["phase"] = 2;
                speichere_daten(daten)


            if phase == 1 and w1_ok: render_phase_button(1, "✅ Phase 1 abschließen", do_phase1)

            if phase >= 2:
                st.markdown("---")
                w2_ok = render_runde(d_ko["w2"], "Winner Runde 2", "d_w2", phase > 2)
                l1_ok = render_runde(d_ko["l1"], "Loser Runde 1", "d_l1", phase > 2)


                def do_phase2():
                    w2_w, w2_l = get_win_los(d_ko["w2"]);
                    l1_w, l1_l = get_win_los(d_ko["l1"])
                    if baum == 8:
                        d_ko["wf"] = [[w2_w[0], w2_w[1], 0, 0]]; d_ko["l2"] = [[l1_w[i], w2_l[i], 0, 0] for i in
                                                                               range(2)]
                    else:
                        d_ko["w3"] = [[w2_w[i], w2_w[i + 1], 0, 0] for i in range(0, 4, 2)]; d_ko["l2"] = [
                            [l1_w[i], w2_l[i], 0, 0] for i in range(4)]
                    d_ko["phase"] = 3;
                    speichere_daten(daten)


                if phase == 2 and w2_ok and l1_ok: render_phase_button(2, "✅ Phase 2 abschließen", do_phase2)

            if phase >= 3:
                st.markdown("---")
                if baum == 8:
                    wf_ok = render_runde(d_ko["wf"], "Winner-Finale", "d_wf", phase > 3)
                else:
                    w3_ok = render_runde(d_ko["w3"], "Winner Runde 3", "d_w3", phase > 3)
                l2_ok = render_runde(d_ko["l2"], "Loser Runde 2", "d_l2", phase > 3)


                def do_phase3():
                    l2_w, _ = get_win_los(d_ko["l2"])
                    if baum == 8:
                        d_ko["l3"] = [[l2_w[0], l2_w[1], 0, 0]]
                    else:
                        w3_w, w3_l = get_win_los(d_ko["w3"]);
                        d_ko["wf"] = [[w3_w[0], w3_w[1], 0, 0]];
                        d_ko["l3"] = [[l2_w[i], l2_w[i + 1], 0, 0] for i in range(0, 4, 2)]
                    d_ko["phase"] = 4;
                    speichere_daten(daten)


                if phase == 3 and l2_ok and (baum == 8 and wf_ok or baum == 16 and w3_ok): render_phase_button(3,
                                                                                                               "✅ Phase 3 abschließen",
                                                                                                               do_phase3)

            if phase >= 4:
                st.markdown("---")
                if baum == 16: wf_ok = render_runde(d_ko["wf"], "Winner-Finale", "d_wf", phase > 4)
                l3_ok = render_runde(d_ko["l3"], "Loser-Halbfinale" if baum == 8 else "Loser Runde 3", "d_l3",
                                     phase > 4)


                def do_phase4():
                    l3_w, _ = get_win_los(d_ko["l3"])
                    if baum == 8:
                        _, wf_l = get_win_los(d_ko["wf"]);
                        d_ko["lf"] = [[l3_w[0], wf_l[0], 0, 0]]
                    else:
                        _, w3_l = get_win_los(d_ko["w3"]);
                        d_ko["l4"] = [[l3_w[i], w3_l[i], 0, 0] for i in range(2)]
                    d_ko["phase"] = 5;
                    speichere_daten(daten)


                if phase == 4 and l3_ok and (baum == 8 or wf_ok): render_phase_button(4, "✅ Phase 4 abschließen",
                                                                                      do_phase4)

            if phase >= 5:
                st.markdown("---")
                if baum == 8:
                    lf_ok = render_runde(d_ko["lf"], "Loser-Finale", "d_lf", phase > 5)


                    def do_phase5_8():
                        wf_w, _ = get_win_los(d_ko["wf"]);
                        lf_w, _ = get_win_los(d_ko["lf"]);
                        d_ko["gf"] = [[wf_w[0], lf_w[0], 0, 0]];
                        d_ko["phase"] = 6;
                        speichere_daten(daten)


                    if phase == 5 and lf_ok: render_phase_button(5, "👑 Zum Großen Finale", do_phase5_8)
                else:
                    l4_ok = render_runde(d_ko["l4"], "Loser Runde 4", "d_l4", phase > 5)


                    def do_phase5_16():
                        l4_w, _ = get_win_los(d_ko["l4"]);
                        d_ko["l5"] = [[l4_w[0], l4_w[1], 0, 0]];
                        d_ko["phase"] = 6;
                        speichere_daten(daten)


                    if phase == 5 and l4_ok: render_phase_button(5, "✅ Weiter (Loser-Halbfinale)", do_phase5_16)

            if phase >= 6:
                st.markdown("---")
                if baum == 8:
                    render_runde(d_ko["gf"], "👑 Großes Finale", "d_gf", False)
                else:
                    l5_ok = render_runde(d_ko["l5"], "Loser-Halbfinale", "d_l5", phase > 6)


                    def do_phase6_16():
                        l5_w, _ = get_win_los(d_ko["l5"]);
                        _, wf_l = get_win_los(d_ko["wf"]);
                        d_ko["lf"] = [[l5_w[0], wf_l[0], 0, 0]];
                        d_ko["phase"] = 7;
                        speichere_daten(daten)


                    if phase == 6 and l5_ok: render_phase_button(6, "✅ Weiter (Loser-Finale)", do_phase6_16)

            if phase >= 7 and baum == 16:
                st.markdown("---")
                lf_ok = render_runde(d_ko["lf"], "Loser-Finale", "d_lf", phase > 7)


                def do_phase7_16():
                    wf_w, _ = get_win_los(d_ko["wf"]);
                    lf_w, _ = get_win_los(d_ko["lf"]);
                    d_ko["gf"] = [[wf_w[0], lf_w[0], 0, 0]];
                    d_ko["phase"] = 8;
                    speichere_daten(daten)


                if phase == 7 and lf_ok: render_phase_button(7, "👑 Zum Großen Finale", do_phase7_16)

            if phase >= 8 and baum == 16:
                st.markdown("---")
                render_runde(d_ko["gf"], "👑 Großes Finale", "d_gf", False)

        # ==========================================
        # 6. TAB SIEGEREHRUNG & EXPORT
        # ==========================================
        if (einzel_fertig or doppel_fertig) and t_sieger:
            with t_sieger:
                st.markdown("<h2 style='text-align: center;'>🏆 Siegerehrung 🏆</h2>", unsafe_allow_html=True)


                # --- STATISTIK FUNKTIONEN ---
                def get_einzel_stats(player):
                    if not player or player == "Noch offen": return {"saetze": 0, "diff": 0}
                    saetze, diff = 0, 0
                    for g_matches in daten["matches_einzel"].values():
                        for match in g_matches:
                            if len(match) < 4: continue
                            p1, p2, s1, s2 = match
                            if p1 == player or p2 == player:
                                if is_valid_score(s1, s2):
                                    my_s = s1 if p1 == player else s2
                                    opp_s = s2 if p1 == player else s1
                                    saetze += (my_s + opp_s)
                                    diff += (my_s - opp_s)
                    for runde in daten["ko_einzel"]["runden"]:
                        for m in runde:
                            if len(m) < 4: continue
                            if m[0] == player or m[1] == player:
                                p1, p2, s1, s2 = m
                                is_f = (len(runde) == 1)
                                if is_valid_score(s1, s2, is_f and daten.get("use_bo7_final", True)):
                                    my_s = s1 if p1 == player else s2
                                    opp_s = s2 if p1 == player else s1
                                    saetze += (my_s + opp_s)
                                    diff += (my_s - opp_s)
                    p3_match = daten["ko_einzel"].get("spiel_um_platz_3")
                    if p3_match and len(p3_match) >= 4 and (p3_match[0] == player or p3_match[1] == player):
                        p1, p2, s1, s2 = p3_match
                        if is_valid_score(s1, s2, daten.get("use_bo7_final", True)):
                            my_s = s1 if p1 == player else s2
                            opp_s = s2 if p1 == player else s1
                            saetze += (my_s + opp_s)
                            diff += (my_s - opp_s)
                    return {"saetze": saetze, "diff": diff}


                def get_doppel_stats(team):
                    if not team: return {"saetze": 0, "diff": 0}
                    saetze, diff = 0, 0
                    keys = ["w1", "w2", "w3", "wf", "l1", "l2", "l3", "l4", "l5", "lf", "gf"]
                    for k in keys:
                        for m in daten["ko_doppel"].get(k, []):
                            if team in m:
                                p1, p2, s1, s2 = m
                                if p1 == "Freilos" or p2 == "Freilos": continue
                                if is_valid_score(s1, s2, False):
                                    my_s = s1 if p1 == team else s2
                                    opp_s = s2 if p1 == team else s1
                                    saetze += (my_s + opp_s)
                                    diff += (my_s - opp_s)
                    return {"saetze": saetze, "diff": diff}


                # --- VARIABLEN INIT ---
                platz_1, platz_2, platz_3 = "", "", "Noch offen"
                s1_stat, s2_stat, s3_stat = {"saetze": 0, "diff": 0}, {"saetze": 0, "diff": 0}, {"saetze": 0, "diff": 0}
                d_platz_1, d_platz_2 = "", ""
                d1_stat, d2_stat = {"saetze": 0, "diff": 0}, {"saetze": 0, "diff": 0}

                # --- EINZEL PODEST ---
                if einzel_fertig:
                    fin_match = daten["ko_einzel"]["runden"][-1][0]
                    platz_1 = fin_match[0] if fin_match[2] > fin_match[3] else fin_match[1]
                    platz_2 = fin_match[1] if fin_match[2] > fin_match[3] else fin_match[0]
                    p3_match = daten["ko_einzel"].get("spiel_um_platz_3")
                    if p3_match and len(p3_match) >= 4 and is_valid_score(p3_match[2], p3_match[3],
                                                                          daten.get("use_bo7_final", True)):
                        platz_3 = p3_match[0] if p3_match[2] > p3_match[3] else p3_match[1]

                    s1_stat = get_einzel_stats(platz_1)
                    s2_stat = get_einzel_stats(platz_2)
                    s3_stat = get_einzel_stats(platz_3)

                    st.markdown("### 🏓 Einzel")
                    st.markdown(f"""
                    <div style="display: flex; justify-content: center; align-items: flex-end; gap: 20px; margin-top: 20px; margin-bottom: 20px; text-align: center;">
                        <div style="background: #e0e0e0; padding: 20px; border-radius: 10px; width: 150px; height: 160px; display: flex; flex-direction: column; justify-content: flex-end;">
                            <span style="font-size: 30px;">🥈</span><b>2. Platz</b><br>{platz_2}
                        </div>
                        <div style="background: #ffd700; padding: 20px; border-radius: 10px; width: 170px; height: 210px; display: flex; flex-direction: column; justify-content: flex-end; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                            <span style="font-size: 40px;">👑</span><b style="font-size: 18px;">1. Platz</b><br>{platz_1}
                        </div>
                        <div style="background: #cd7f32; padding: 20px; border-radius: 10px; width: 150px; height: 130px; display: flex; flex-direction: column; justify-content: flex-end;">
                            <span style="font-size: 30px;">🥉</span><b>3. Platz</b><br>{platz_3}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(label=f"🥈 {platz_2}", value=f"{s2_stat['saetze']} Sätze",
                                  delta=f"{s2_stat['diff']:+d} Diff")
                    with c2:
                        st.metric(label=f"👑 {platz_1}", value=f"{s1_stat['saetze']} Sätze",
                                  delta=f"{s1_stat['diff']:+d} Diff")
                    with c3:
                        st.metric(label=f"🥉 {platz_3}", value=f"{s3_stat['saetze']} Sätze",
                                  delta=f"{s3_stat['diff']:+d} Diff")

                # --- DOPPEL PODEST ---
                if doppel_fertig:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("### 🤝 Doppel")
                    last_gf = gf[-1]
                    d_platz_1 = last_gf[0] if last_gf[2] > last_gf[3] else last_gf[1]
                    d_platz_2 = last_gf[1] if last_gf[2] > last_gf[3] else last_gf[0]

                    d1_stat = get_doppel_stats(d_platz_1)
                    d2_stat = get_doppel_stats(d_platz_2)

                    st.markdown(f"""
                    <div style="display: flex; justify-content: center; align-items: flex-end; gap: 20px; margin-top: 20px; margin-bottom: 20px; text-align: center;">
                        <div style="background: #e0e0e0; padding: 20px; border-radius: 10px; width: 150px; height: 160px; display: flex; flex-direction: column; justify-content: flex-end;">
                            <span style="font-size: 30px;">🥈</span><b>2. Platz</b><br>{d_platz_2}
                        </div>
                        <div style="background: #ffd700; padding: 20px; border-radius: 10px; width: 170px; height: 210px; display: flex; flex-direction: column; justify-content: flex-end; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                            <span style="font-size: 40px;">👑</span><b style="font-size: 18px;">1. Platz</b><br>{d_platz_1}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1: st.metric(label=f"🥈 {d_platz_2}", value=f"{d2_stat['saetze']} Sätze",
                                       delta=f"{d2_stat['diff']:+d} Diff")
                    with c2: st.metric(label=f"👑 {d_platz_1}", value=f"{d1_stat['saetze']} Sätze",
                                       delta=f"{d1_stat['diff']:+d} Diff")

                # --- EXPORT REPORT ---
                st.markdown("<br><br>", unsafe_allow_html=True)
                report_txt = f"=== TURNIER BERICHT ===\n\n"
                if einzel_fertig:
                    report_txt += f"EINZEL:\n"
                    report_txt += f"1. Platz: {platz_1} ({s1_stat['saetze']} Saetze, {s1_stat['diff']:+d} Diff)\n"
                    report_txt += f"2. Platz: {platz_2} ({s2_stat['saetze']} Saetze, {s2_stat['diff']:+d} Diff)\n"
                    report_txt += f"3. Platz: {platz_3} ({s3_stat['saetze']} Saetze, {s3_stat['diff']:+d} Diff)\n"
                if doppel_fertig:
                    report_txt += f"\nDOPPEL:\n"
                    report_txt += f"1. Platz: {d_platz_1} ({d1_stat['saetze']} Saetze, {d1_stat['diff']:+d} Diff)\n"
                    report_txt += f"2. Platz: {d_platz_2} ({d2_stat['saetze']} Saetze, {d2_stat['diff']:+d} Diff)\n"
                report_txt += "\nHerzlichen Glueckwunsch!"

                st.download_button("📄 Turnier-Ergebnisse exportieren (.txt)", data=report_txt,
                                   file_name="turnier_ergebnisse.txt", mime="text/plain")

                # --- TURNIER EINFRIEREN (WENN BEIDES FERTIG) ---
                if einzel_fertig and doppel_fertig:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if not is_readonly:
                        if not is_frozen:
                            if st.button("🔒 Turnierergebnisse offiziell einfrieren"):
                                daten["turnier_eingefroren"] = True
                                speichere_daten(daten);
                                st.rerun()
                        else:
                            st.success("🔒 Das Turnier wurde offiziell beendet und eingefroren.")
                elif not is_readonly:
                    st.info(
                        "Das Turnier kann erst eingefroren werden, wenn Einzel und Doppel komplett abgeschlossen sind.")

        # ==========================================
        # 7. RESET
        # ==========================================
        if not is_readonly:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            col_reset = st.columns(1)[0]
            with col_reset:
                if "bestaetige_reset" not in st.session_state: st.session_state["bestaetige_reset"] = False
                if not st.session_state["bestaetige_reset"]:
                    if st.button("⚠️ Turnier Reset (Alles auf Anfang)"):
                        st.session_state["bestaetige_reset"] = True;
                        st.rerun()
                else:
                    st.error("Wirklich alles zurücksetzen? (Erstellt ein Backup der aktuellen Daten)")
                    c_ja, c_nein = st.columns(2)
                    if c_ja.button("Ja, Backup erstellen & Reset", type="primary"):
                        st.session_state["bestaetige_reset"] = False
                        if os.path.exists(DATEI):
                            os.rename(DATEI, f"backup_{int(time.time())}.json")
                        speichere_daten(lade_daten())  # Leere Daten laden
                        st.rerun()
                    if c_nein.button("Abbrechen"):
                        st.session_state["bestaetige_reset"] = False;
                        st.rerun()