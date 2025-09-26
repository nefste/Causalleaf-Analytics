# Kapazitätsplanung MVP (Streamlit)

Dieses MVP demonstriert das im Dokument `MVP.md` beschriebene Dashboard für ein strategisch-taktisches Kapazitätsmanagement im Krankenhaus. Die App simuliert synthetische Daten, visualisiert Plan- und Prognosekurven, stellt eine Ampel-Heatmap mit Handlungsempfehlungen bereit und fasst zentrale IKM-Kennzahlen zusammen.

## Funktionsumfang

- Jahresverlauf mit Plan-, Prognose- und Kapazitätslinie je Ressource.
- Ampel-Heatmap (KW × Ressource) inkl. Empfehlungen nach Ampellogik.
- Einstellungs-Panel für interne/externe Treiber, Datenrhythmus und Schwellenwerte.
- KPI-Kacheln (Auslastung, MAPE, Wartetage, Stornoquote, Pflege-Engpass) und Top-Treiber.
- Wochen-Sparkline zur schnellen Trendprüfung.
- Downloads: CSV-Export (Plan/Prognose/Capacity + Treiber) und SVG-Export der Liniengrafik.

## Installation & Start

1. Python ≥ 3.10 verwenden.
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. Streamlit-App starten:
   ```bash
   streamlit run app.py
   ```
4. Die Anwendung öffnet sich im Browser unter `http://localhost:8501`.

## Bedienung

- **Einstellungen (linke Sidebar):**
  - Interne Faktoren (Verweildauer, OP-Zeiten, Patient-Pflege-Ratio, Abwesenheiten, Cluster).
  - Externe Faktoren (Saisonalität, Grippe-/Epidemie-Index, Wetter-/Unfalltreiber).
  - Datenrhythmus (wöchentlich oder monatlich) für die Assimilation der Ist-Zahlen in die Prognose.
  - Ampel-Schwellen (`Grün`-Puffer und Schwelle für `Gelb`).
  - Button **Standardwerte** setzt alle Parameter zurück. **Prognose aktualisieren** erzwingt einen Re-Run mit neuen Zufallszahlen (Seed-kontrolliert).

- **Jahresplanung:** Interaktive SVG-Linie (Plan, Prognose, Kapazität) je Ressource. Download als SVG sowie KPI-Kacheln zur aktuellen Woche.

- **Prognose & Steuerung:** Ampel-Heatmap mit Verdichtung nach Kalenderwochen, Empfehlungen nach Kritikalität, Wochen-Sparkline und Top-Treiber.

## Ampellogik & Empfehlungen

- Normierter Gap: `(Prognose − Kapazität) / Kapazität`.
- Schwellen (Standard):
  - `|Norm-Gap| < 0.05` → Grün (stabil)
  - `0.05 ≤ Norm-Gap < 0.15` → Gelb (Beobachtung, leichte Maßnahmen)
  - `Norm-Gap ≥ 0.15` → Rot (kritisch, starke Maßnahmen)
  - Negative Abweichungen unterhalb des Schwellenwertes → Blau (Überkapazität, Entlastung möglich)
- Empfehlungen basieren auf heuristischen Regeln (OP-Verschiebung, Betten öffnen/schließen, Pflege-Schichten umplanen etc.) und berücksichtigen die Patient-Pflege-Ratio.

## Daten & Grenzen

- Vollständig synthetische Daten mit seedbarem PRNG, Kombination aus Trends, Saison, internen und externen Treibern.
- Assimilation der Ist-Zahlen wöchentlich oder monatlich via exponentiellem Glättungsanteil (`α = 0.3`).
- Low-fi Visualisierung (Grau-Schema + Ampelfarben), keine externen CDNs oder Fonts.
- MVP-Status: Kein Persistenzspeicher, keine Benutzerverwaltung, keine Schnittstellen (HL7/FHIR), keine Echtzeit-Daten.

## Lizenz

MIT License – frei zur Verwendung, Anpassung und Weitergabe.
