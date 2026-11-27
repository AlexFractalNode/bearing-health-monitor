# Projekt-Brief: Bearing Health Monitor (Predictive Maintenance auf NASA-IMS-Vibrationsdaten)

> Übergabe-Dokument für die Claude-Code-Session. Lege diese Datei im Projekt ab
> (z. B. als `docs/PROJECT_BRIEF.md` oder als Projekt-Anweisung) und starte mit dem Start-Prompt unten.

---

## 0. Start-Prompt (zum Einfügen als erste Nachricht)

```
Hallo Claude, wir bauen ein kleines Data-Science-Portfolio-Projekt für mein GitHub-Profil.
Lies bitte zuerst PROJECT_BRIEF.md vollständig. Es enthält Ziel, Datensatz, gewählten Ansatz,
Phasen und Arbeitsregeln.

Dann:
1. Fasse in höchstens 8 Sätzen zusammen, was du gebaut haben wirst und wie das Ergebnis aussieht.
2. Nenne Widersprüche oder Lücken, die du im Brief findest (Abschnitt 11 listet bekannte offene Punkte).
3. Starte mit Phase 0 und frage mich nur bei Entscheidungen, die das Ergebnis wirklich ändern.

Arbeitsregeln: Antworten an mich auf Deutsch, Code/Kommentare/README auf Englisch.
Keine Rohdaten committen. Nichts auf GitHub pushen, ohne dass ich es bestätigt habe.
```

---

## 1. Worum geht es?

**Alexander** (Data-Science-Student, 3. Semester) möchte ein **technisch-wissenschaftliches Portfolio-Projekt**
für sein GitHub-Profil. Es soll zeigen, dass er den Weg von **Rohsignal → Features → Modell → Auswertung →
kleiner Dienst** sauber beherrscht und nicht nur ein Notebook auf einem fertigen CSV abgibt.

**Projektidee:** Aus Vibrationsmessungen von Wälzlagern, die bis zum Ausfall gelaufen sind (NASA-IMS-Datensatz),
wird der Gesundheitszustand eines Lagers überwacht. Ein Modell lernt, wie ein *gesundes* Lager aussieht, und
schlägt Alarm, sobald sich das Signal davon entfernt. Das Ergebnis wird als kleine API (FastAPI + Docker)
bereitgestellt und in einer verständlichen README präsentiert.

**Warum dieses Thema?** Es verbindet Signalverarbeitung (FFT, Filter) mit Machine Learning (Anomalieerkennung,
Autoencoder) und ist industrienah. Genau diese Kombination fehlt in den meisten Studierenden-Portfolios.

---

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele**
- Ein reproduzierbares Repo, das ein Recruiter in 5 Minuten versteht (starke README mit Abbildungen).
- Ein nachvollziehbarer Signal-Feature-Teil (Zeit- und Frequenzbereich, Hüllkurvenspektrum).
- Mindestens zwei Anomalie-Modelle plus eine **einfache Baseline** (z. B. RMS-Schwellwert) im fairen Vergleich.
- Saubere Evaluation ohne Zukunftswissen (siehe Abschnitt 7).
- Ein lauffähiger Mini-Dienst: Messung rein, Health-Score und Alarmstatus raus.

**Nicht-Ziele**
- Keine genaue Restlebensdauer-Vorhersage (RUL). Es gibt nur wenige Ausfälle, das wäre statistisch nicht belastbar.
- Kein Cloud-Deployment, keine MLOps-Plattform, keine große Datenbank.
- Keine Optimierung auf Leaderboard-Zahlen.

**Anti-Ziele (wäre ein Misserfolg, auch wenn der Code läuft)**
- Data Leakage (Zufallssplit über Zeitreihen, Skalierung auf allen Daten, Schwellwert auf dem Testlauf getunt).
- Ein Deep-Learning-Modell ohne Vergleich zu einer einfachen Baseline.
- Behauptungen in der README, die die Ergebnisse nicht tragen.

---

## 3. Was Alexander schon kann (als gegeben annehmen)

Aus den Modulbeschreibungen Semester 1 bis 3. Nichts davon muss ausführlich erklärt werden:

| Gebiet | Vorhanden |
|---|---|
| Python | Grundlagen, OOP, Module/Pakete, Fehlerbehandlung, Web-APIs/Scraping |
| Datenstack | NumPy, Pandas (inkl. Zeitreihentypen), Matplotlib, Seaborn |
| Statistik/Signale | Beschreibende und schließende Statistik, Regression, Stochastische Prozesse, **FFT, Abtasttheorem, digitale Filter (IIR/FIR)** |
| Mathe | Lineare Algebra inkl. **SVD, Eigenwerte**, Optimierung, Gradientenverfahren, Adam |
| ML | scikit-learn (Kreuzvalidierung, Grid-Search, PCA), Random Forest, Boosting, SVM, Clustering, **Autoencoder**, t-SNE/Isomap |
| Deep Learning | Keras/TensorFlow, vorwärts gerichtete Netze, CNNs, Dropout |
| Software/Daten | UML, SQL und ER-Modellierung (Datenbanken 1 läuft aktuell) |

Neu für ihn dürften sein: Wälzlager-Fehlerfrequenzen und Hüllkurvenanalyse, FastAPI, Docker, Testen mit pytest.
Diese Teile bitte kurz und praxisnah erklären.

---

## 4. Datensatz: NASA / IMS Bearings

Quelle: Center for Intelligent Maintenance Systems (IMS), University of Cincinnati, veröffentlicht über das
NASA Prognostics Data Repository. Landing Page: <https://data.nasa.gov/dataset/ims-bearings>
(Download laut Katalogeintrag: `https://data.nasa.gov/docs/legacy/IMS.zip`). Lizenz laut Katalog: US Government Works.

Was recherchiert und bestätigt ist:
- Vier Lager auf einer Welle, Drehzahl **2000 rpm**, konstante Last.
- **Drei Run-to-Failure-Experimente**, Vibrations-Snapshots alle 5 bzw. 10 Minuten.
- Jeder Snapshot: **eine Sekunde, 20 480 Messwerte bei 20 kHz**.
- Natürliche Schadensentwicklung, nicht künstlich eingebracht.

**Von Claude Code selbst zu verifizieren** (aus der mitgelieferten Readme und den Dateien, nicht aus diesem Brief übernehmen):
- Genaue Kanalzahl pro Test (nach meinem Kenntnisstand 8 Kanäle in Test 1, 4 Kanäle in Test 2 und 3) und welcher Kanal zu welchem Lager gehört.
- Anzahl der Dateien pro Test, Zeitstempel in den Dateinamen, Trennzeichen.
- Welche Lager in welchem Test ausgefallen sind und mit welchem Schadenstyp (Innenring, Außenring, Rolle).
- Größe des Downloads. Sie ist groß, daher nicht ins Git-Repo.

Falls die Sandbox den Download blockiert: Alexander lädt `IMS.zip` manuell herunter und legt es unter `data/raw/` ab.

---

## 5. Gewählter Ansatz und warum

**Ansatz:** Anomalieerkennung auf Basis eines "gesunden" Referenzbereichs plus Health-Indicator-Verlauf.
Pro Snapshot werden Features berechnet, ein Modell wird nur auf dem frühen, gesunden Abschnitt eines Laufs
trainiert, und der Verlauf des Anomalie-Scores wird gegen den tatsächlichen Ausfall bewertet.

**Warum nicht überwachte RUL-Regression?** Es existieren nur wenige Ausfallereignisse. Ein Modell würde sich
aufs Auswendiglernen dieser Läufe beschränken. Anomalieerkennung ist hier die ehrliche Problemstellung.

**Warum nicht NASA C-MAPSS (Turbofan)?** Dort gibt es pro Flugzyklus nur 21 Sensor-Momentwerte, keine
hochfrequenten Rohsignale. FFT und Filter würden keinen Sinn ergeben, und der Signalverarbeitungs-Teil, der das
Projekt besonders macht, entfiele. C-MAPSS bleibt höchstens eine spätere Erweiterung.

---

## 6. Pipeline und Repo-Struktur

```
raw snapshots (20 kHz) ──► preprocessing ──► features ──► baseline + models ──► evaluation
                                                              │
                                                              └──► FastAPI service (Docker)
```

Vorgeschlagene Struktur (Claude Code darf sinnvoll abweichen, bitte begründen):

```
bearing-health-monitor/
├── README.md                 # Recruiter-tauglich, Englisch
├── docs/PROJECT_BRIEF.md     # dieses Dokument
├── data/                     # nicht committen (.gitignore), nur data/README.md mit Download-Anleitung
│   ├── raw/
│   └── processed/            # Features als Parquet
├── notebooks/                # EDA und Ergebnis-Abbildungen, schlank halten
├── src/bearing_monitor/
│   ├── io.py                 # Laden der Snapshots
│   ├── features.py           # Zeit-/Frequenzbereichs-Features, Hüllkurvenspektrum
│   ├── models.py             # Baseline, PCA/Mahalanobis, Isolation Forest, Autoencoder
│   ├── evaluate.py           # Alarmzeitpunkt, Vorlaufzeit, Fehlalarme
│   └── api.py                # FastAPI
├── tests/                    # pytest für features, evaluate, api
├── Dockerfile
├── pyproject.toml / requirements.txt
└── .gitignore
```

---

## 7. Phasen mit Fertig-Kriterien

Nach jeder Phase ein Commit mit sprechender Nachricht. Vor der nächsten Phase kurz mit Alexander abstimmen.

**Phase 0 – Setup und Datencheck**
- Repo, virtuelle Umgebung, `.gitignore` (Rohdaten, `.venv`, Modelle ausnehmen), Grundstruktur.
- Daten beschaffen, Abschnitt 4 verifizieren, Befunde in `data/README.md` festhalten.
- *Fertig, wenn:* ein Snapshot geladen und als Zeitsignal und Spektrum geplottet ist.

**Phase 1 – Exploration**
- Verlauf einfacher Kennwerte (RMS, Kurtosis) über die gesamte Laufzeit pro Lager und Test.
- Erste Abbildung: "Ausfall im Signal sichtbar machen".
- *Fertig, wenn:* Alexander und Claude Code erklären können, ab wann welches Lager sichtbar auffällig wird.

**Phase 2 – Feature-Engineering**
- Zeitbereich: RMS, Standardabweichung, Kurtosis, Schiefe, Crest-Faktor, Peak-to-Peak.
- Frequenzbereich: Energie in Frequenzbändern (FFT oder Welch), spektraler Schwerpunkt.
- Hüllkurvenspektrum: Bandpass, Hilbert-Hüllkurve, FFT; Energie um die Lager-Fehlerfrequenzen.
  Geometrie des Lagers (Rexnord ZA-2115) nach meinem Kenntnisstand, **nicht geprüft**: 16 Wälzkörper, Teilkreisdurchmesser 2,815 in,
  Wälzkörperdurchmesser 0,331 in, Berührungswinkel 15,17°. Daraus ergeben sich bei 2000 rpm etwa
  BPFO ≈ 236 Hz und BPFI ≈ 297 Hz. **Claude Code rechnet das selbst nach** und zitiert die Quelle.
- Features als Parquet speichern, Berechnung als getestete Funktionen in `features.py`.
- *Fertig, wenn:* `pytest` für ein synthetisches Testsignal bekannte Werte liefert (z. B. Sinus mit bekannter RMS und Frequenz).

**Phase 3 – Modelle und Evaluation**
- Baseline: RMS- oder Kurtosis-Schwellwert (z. B. Mittelwert plus k Standardabweichungen des gesunden Abschnitts).
- Modell A: PCA-Rekonstruktionsfehler oder Mahalanobis-Distanz.
- Modell B: Isolation Forest oder One-Class-SVM.
- Modell C: Autoencoder (Keras) auf den Features, optional auf Spektrogrammen.
- **Evaluationsregeln:**
  - Training nur auf dem frühen, gesunden Abschnitt (z. B. die ersten 20 bis 30 % eines Laufs, Anteil begründen).
  - Zeitlich geordnet, **nie mischen**. Skalierer nur auf Trainingsdaten fitten.
  - Schwellwert ausschließlich aus Trainingsdaten ableiten.
  - Kennzahlen: Alarmzeitpunkt relativ zum Ausfall (Vorlaufzeit), Anzahl Fehlalarme im gesunden Abschnitt.
  - Wenn möglich Kreuzvergleich: auf Test A gesund trainieren, auf Test B bewerten.
- *Fertig, wenn:* eine Vergleichstabelle und Abbildung (Score über der Zeit mit Alarmschwelle und Ausfallzeitpunkt) vorliegen und ehrlich diskutiert sind, auch falls die Baseline gewinnt.

**Phase 4 – Mini-Dienst**
- FastAPI-Endpunkt: nimmt einen Snapshot entgegen (z. B. JSON-Array oder Datei-Upload), gibt Health-Score und Alarmstatus zurück.
- Gespeichertes Modell mit joblib bzw. Keras-Format, Version der Abhängigkeiten festhalten.
- `Dockerfile`, Test des Endpunkts mit pytest und `TestClient`.
- *Fertig, wenn:* `docker build` und `docker run` funktionieren und ein Beispielaufruf in der README steht.

**Phase 5 – README und Politur**
- Englische README: Problem, Daten, Methode (mit 2 bis 3 Abbildungen), Ergebnisse, **Limitations**, Reproduktionsanleitung.
- Kurzes Fazit, was die Ergebnisse *nicht* belegen (wenige Läufe, ein Lagertyp).
- Linting (ruff), Tests grün, Beispiel-Notebook läuft von oben nach unten durch.

**Optional (nur nach Absprache):** Streamlit-Dashboard als Demo, Zweitdatensatz (z. B. FEMTO/PRONOSTIA oder XJTU-SY) zur Generalisierungsprüfung.

---

## 8. Tooling und Konventionen

- Python 3.11 oder neuer. **Prüfen, welche Python-Version die installierte TensorFlow-Version unterstützt**, und danach entscheiden.
- Bibliotheken: numpy, scipy (`scipy.signal`), pandas, pyarrow, scikit-learn, matplotlib, seaborn, tensorflow/keras, fastapi, uvicorn, pydantic, joblib, pytest, ruff.
- Umgebung: Windows 11 (Alexanders PC). TensorFlow läuft dort nur auf der CPU, das reicht für einen kleinen Autoencoder.
- Seeds fixieren, Ergebnisse reproduzierbar machen.
- Abbildungen als PNG/SVG in `docs/figures/` ablegen und in der README verlinken.
- Commit-Nachrichten kurz und im Imperativ (Englisch).

---

## 9. Arbeitsweise mit Alexander

- Chat auf **Deutsch**, Code, Kommentare, Docstrings, README und Commit-Nachrichten auf **Englisch**.
- Er ist Student, kein Anfänger: Erkläre neue Konzepte (Hüllkurvenanalyse, API, Docker) knapp und verständlich, bekannte Dinge nicht.
- In Phasen arbeiten, nach jeder Phase kurz berichten, was herauskam und was auffiel. Keine langen Zwischenmonologe.
- Entscheidungen, die das Ergebnis ändern, vorher vorschlagen: Option, Kompromiss, Empfehlung.
- Er besitzt zwei GitHub-Accounts (privat und Uni). **Vor dem ersten Repo-Anlegen oder Push fragen, welcher Account gemeint ist.** Nie ohne Bestätigung pushen.
- Ehrlichkeit vor Optik: Wenn die Baseline besser ist oder Ergebnisse schwach sind, steht das so in der README.

---

## 10. Quellen für Hintergrundwissen

- NASA Prognostics Data Repository, IMS Bearings: <https://data.nasa.gov/dataset/ims-bearings>
- Lee et al., 2007 (Originalbeschreibung des IMS-Experiments), zitiert in den meisten Papern zum Datensatz.
- Review zu ML/DL für Lagerdiagnose: <https://arxiv.org/abs/1901.08247>
- Autoencoder-basiertes Health-Monitoring auf IMS: <https://arxiv.org/abs/1703.06272>

---

## 11. Bekannte offene Punkte (bitte früh klären)

1. **Ausfallzeitpunkte:** Wann genau gilt ein Lager als "ausgefallen"? Aus Readme/Literatur ableiten und dokumentieren.
2. **Länge des gesunden Abschnitts:** Fester Anteil oder datengetrieben (z. B. bis erste Auffälligkeit)? Vorschlag machen und begründen.
3. **Kreuzvalidierung zwischen Tests:** Sind die Tests vergleichbar genug (andere Kanalzahl in Test 1)? Prüfen, bevor darauf ein Ergebnis gebaut wird.
4. **Datenmenge:** Reichen Feature-Dateien als Parquet, oder werden Spektrogramme für den Autoencoder gebraucht (Speicher, Laufzeit)?
5. **Namen:** Repo-Name `bearing-health-monitor` ist nur ein Arbeitstitel.

---

## 12. Annahmen, die im Brief als Entscheidungen stehen (Alexander bitte gegenlesen)

- Fokus auf Anomalieerkennung statt RUL-Regression (Abschnitt 5).
- IMS statt C-MAPSS als Hauptdatensatz (Abschnitt 5).
- Englisch für Code und README, Deutsch für den Chat.
- FastAPI und Docker als Deployment, Streamlit nur optional.
